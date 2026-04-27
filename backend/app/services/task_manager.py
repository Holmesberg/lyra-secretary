"""
Task Manager - SINGLE MUTATION AUTHORITY.

ALL task modifications MUST go through this service.
No other service should modify Task objects directly.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

import logging

from app.db.models import Task, TaskState, TaskSource, CategoryMapping, Deadline, CalibrationNudgeEvent
from app.db.scoping import get_current_user_id
from app.services.parser import TaskParser, extract_scope_bullets, infer_deadline_binding
from app.services.state_machine import StateMachine
from app.services.conflict_detector import ConflictDetector, ConflictResult
from app.services.notion_client import NotionClient
from app.utils.redis_client import RedisClient
from app.utils.time_utils import to_utc, now_utc
from app.core.exceptions import ImmutableTaskError

logger = logging.getLogger(__name__)


def _require_current_user(op: str) -> int:
    """Resolve the acting user_id from the request-scoped ContextVar.

    Fails closed with an explicit error instead of silently defaulting to
    operator (user_id=1), which was the LYR-093 cross-tenant write leak.
    Background jobs MUST call set_current_user_id(...) before invoking
    TaskManager — see workers/jobs/_per_user.py.
    """
    uid = get_current_user_id()
    if uid is None:
        raise RuntimeError(
            f"{op}: no current_user_id in ContextVar — refusing to write. "
            "Set it via middleware (HTTP) or _per_user.py (worker)."
        )
    return uid


class TaskManager:
    """
    Single authority for all task mutations.
    
    Architecture principle: All writes flow through here.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.parser = TaskParser()
        self.state_machine = StateMachine(db)
        self.conflict_detector = ConflictDetector(db)
        self.notion = NotionClient()
        self.redis = RedisClient()
    
    def _compute_session_index(
        self, planned_start_utc: datetime, created_at: datetime
    ) -> int:
        """Compute immutable session_index_in_day for a new task.

        Resets per local-tz date (Cairo). Counts existing non-system_error
        tasks on the same local date that are strictly earlier in
        (planned_start_utc, created_at) ordering. Called from every Task
        creation site. Set once, never recomputed — the cascade chain
        (Paper 2) depends on this being immutable.
        """
        from zoneinfo import ZoneInfo
        from app.core.config import settings

        tz = ZoneInfo(settings.USER_TIMEZONE)
        utc = ZoneInfo("UTC")

        # Local Cairo date for the new task
        ps_aware = planned_start_utc.replace(tzinfo=utc) if planned_start_utc.tzinfo is None else planned_start_utc
        local_date = ps_aware.astimezone(tz).date()

        # Cairo midnight → UTC range for the same local date
        day_start_local = datetime.combine(local_date, datetime.min.time(), tzinfo=tz)
        day_end_local = day_start_local + timedelta(days=1)
        day_start_utc = day_start_local.astimezone(utc).replace(tzinfo=None)
        day_end_utc = day_end_local.astimezone(utc).replace(tzinfo=None)

        # Count tasks on the same local day that are strictly earlier.
        # Tiebreaker: created_at ASC for identical planned_start_utc.
        from sqlalchemy import or_, and_
        count = self.db.query(Task).filter(
            Task.planned_start_utc >= day_start_utc,
            Task.planned_start_utc < day_end_utc,
            or_(
                Task.initiation_status != "system_error",
                Task.initiation_status.is_(None),
            ),
            Task.voided_at.is_(None),
            or_(
                Task.planned_start_utc < planned_start_utc,
                and_(
                    Task.planned_start_utc == planned_start_utc,
                    Task.created_at < created_at,
                ),
            ),
        ).count()
        return count

    def _infer_category(self, title: str) -> Optional[str]:
        """Infer category from title using CategoryMapping table.

        Checks exact word matches first (prevents false substring hits like
        'run' inside 'running'). Falls back to substring for multi-word
        keywords such as 'problem set'.
        """
        title_lower = title.lower()
        words = set(title_lower.split())
        mappings = self.db.query(CategoryMapping).all()
        # Pass 1: exact word match
        for m in mappings:
            if m.keyword.lower() in words:
                return m.category
        # Pass 2: multi-word keyword substring fallback
        for m in mappings:
            if " " in m.keyword and m.keyword.lower() in title_lower:
                return m.category
        return None

    def _validate_bindable_deadline(self, deadline_id: str) -> Deadline:
        """Resolve a deadline_id to a Deadline row that accepts new task bindings.

        Loop 11 (alembic 033) — explicit-binding helper for parser Pass 1.
        Reads user_id from the request-scoped ContextVar (matches the
        codebase's existing scoping pattern, NOT a param).

        Bindable: state ∈ {planned, active} AND voided_at IS NULL AND
        deadline.user_id == current_user.

        Raises ValueError on:
          - deadline not found
          - cross-user attempt (deadline owned by a different user)
          - voided deadline
          - terminal state (completed | missed | skipped | voided)

        See `docs/deadline_mechanism_design.md §"Inference mechanism"` Pass 1.
        Caller (create_task) is responsible for catching ValueError and
        mapping to HTTP 400 at the API layer.
        """
        uid = _require_current_user("validate_bindable_deadline")
        deadline = self.db.query(Deadline).filter(
            Deadline.deadline_id == deadline_id
        ).first()
        if deadline is None:
            raise ValueError(f"deadline_not_found: {deadline_id}")
        if deadline.user_id != uid:
            # Same error wording as not-found to avoid cross-user leakage
            # signal (don't tell user_A that user_B owns a specific UUID).
            raise ValueError(f"deadline_not_found: {deadline_id}")
        if deadline.voided_at is not None:
            raise ValueError(f"deadline_voided: {deadline_id}")
        if deadline.state not in ("planned", "active"):
            raise ValueError(
                f"deadline_terminal_state: {deadline_id} is in state "
                f"'{deadline.state}' which rejects new task bindings"
            )
        return deadline

    def create_task(
        self,
        title: str,
        start: datetime,
        end: datetime,
        category: Optional[str] = None,
        description: Optional[str] = None,
        state: TaskState = TaskState.PLANNED,
        source: TaskSource = TaskSource.MANUAL,
        confidence_score: Optional[float] = None,
        force_conflicts: bool = False,
        deadline_id: Optional[str] = None,
        # Loop 1 (alembic 034) — calibration nudge decision logging.
        # All four nudge_* params are all-or-none; partial sets raise.
        nudge_decision: Optional[str] = None,
        nudge_suggested_duration_minutes: Optional[int] = None,
        nudge_bias_factor: Optional[float] = None,
        nudge_sample_size: Optional[int] = None,
    ) -> tuple[Optional[Task], ConflictResult, bool]:
        """
        Create a new task.

        Returns:
            (created_task | None, ConflictResult, notion_synced)

        Severity contract (Path A, Apr 16 2026):
          - HARD conflicts (overlap with EXECUTING) ALWAYS reject regardless
            of force_conflicts. Single-mutation-authority is structural.
          - SOFT conflicts (PLANNED/PAUSED overlap, duplicate title same UTC
            day) reject when force_conflicts=False, accept when True.
          - No conflicts → create normally.

        Loop 11 (alembic 033, 2026-04-26):
          - `deadline_id` (optional) → parser Pass 1 explicit binding.
            Validated by `_validate_bindable_deadline`; ValueError on
            invalid id / cross-user / voided / terminal state.
            On bind, `deadline_match_source='user_explicit'`,
            `deadline_match_confidence=1.0`. If the deadline is in
            'planned' state, auto-transitions to 'active' (idempotent
            if already active).
          - `scope_bullet_count_at_plan` is auto-counted from
            `description` regardless of deadline binding. Powers
            MANIFESTO Rule 12's `scope_density` metric.
        """
        # Convert naive local times (Cairo) to UTC before storing
        start = to_utc(start)
        end = to_utc(end)

        # P4: Reject tasks with start time in the past (5 min buffer)
        if start < now_utc() - timedelta(minutes=5):
            raise ValueError("start_in_past: Task start time is in the past. Did you mean tomorrow?")

        # Classified detection (overlap + same-UTC-day duplicate title)
        result = self.conflict_detector.detect(start, end, title=title)

        # HARD always wins — force cannot override single-mutation authority
        if result.has_hard():
            return None, result, False
        if result.has_soft() and not force_conflicts:
            return None, result, False

        # Loop 11: validate explicit deadline binding BEFORE creating task
        # (fail fast — no orphan tasks if deadline_id is bogus).
        bound_deadline: Optional[Deadline] = None
        bound_via_inference = False
        bound_confidence: Optional[float] = None
        if deadline_id is not None:
            bound_deadline = self._validate_bindable_deadline(deadline_id)
            bound_confidence = 1.0
        else:
            # Pass 2 — keyword-overlap inference. Only fires if no
            # explicit deadline_id was supplied. Loads bindable
            # deadlines for the current user (state ∈ planned|active,
            # voided_at IS NULL) and picks the best title-overlap match
            # if any clears the 0.5 threshold.
            uid_for_pass2 = _require_current_user("create_task_pass2")
            candidates = (
                self.db.query(Deadline)
                .filter(
                    Deadline.user_id == uid_for_pass2,
                    Deadline.voided_at.is_(None),
                    Deadline.state.in_(("planned", "active")),
                )
                .all()
            )
            if candidates:
                match = infer_deadline_binding(title, candidates)
                if match is not None:
                    bound_deadline, bound_confidence = match
                    bound_via_inference = True

        # Auto-infer category from title if not provided
        if not category:
            category = self._infer_category(title)

        # Calculate duration
        duration_minutes = int((end - start).total_seconds() / 60)

        # Loop 11: parse scope bullets from description at PLANNED creation.
        scope_bullets_at_plan = extract_scope_bullets(description)

        # Create task (transaction safety)
        created_at_ts = now_utc()
        uid = _require_current_user("create_task")
        task = Task(
            title=title,
            planned_start_utc=start,
            planned_end_utc=end,
            planned_duration_minutes=duration_minutes,
            category=category,
            state=state,
            source=source,
            confidence_score=confidence_score,
            description=description,
            created_at=created_at_ts,
            last_modified_at=created_at_ts,
            session_index_in_day=self._compute_session_index(start, created_at_ts),
            user_id=uid,
            # Loop 11 fields (alembic 033)
            scope_bullet_count_at_plan=scope_bullets_at_plan,
            deadline_id=bound_deadline.deadline_id if bound_deadline else None,
            deadline_match_confidence=bound_confidence if bound_deadline else None,
            deadline_match_source=(
                "parser_auto" if (bound_deadline and bound_via_inference)
                else "user_explicit" if bound_deadline
                else None
            ),
        )

        # Loop 11: auto-transition planned → active on first bind. Idempotent
        # if deadline already active. Terminal states are unreachable here
        # (rejected by _validate_bindable_deadline above).
        if bound_deadline is not None and bound_deadline.state == "planned":
            bound_deadline.state = "active"

        self.db.add(task)
        self.db.flush()  # Get task_id

        # Loop 1 (alembic 034): if a calibration nudge fired during this
        # task's creation, log the user's decision in the same transaction
        # as the task. All-four-or-none discipline; partials raise. The
        # event row's executed_duration_minutes + resolved_at are NULL
        # at fire time and stamped by complete_task() when the task
        # transitions to EXECUTED.
        nudge_fields_present = sum(
            1 for f in (
                nudge_decision,
                nudge_suggested_duration_minutes,
                nudge_bias_factor,
                nudge_sample_size,
            ) if f is not None
        )
        if nudge_fields_present == 4:
            self.db.add(CalibrationNudgeEvent(
                user_id=uid,
                task_id=task.task_id,
                suggested_duration_minutes=nudge_suggested_duration_minutes,
                user_planned_duration_minutes=duration_minutes,
                bias_factor=nudge_bias_factor,
                sample_size=nudge_sample_size,
                user_decision=nudge_decision,
                decided_at=created_at_ts,
            ))
        elif nudge_fields_present != 0:
            # Defensive — Pydantic schema already enforces all-or-none, but
            # internal callers (StopwatchManager.start unplanned-task path)
            # bypass schema validation. Raise loudly so the bug surfaces.
            raise ValueError(
                f"create_task: nudge_* fields must be all-or-none; got "
                f"{nudge_fields_present}/4 present"
            )

        # Path B onboarding stamp: the first task a user ever creates
        # completes the onboarding ritual atomically with the task
        # create, so there's no window where the user has one task AND
        # a null onboarding_completed_at (which would silently re-show
        # the onboarding surface on next layout-level fetch of /users/me).
        try:
            from app.db.models import User
            u = self.db.query(User).filter(User.user_id == uid).first()
            if u is not None and u.onboarding_completed_at is None:
                u.onboarding_completed_at = created_at_ts
        except Exception as e:
            logger.warning(f"Onboarding stamp failed (non-blocking): {e}")
        self.db.commit()
        self.db.refresh(task)

        # Notion sync deferred to Redis queue — inline call cost user 1-8s per
        # create on the hot path. Queue drains via APScheduler worker.
        notion_synced = False
        try:
            self.redis.queue_notion_sync(task.task_id, {"action": "sync"}, user_id=str(get_current_user_id() or 1))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notion queue failed during create_task: {e}", exc_info=True)
        
        # Substitution detection: link to recently DELETED task in overlapping slot
        try:
            cutoff = now_utc() - timedelta(minutes=10)
            deleted_task = self.db.query(Task).filter(
                Task.state == TaskState.DELETED,
                Task.last_modified_at >= cutoff,
                Task.planned_start_utc < end,
                Task.planned_end_utc > start,
            ).first()
            if deleted_task:
                task.replaces_task_id = deleted_task.task_id
                deleted_task.replaced_by_task_id = task.task_id
                self.db.commit()
                self.db.refresh(task)
        except Exception as e:
            logger.warning(f"Substitution linkage failed (non-blocking): {e}")

        # Cache for undo — best-effort
        try:
            uid = str(get_current_user_id() or 1)
            self.redis.cache_undo_action("create_task", task.task_id, {
                "task_id": task.task_id,
                "title": task.title
            }, user_id=uid)
            self.redis.set_last_task(task.task_id, task.title, task.state.value if hasattr(task.state, "value") else str(task.state), user_id=uid)
        except Exception:
            pass
        return task, [], notion_synced
    
    def create_retroactive_task(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        category: Optional[str] = None,
        pre_task_readiness: Optional[int] = None,
        post_task_reflection: Optional[int] = None,
        planned_duration_minutes: Optional[int] = None,
        unplanned_reason: Optional[str] = None,
        total_paused_minutes: Optional[int] = None,
    ) -> tuple[Task, bool]:
        """
        Create a completed task from past timestamps (retroactive logging).

        Bypasses: past-time check, conflict detection, state machine.
        If planned_duration_minutes provided, computes real delta.
        Otherwise sets planned = executed (delta = 0).

        Returns:
            (task, notion_synced)
        """
        start_utc = to_utc(start_time)
        end_utc = to_utc(end_time)

        if end_utc <= start_utc:
            raise ValueError("end_time must be after start_time")

        if not category:
            category = self._infer_category(title)

        wall_clock = int((end_utc - start_utc).total_seconds() / 60)
        paused = total_paused_minutes or 0
        if paused > wall_clock:
            raise ValueError("total_paused_minutes cannot exceed wall-clock duration")
        executed_duration = wall_clock - paused
        if executed_duration < 1:
            raise ValueError("Session must be at least 1 minute of active work")

        if planned_duration_minutes is not None:
            planned_dur = planned_duration_minutes
            planned_end_utc = start_utc + timedelta(minutes=planned_dur)
        else:
            planned_dur = executed_duration
            planned_end_utc = end_utc

        created_at_ts = now_utc()
        uid = _require_current_user("create_retroactive_task")
        task = Task(
            title=title,
            category=category,
            planned_start_utc=start_utc,
            planned_end_utc=planned_end_utc,
            planned_duration_minutes=planned_dur,
            executed_start_utc=start_utc,
            executed_end_utc=end_utc,
            executed_duration_minutes=executed_duration,
            state=TaskState.EXECUTED,
            source=TaskSource.MANUAL,
            initiation_status="retroactive",
            pre_task_readiness=pre_task_readiness,
            post_task_reflection=post_task_reflection,
            unplanned_reason=unplanned_reason,
            created_at=created_at_ts,
            last_modified_at=created_at_ts,
            session_index_in_day=self._compute_session_index(start_utc, created_at_ts),
            user_id=uid,
        )

        self.db.add(task)
        self.db.flush()
        # Path B onboarding stamp (see create_task): retroactive is also a
        # first-interaction path that completes the ritual.
        try:
            from app.db.models import User
            u = self.db.query(User).filter(User.user_id == uid).first()
            if u is not None and u.onboarding_completed_at is None:
                u.onboarding_completed_at = created_at_ts
        except Exception as e:
            logger.warning(f"Onboarding stamp failed (non-blocking): {e}")
        self.db.commit()
        self.db.refresh(task)

        # Sync to Notion
        notion_synced = False
        try:
            self.notion.sync_task(task, db=self.db)
            notion_synced = True
        except Exception as e:
            logger.error(f"Notion sync failed during create_retroactive_task: {e}", exc_info=True)
            self.redis.queue_notion_sync(task.task_id, {"action": "sync"}, user_id=str(get_current_user_id() or 1))

        return task, notion_synced

    def start_task(self, task_id: str) -> Task:
        """
        Start a task (transition PLANNED → EXECUTING).
        
        Args:
            task_id: Task to start
            
        Returns:
            Updated task
        """
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        
        task = self.state_machine.transition(task, TaskState.EXECUTING)

        # Notion sync deferred to Redis queue (P0 latency fix 2026-04-15).
        try:
            self.redis.queue_notion_sync(task.task_id, {"action": "sync"}, user_id=str(get_current_user_id() or 1))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notion queue failed during start_task: {e}", exc_info=True)

        return task
    
    def complete_task(
        self,
        task_id: str,
        executed_start: datetime,
        executed_end: datetime
    ) -> tuple[Task, bool]:
        """
        Mark task as completed.
        
        Args:
            task_id: Task to complete
            executed_start: Actual start time (UTC)
            executed_end: Actual end time (UTC)
            
        Returns:
            (updated_task, notion_synced)
        """
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        if task.voided_at is not None:
            raise ValueError("Cannot complete a voided task")

        executed_duration = int((executed_end - executed_start).total_seconds() / 60)

        task.executed_start_utc = executed_start
        task.executed_end_utc = executed_end
        task.executed_duration_minutes = executed_duration

        # Loop 11 (alembic 033) — re-sample scope bullets at execute time
        # BEFORE the EXECUTED state transition fires (task is still mutable
        # while in EXECUTING/PAUSED — once EXECUTED, immutability per
        # state_machine.py:29 forbids further writes). The (at_plan,
        # at_execute) pair is the within-task scope-drift signal exposed
        # in MANIFESTO Rule 12's exploratory secondary analysis.
        task.scope_bullet_count_at_execute = extract_scope_bullets(task.description)

        # Loop 1 (alembic 034) — stamp calibration_nudge_event outcome if
        # one exists for this task. Inline UPDATE in the same transaction
        # as the task transition (cheaper than an APScheduler reconciliation
        # job; sub-millisecond per stop). voided_at filter respects the
        # voided_at_guard discipline — if the nudge event was invalidated
        # post-creation we don't resurrect it.
        nudge_event = (
            self.db.query(CalibrationNudgeEvent)
            .filter(
                CalibrationNudgeEvent.task_id == task.task_id,
                CalibrationNudgeEvent.executed_duration_minutes.is_(None),
                CalibrationNudgeEvent.voided_at.is_(None),
            )
            .first()
        )
        if nudge_event is not None:
            nudge_event.executed_duration_minutes = executed_duration
            nudge_event.resolved_at = now_utc()

        task = self.state_machine.transition(task, TaskState.EXECUTED)

        # Notion sync deferred to Redis queue (P0 latency fix 2026-04-15).
        notion_synced = False
        try:
            self.redis.queue_notion_sync(task.task_id, {"action": "sync"}, user_id=str(get_current_user_id() or 1))
        except Exception as e:
            logger.error(f"Notion queue failed during complete_task: {e}", exc_info=True)

        try:
            self.redis.set_last_task(task.task_id, task.title, task.state.value if hasattr(task.state, "value") else str(task.state), user_id=str(get_current_user_id() or 1))
        except Exception:
            pass
        return task, notion_synced
    
    def skip_task(self, task_id: str, reason: Optional[str] = None) -> Task:
        """
        Mark task as skipped.
        
        Args:
            task_id: Task to skip
            reason: Optional reason
            
        Returns:
            Updated task
        """
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        if task.voided_at is not None:
            raise ValueError("Cannot skip a voided task")

        task = self.state_machine.transition(task, TaskState.SKIPPED, notes=reason)

        # Notion sync deferred to Redis queue (P0 latency fix 2026-04-15).
        try:
            self.redis.queue_notion_sync(task.task_id, {"action": "sync"}, user_id=str(get_current_user_id() or 1))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notion queue failed during skip_task: {e}", exc_info=True)

        return task
    
    def delete_task(self, task_id: str) -> Task:
        """
        Delete a task (soft delete - mark as DELETED).
        
        Args:
            task_id: Task to delete
            
        Returns:
            Updated task
        """
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        
        if task.state in (TaskState.EXECUTED, TaskState.DELETED):
            raise ImmutableTaskError("Cannot delete immutable task")
        
        task = self.state_machine.transition(task, TaskState.DELETED)
        
        # Sync delete state to Notion (archive the page)
        try:
            if task.notion_page_id:
                self.notion.archive_page(task.notion_page_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notion archive failed during delete_task: {e}", exc_info=True)
            self.redis.queue_notion_sync(task.task_id, {"action": "archive"}, user_id=str(get_current_user_id() or 1))
        
        # Cache for undo — best-effort, Redis may be unavailable in some environments
        try:
            state_value = task.state.value if hasattr(task.state, 'value') else str(task.state)
            self.redis.cache_undo_action("delete_task", task.task_id, {
                "task_id": task.task_id,
                "title": task.title,
                "previous_state": state_value
            }, user_id=str(get_current_user_id() or 1))
        except Exception:
            pass

        return task
    
    def swap_tasks(self, task_a_id: str, task_b_id: str) -> tuple["Task", "Task"]:
        """
        Atomically swap a SKIPPED task and a PLANNED task.

        The SKIPPED task is reactivated as PLANNED at the other task's time slot.
        The PLANNED task is marked SKIPPED with initiation_status='user_skipped'.

        Intentionally bypasses state machine immutability — this is the only
        operation allowed to do so, and only for SKIPPED↔PLANNED pairs.
        """
        task_a = self.db.query(Task).filter(Task.task_id == task_a_id).first()
        task_b = self.db.query(Task).filter(Task.task_id == task_b_id).first()
        if not task_a:
            raise ValueError(f"Task {task_a_id} not found")
        if not task_b:
            raise ValueError(f"Task {task_b_id} not found")

        if task_a.voided_at is not None:
            raise ValueError(f"Task {task_a_id} is voided")
        if task_b.voided_at is not None:
            raise ValueError(f"Task {task_b_id} is voided")

        states = {task_a.state, task_b.state}
        if states != {TaskState.SKIPPED, TaskState.PLANNED}:
            raise ValueError("swap requires exactly one SKIPPED task and one PLANNED task")

        skipped = task_a if task_a.state == TaskState.SKIPPED else task_b
        planned = task_b if task_a.state == TaskState.SKIPPED else task_a

        # Snapshot the planned task's slot before mutating anything
        new_start = planned.planned_start_utc
        new_end = planned.planned_end_utc
        new_duration = planned.planned_duration_minutes

        # Reactivate the SKIPPED task — adopt the planned slot, clear execution data
        skipped.state = TaskState.PLANNED
        skipped.planned_start_utc = new_start
        skipped.planned_end_utc = new_end
        skipped.planned_duration_minutes = new_duration
        skipped.executed_start_utc = None
        skipped.executed_end_utc = None
        skipped.executed_duration_minutes = None
        skipped.initiation_status = "not_started"
        skipped.pre_task_readiness = None
        skipped.post_task_reflection = None
        skipped.last_modified_at = now_utc()

        # Mark the formerly-planned task as user-skipped
        planned.state = TaskState.SKIPPED
        planned.initiation_status = "user_skipped"
        planned.last_modified_at = now_utc()

        self.db.commit()
        self.db.refresh(skipped)
        self.db.refresh(planned)

        for t in (skipped, planned):
            try:
                self.notion.sync_task(t, db=self.db)
            except Exception as e:
                logger.error(f"Notion sync failed on swap for {t.task_id}: {e}", exc_info=True)
                try:
                    self.redis.queue_notion_sync(t.task_id, {"action": "sync"}, user_id=str(get_current_user_id() or 1))
                except Exception:
                    pass

        return skipped, planned

    def reschedule_task(
        self,
        task_id: str,
        new_start: datetime,
        new_end: Optional[datetime] = None,
        title: Optional[str] = None,
        category: Optional[str] = None,
    ) -> tuple[Task, list[Task]]:
        """
        Reschedule a task (preserves TaskID).
        
        Args:
            task_id: Task to reschedule
            new_start: New start time (UTC)
            new_end: New end time (UTC), or None to preserve duration
            
        Returns:
            (updated_task, conflicts)
        """
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        if task.voided_at is not None:
            raise ValueError("Cannot reschedule a voided task")

        if not task.is_mutable:
            raise ImmutableTaskError("Cannot reschedule immutable task")
        
        # Convert naive local times (Cairo) to UTC before storing
        new_start = to_utc(new_start)

        if new_end is None:
            duration = task.planned_end_utc - task.planned_start_utc
            new_end = new_start + duration
        else:
            new_end = to_utc(new_end)

        # Check for conflicts (excluding current task). Reschedule keeps its
        # legacy permissive behavior — conflicts are reported but the move
        # proceeds. Severity-based gating is /v1/create scope per Path A;
        # adding it to /v1/reschedule would also tighten calendar drag/resize
        # in ways that need their own browser-verify pass.
        conflicts = self.conflict_detector.detect(
            new_start,
            new_end,
            exclude_task_id=task.task_id,
        ).all_conflicts()
        
        # Update task
        task.planned_start_utc = new_start
        task.planned_end_utc = new_end
        task.planned_duration_minutes = int((new_end - new_start).total_seconds() / 60)
        if title is not None:
            task.title = title
        if category is not None:
            task.category = category
        task.reschedule_count = (task.reschedule_count or 0) + 1
        task.last_modified_at = now_utc()
        self.db.commit()
        self.db.refresh(task)
        
        # Notion sync deferred to Redis queue (P0 latency fix 2026-04-15).
        try:
            self.redis.queue_notion_sync(task.task_id, {"action": "sync"}, user_id=str(get_current_user_id() or 1))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notion queue failed during reschedule_task: {e}", exc_info=True)

        try:
            self.redis.set_last_task(task.task_id, task.title, task.state.value if hasattr(task.state, "value") else str(task.state), user_id=str(get_current_user_id() or 1))
        except Exception:
            pass
        return task, conflicts
