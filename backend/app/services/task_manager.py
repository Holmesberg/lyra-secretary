"""
Task Manager - SINGLE MUTATION AUTHORITY.

ALL task modifications MUST go through this service.
No other service should modify Task objects directly.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

import logging

from app.db.models import Task, TaskState, TaskSource, CategoryMapping
from app.db.scoping import get_current_user_id
from app.services.parser import TaskParser
from app.services.state_machine import StateMachine
from app.services.conflict_detector import ConflictDetector
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

    def create_task(
        self,
        title: str,
        start: datetime,
        end: datetime,
        category: Optional[str] = None,
        state: TaskState = TaskState.PLANNED,
        source: TaskSource = TaskSource.MANUAL,
        confidence_score: Optional[float] = None,
        force_conflicts: bool = False
    ) -> tuple[Optional[Task], list[Task], bool]:
        """
        Create a new task.
        
        Args:
            title: Task title
            start: Start time (UTC)
            end: End time (UTC)
            category: Optional category
            state: Initial state (default PLANNED)
            source: How task was created
            confidence_score: Parser confidence
            force_conflicts: Ignore conflicts if True
            
        Returns:
            (created_task, conflicts)
            If conflicts exist and not forced: (None, conflicts)
        """
        # Convert naive local times (Cairo) to UTC before storing
        start = to_utc(start)
        end = to_utc(end)

        # P4: Reject tasks with start time in the past (5 min buffer)
        if start < now_utc() - timedelta(minutes=5):
            raise ValueError("start_in_past: Task start time is in the past. Did you mean tomorrow?")

        # Detect conflicts
        conflicts = self.conflict_detector.detect(start, end)
        
        if conflicts and not force_conflicts:
            return None, conflicts, False
        
        # Auto-infer category from title if not provided
        if not category:
            category = self._infer_category(title)

        # Calculate duration
        duration_minutes = int((end - start).total_seconds() / 60)
        
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
            created_at=created_at_ts,
            last_modified_at=created_at_ts,
            session_index_in_day=self._compute_session_index(start, created_at_ts),
            user_id=uid,
        )
        
        self.db.add(task)
        self.db.flush()  # Get task_id
        self.db.commit()
        self.db.refresh(task)
        
        # Sync to Notion (non-blocking)
        notion_synced = False
        try:
            self.notion.sync_task(task, db=self.db)
            notion_synced = True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notion sync failed during create_task: {e}", exc_info=True)
            self.redis.queue_notion_sync(task.task_id, {"action": "sync"}, user_id=str(get_current_user_id() or 1))
        
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
        
        # Sync to Notion
        try:
            self.notion.sync_task(task, db=self.db)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notion sync failed during start_task: {e}", exc_info=True)
            self.redis.queue_notion_sync(task.task_id, {"action": "sync"}, user_id=str(get_current_user_id() or 1))
        
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
        task = self.state_machine.transition(task, TaskState.EXECUTED)
        
        # Sync to Notion
        notion_synced = False
        try:
            self.notion.sync_task(task, db=self.db)
            notion_synced = True
        except Exception as e:
            logger.error(f"Notion sync failed during complete_task: {e}", exc_info=True)
            try:
                self.redis.queue_notion_sync(task.task_id, {"action": "sync"}, user_id=str(get_current_user_id() or 1))
            except Exception:
                pass

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
        
        # Sync to Notion
        try:
            self.notion.sync_task(task, db=self.db)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notion sync failed during skip_task: {e}", exc_info=True)
            self.redis.queue_notion_sync(task.task_id, {"action": "sync"}, user_id=str(get_current_user_id() or 1))
        
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

        # Check for conflicts (excluding current task)
        conflicts = self.conflict_detector.detect(
            new_start,
            new_end,
            exclude_task_id=task.task_id
        )
        
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
        
        # Sync to Notion
        try:
            self.notion.sync_task(task, db=self.db)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notion sync failed during reschedule_task: {e}", exc_info=True)
            try:
                self.redis.queue_notion_sync(task.task_id, {"action": "sync"}, user_id=str(get_current_user_id() or 1))
            except Exception:
                pass

        try:
            self.redis.set_last_task(task.task_id, task.title, task.state.value if hasattr(task.state, "value") else str(task.state), user_id=str(get_current_user_id() or 1))
        except Exception:
            pass
        return task, conflicts
