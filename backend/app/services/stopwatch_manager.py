"""Stopwatch lifecycle management with Redis."""
from datetime import datetime, timedelta
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import Session

import logging

import uuid

from app.db.models import PauseEvent, StopwatchSession, Task, TaskState
from app.core.exceptions import InvalidStateTransitionError
from app.services.active_stopwatch_store import ActiveStopwatchStore
from app.services.interruption_metrics import task_interruption_metrics
from app.services.stopwatch_reflections import (
    _compute_calibration_nudge as _reflection_compute_calibration_nudge,
    _compute_micro_mirror as _reflection_compute_micro_mirror,
    _derive_current_pause_anchor as _reflection_derive_current_pause_anchor,
)
from app.services.task_manager import TaskManager
from app.utils.tasks_range_cache import invalidate_user_ranges
from app.utils.redis_client import RedisClient
from app.utils.time_utils import now_utc, to_local, strip_tz

logger = logging.getLogger(__name__)

class StopwatchAlreadyRunningError(Exception):
    pass

class NoActiveStopwatchError(Exception):
    pass

class StopwatchAlreadyPausedError(Exception):
    pass

class StopwatchNotPausedError(Exception):
    pass


STALE_PAUSE_RESOLUTION_HOURS = 72
STALE_PAUSE_RESOLUTION_FLAG = "user_resolved_stale_pause"
STALE_PAUSE_TASK_STATUS = "stale_resolved"


def _compute_micro_mirror(task: Task, interruption_metrics=None) -> Optional[str]:
    """One-line behavioral observation on stop. Priority: initiation > delta > pauses.

    Text is deliberately neutral — no evaluative framing ("strong focus",
    "fragmented"). Mirror-not-judge per docs/design_patterns/notification_patterns.md
    §No guilt and MANIFESTO.md §Shipping Philosophy (narrative layer must not
    become a judgment layer; VT-21 candidate).
    """
    return _reflection_compute_micro_mirror(task, interruption_metrics)


def _compute_calibration_nudge(task: Task, db: Session) -> Optional[str]:
    """Reference-class forecast for same-category EXECUTED history.

    Fires at n >= 3. This threshold is Phase 4.5's pre-registered floor —
    chosen over n >= 5 to give trusted users usable feedback during the
    cold-start window (3-7 day trusted-user engagement loop). Reconsider
    at alpha based on observed signal stability. Any change is a new
    pre-registration with its own window start.

    Filter notes:
      - `Task.executed_duration_minutes.is_not(None)` stands in for the
        delta filter: `Task.duration_delta_minutes` is a Python `@property`
        computed from planned/executed, not a mapped column, so it cannot
        be used in a SQL WHERE clause (SQLAlchemy silently resolves it to
        a Python bool, producing a no-op filter). The property returns
        None iff executed_duration_minutes is None, so filtering on the
        underlying column is semantically equivalent.
      - `Task.initiation_status != "system_error"` drops NULL rows under
        SQL tri-value logic. Verified safe 2026-04-15: zero production
        rows have NULL initiation_status (0/118). Production values are
        'initiated' and 'retroactive'; all non-system_error.
    """
    return _reflection_compute_calibration_nudge(task, db)


class StopwatchManager:
    """Manage stopwatch sessions with Redis persistence."""

    def __init__(self, db: Session):
        self.db = db
        self.redis = RedisClient()
        self.task_manager = TaskManager(db)
        self.active_store = ActiveStopwatchStore(
            db=db,
            redis=self.redis,
            invalidate_task_ranges=self._invalidate_task_ranges,
        )

    @staticmethod
    def _user_key() -> str:
        """Redis namespace key derived from the authenticated user.

        Phase 3.2 discovered that using a static "user_primary" key for
        all users leaked one user's active timer into another's status
        response. Now every Redis stopwatch key is namespaced to the
        numeric user_id from the scoping ContextVar.
        """
        from app.db.scoping import get_current_user_id
        uid = get_current_user_id()
        if uid is None:
            raise RuntimeError(
                "StopwatchManager._user_key: no current_user_id — "
                "refusing redis lookup without tenant context."
            )
        return str(uid)

    @staticmethod
    def _invalidate_task_ranges(user_id: str | int) -> None:
        try:
            invalidate_user_ranges(int(user_id))
        except Exception as exc:  # noqa: BLE001 - cache invalidation is best effort
            logger.warning(
                "stopwatch_manager: task range cache invalidation failed for user %s: %s",
                user_id,
                type(exc).__name__,
            )

    def _clear_terminal_stopwatch_state(self, user_id: str) -> None:
        """Best-effort cache cleanup after terminal DB truth has committed."""
        try:
            self.redis.clear_stopwatch_state(user_id)
        except Exception as exc:  # noqa: BLE001 - DB terminal state is canonical
            logger.warning(
                "stopwatch.stop: terminal Redis cleanup failed for user %s: %s",
                user_id,
                type(exc).__name__,
            )

    def _publish_committed_start(
        self,
        *,
        user_id: str,
        session: StopwatchSession,
        task: Task,
    ) -> None:
        """Best-effort Redis publication after start truth has committed."""
        try:
            self.redis.activate_stopwatch(
                user_id=user_id,
                session_id=session.session_id,
                task_id=task.task_id,
                title=task.title,
                start_time=session.start_time_utc.isoformat(),
            )
        except Exception as exc:  # noqa: BLE001 - DB start state is canonical
            logger.warning(
                "stopwatch.start: Redis publication failed for user %s: %s",
                user_id,
                type(exc).__name__,
            )

    def _publish_committed_pause(
        self,
        *,
        user_id: str,
        session: StopwatchSession,
        paused_at: datetime,
    ) -> None:
        """Best-effort Redis publication after pause truth has committed."""
        try:
            self.redis.set_pause_state(
                user_id,
                session.session_id,
                paused_at.isoformat(),
            )
        except Exception as exc:  # noqa: BLE001 - DB pause state is canonical
            logger.warning(
                "stopwatch.pause: Redis publication failed for user %s: %s",
                user_id,
                type(exc).__name__,
            )

    def _clear_committed_resume_pause_state(self, user_id: str) -> None:
        """Best-effort Redis cleanup after resume truth has committed."""
        try:
            self.redis.clear_pause_state(user_id)
        except Exception as exc:  # noqa: BLE001 - DB resume state is canonical
            logger.warning(
                "stopwatch.resume: Redis cleanup failed for user %s: %s",
                user_id,
                type(exc).__name__,
            )

    def _publish_committed_switch(
        self,
        *,
        user_id: str,
        session: StopwatchSession,
        task: Task,
    ) -> None:
        """Best-effort Redis publication after switch truth has committed."""
        try:
            self.redis.activate_stopwatch(
                user_id=user_id,
                session_id=session.session_id,
                task_id=task.task_id,
                title=task.title,
                start_time=session.start_time_utc.isoformat(),
            )
        except Exception as exc:  # noqa: BLE001 - DB switch state is canonical
            logger.warning(
                "stopwatch.switch: Redis publication failed for user %s: %s",
                user_id,
                type(exc).__name__,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_active(self, user_id: str) -> Optional[dict]:
        return self.active_store.get_active(user_id)

    def _close_orphan_session(self, session_id: str) -> None:
        """Close an unclosed StopwatchSession without touching task metrics.

        Used when a task was voided out from under an active session — we
        just want the row marked closed so _recover_from_db stops finding
        it. No duration/delta math, no micro-mirror, no external sync.

        Also closes any open pause_event rows for this session (resumed_at_utc
        IS NULL) so pause-history analytics don't see dangling opens. The
        session's auto_closed=True flag on the parent row is the data-quality
        signal — analytics filtering on clean data should exclude auto-closed
        sessions rather than filtering open/closed pause_events directly.
        """
        self.active_store.close_orphan_session(session_id)

    def _close_open_pause_events(self, session_id: str, closed_at: datetime) -> None:
        """Close any PauseEvent rows for this session that are still open.

        Called from orphan/stale cleanup paths. Sets resumed_at_utc=closed_at
        and computes duration_minutes from paused_at_utc. Does not commit —
        caller owns the transaction.
        """
        self.active_store.close_open_pause_events(session_id, closed_at)

    def void_cleanup(self, task_id: str) -> None:
        """Clear stopwatch state bound to a task that is being voided.

        Called by the /v1/tasks/{id}/void endpoint so the frontend banner
        disappears on the next status poll instead of waiting for the
        _get_active self-heal path. Closes any unclosed StopwatchSession
        bound to this task_id and clears Redis active/pause state if it
        points at this task.
        """
        user_id = self._user_key()
        self.active_store.void_cleanup(task_id=task_id, user_id=user_id)

    def _get_session(self, session_id: str) -> StopwatchSession:
        session = self.db.query(StopwatchSession).filter(
            StopwatchSession.session_id == session_id
        ).first()
        if not session:
            raise NoActiveStopwatchError("Stopwatch session not found in database")
        return session

    def _active_elapsed(self, session: StopwatchSession, pause_state: Optional[dict]) -> int:
        """Elapsed minutes of active work (excludes all paused time).

        Float-seconds arithmetic then convert to int minutes at the end so
        sub-minute pauses don't truncate to zero (LYR-094). The integer
        return preserves the existing early-stop gate and status payload.
        """
        return self._active_elapsed_seconds(session, pause_state) // 60

    def _active_elapsed_seconds(self, session: StopwatchSession, pause_state: Optional[dict]) -> int:
        """Same as _active_elapsed but returns seconds (LYR-111).

        The status payload exposes both. Banner uses seconds as its tick
        basis so resume-after-swap doesn't snap to the last whole minute.

        Tz hotfix (2026-04-28): strip_tz on every datetime reaching the
        subtraction — Supabase TIMESTAMPTZ + Redis-ISO-with-offset both
        produce aware datetimes that crash against now_utc()'s naive
        return. See time_utils.strip_tz docstring.
        """
        now = now_utc()
        session_start = strip_tz(session.start_time_utc)
        total_seconds = (now - session_start).total_seconds() if session_start else 0.0
        paused_seconds = (session.total_paused_minutes or 0.0) * 60.0
        if pause_state:
            paused_at = strip_tz(datetime.fromisoformat(pause_state["paused_at"]))
            paused_seconds += (now - paused_at).total_seconds()
        active_seconds = max(0.0, total_seconds - paused_seconds)
        return int(active_seconds)

    def check_early_stop(self) -> tuple[bool, int, int]:
        """
        Check if stopping now would be an early stop (< 50% of planned).

        Returns (is_early_stop, active_elapsed_minutes, planned_minutes).
        Does NOT stop the timer.
        """
        user_id = self._user_key()
        active = self._get_active(user_id)
        if not active:
            return False, 0, 0

        session = self._get_session(active["session_id"])
        pause_state = self.redis.get_pause_state(user_id)
        elapsed = self._active_elapsed(session, pause_state)

        task = self.db.query(Task).filter(Task.task_id == active["task_id"]).first()
        planned = task.planned_duration_minutes if task and task.planned_duration_minutes else 0

        is_early = planned > 0 and elapsed < (planned * 0.5)
        return is_early, elapsed, planned

    def _recover_from_db(self, user_id: str) -> Optional[dict]:
        """Rehydrate Redis active_stopwatch from DB after Redis loss/eviction.

        Multi-tasking awareness (Apr 25 fix): with the swap endpoint, a user
        can have multiple open StopwatchSessions at once — one per task that
        was paused-mid-work. The currently-active task is the one whose
        Task.state is EXECUTING; all other open sessions belong to PAUSED
        tasks (interruption parents or post-swap source tasks).

        Recovery priority:
          1. Find the unique session whose task is in state==EXECUTING.
             That's unambiguously the user's active stopwatch.
          2. If no executing task exists, fall back to the PAUSED task with
             the most recent paused_at_utc (the user's last interaction).
             Rehydrate Redis pause_state too in that case.
          3. If neither exists, return None — no recoverable state.

        Pre-fix bug: ordered by start_time_utc.DESC, which after multi-tasking
        could pick the most-recently-started session (likely the child of an
        interruption flow) even when the user had already switched back to
        the parent. That left Redis pointing at a PAUSED task while another
        task was actually EXECUTING — the swap chip then disappeared because
        get_paused_others excludes the Redis-active session.
        """
        return self.active_store.recover_from_db(user_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(
        self,
        task_id: Optional[str] = None,
        title: Optional[str] = None,
        pre_task_readiness: Optional[int] = None,
        interruption_type: Optional[str] = None,
    ) -> tuple[StopwatchSession, Task, bool]:
        """Start stopwatch. Returns (session, task, is_future_task).

        If the current stopwatch is PAUSED, the new task is linked as an
        interruption via parent_task_id. If the current stopwatch is running,
        callers must pass interruption_type; the running task is paused with
        pause_reason='task_switch' before the child starts. The parent session
        stays in DB (unclosed) and can be resumed later.
        """
        user_id = self._user_key()
        active = self._get_active(user_id)
        active_before_start = dict(active) if active else None
        pause_state_before_start = self.redis.get_pause_state(user_id) if active else None
        parent_pause_state_after_switch = None
        paused_task_id = None
        target_task = None
        undo_task_snapshot = None

        if task_id:
            target_task = self.db.query(Task).filter(Task.task_id == task_id).first()
            if not target_task:
                raise ValueError("Task not found")
            if target_task.voided_at is not None:
                raise ValueError("Cannot start a timer on a voided task")
        elif not title:
            raise ValueError("Title required for unplanned task")

        if active:
            if task_id and active["task_id"] == task_id:
                session = self._get_session(active["session_id"])
                task = target_task or self.db.query(Task).filter(
                    Task.task_id == active["task_id"]
                ).first()
                if task is None or task.voided_at is not None or session.end_time_utc is not None:
                    self.redis.clear_stopwatch_state(user_id)
                    raise StopwatchAlreadyRunningError(
                        f"Stopwatch state for task {active['task_id']} is stale"
                    )
                is_future_task = False
                if task.planned_start_utc and task.planned_start_utc > now_utc() + timedelta(minutes=5):
                    is_future_task = True
                return session, task, is_future_task
            pause_state = self.redis.get_pause_state(user_id)
            if pause_state:
                # Current timer is paused — allow starting a new task
                paused_task_id = active["task_id"]
                # Clear active stopwatch from Redis (DB session stays unclosed)
                self.redis.clear_stopwatch_state(user_id)
            else:
                if not interruption_type:
                    raise StopwatchAlreadyRunningError(
                        f"Stopwatch already running for task {active['task_id']}"
                    )
                if target_task is not None and not self.task_manager.state_machine.can_transition(
                    target_task, TaskState.EXECUTING
                ):
                    state = (
                        target_task.state.value
                        if hasattr(target_task.state, "value")
                        else str(target_task.state)
                    )
                    raise InvalidStateTransitionError(
                        f"Cannot transition from {state} to {TaskState.EXECUTING.value}"
                    )
                self.pause(pause_reason="task_switch", pause_initiator="self")
                paused_task_id = active["task_id"]
                parent_pause_state_after_switch = self.redis.get_pause_state(user_id)
                self.redis.clear_stopwatch_state(user_id)

        if task_id:
            undo_task_snapshot = {
                "state": (
                    target_task.state.value
                    if hasattr(target_task.state, "value")
                    else str(target_task.state)
                ),
                "pre_task_readiness": target_task.pre_task_readiness,
                "initiation_status": target_task.initiation_status,
                "initiation_delay_minutes": target_task.initiation_delay_minutes,
                "parent_task_id": target_task.parent_task_id,
                "interruption_type": target_task.interruption_type,
            }
            task = self.task_manager.start_task(task_id)
            created_task_for_start = False
        else:
            # create_task() expects Cairo local time (calls to_utc internally)
            local_now = to_local(now_utc())
            task, _, _ = self.task_manager.create_task(
                title=title,
                start=local_now,
                end=local_now + timedelta(hours=1),
                state=TaskState.EXECUTING
            )
            created_task_for_start = True

        is_future_task = False
        if hasattr(task, "planned_start_utc") and task.planned_start_utc:
            if task.planned_start_utc > now_utc() + timedelta(minutes=5):
                is_future_task = True

        actual_start = now_utc()
        from app.db.scoping import get_current_user_id
        uid = get_current_user_id()
        if uid is None:
            raise RuntimeError(
                "stopwatch.start: no current_user_id in ContextVar — refusing to write."
            )
        session = StopwatchSession(
            task_id=task.task_id,
            start_time_utc=actual_start,
            auto_closed=False,
            total_paused_minutes=0,
            user_id=uid,
        )
        self.db.add(session)
        self.db.flush()

        task.pre_task_readiness = pre_task_readiness
        task.initiation_status = "initiated"
        if paused_task_id:
            task.parent_task_id = paused_task_id
            task.interruption_type = interruption_type or "unknown"
        if task.planned_start_utc:
            delay = int((actual_start - task.planned_start_utc).total_seconds() / 60)
            task.initiation_delay_minutes = delay
        self.db.add(task)

        # Alpha funnel (alembic 037, 2026-04-28): first_timer_started_at
        # stamp, lazy-once. Drives the North Star metric task_created +
        # timer_started within first 3 min via /v1/analytics/alpha_funnel.
        try:
            from app.db.models import User
            u = self.db.query(User).filter(User.user_id == uid).first()
            if u is not None and u.first_timer_started_at is None:
                u.first_timer_started_at = actual_start
        except Exception as e:
            logger.warning(f"first_timer_started_at stamp failed (non-blocking): {e}")

        self.db.commit()
        self._invalidate_task_ranges(user_id)
        self.db.refresh(session)
        self.db.refresh(task)

        # A status poll can recover the paused parent from DB after the old
        # Redis state is cleared but before this child is published. Activate
        # the child and clear any recovered parent pause marker atomically so
        # the child cannot inherit the parent's paused state.
        self._publish_committed_start(user_id=user_id, session=session, task=task)
        try:
            self.redis.cache_undo_action(
                "start_stopwatch",
                session.session_id,
                {
                    "task_id": task.task_id,
                    "title": task.title,
                    "session_id": session.session_id,
                    "created_task": created_task_for_start,
                    "task_snapshot": undo_task_snapshot,
                    "active_before_start": active_before_start,
                    "pause_state_before_start": pause_state_before_start,
                    "parent_pause_state_after_switch": parent_pause_state_after_switch,
                },
                user_id=user_id,
            )
            # A task may have been created moments before it was started.
            # The visible undo surface is now "undo timer start"; do not leave
            # an older hidden task-creation undo key competing with it.
            self.redis.clear_undo_data(task.task_id, user_id=user_id)
        except Exception as e:
            logger.warning("stopwatch.start: undo cache write failed: %s", e)

        return session, task, is_future_task

    def pause(
        self,
        pause_reason: str,
        pause_initiator: str,
    ) -> dict:
        """Pause the active stopwatch. Stores pause timestamp in DB and Redis.

        Both pause_reason and pause_initiator are required — no silent
        defaults. The stopwatch_session columns are preserved (latest-
        pause-wins behavior, used by overflow-check pathways), but the
        authoritative per-pause record is the pause_event row inserted
        here. Multi-pause sessions keep all their history in pause_event.
        """
        if not pause_reason or not pause_initiator:
            # Defense-in-depth: the API schema already enforces this, but a
            # direct caller must not slip a silent default past the service
            # boundary. Hard Rules 3/4/5.
            raise ValueError(
                "pause_reason and pause_initiator are required; "
                "silent defaults removed per do_not_add.md §Hardcoded default values"
            )

        user_id = self._user_key()
        active = self._get_active(user_id)
        if not active:
            raise NoActiveStopwatchError("No active stopwatch")

        existing_pause_state = self.redis.get_pause_state(user_id)
        if existing_pause_state:
            session = self._get_session(existing_pause_state.get("session_id") or active["session_id"])
            paused_at_raw = existing_pause_state.get("paused_at")
            paused_at = (
                strip_tz(datetime.fromisoformat(paused_at_raw))
                if paused_at_raw
                else strip_tz(session.paused_at_utc)
            )
            return {
                "paused": True,
                "elapsed_minutes": self._active_elapsed(session, existing_pause_state),
                "paused_at": paused_at or now_utc(),
                "pause_reason": session.pause_reason or pause_reason,
                "pause_initiator": session.pause_initiator or pause_initiator,
            }

        session = self._get_session(active["session_id"])
        now = now_utc()
        elapsed = self._active_elapsed(session, None)

        session.paused_at_utc = now
        session.pause_reason = pause_reason
        session.pause_initiator = pause_initiator

        # Per-pause immutable history — replaces the overwrite-on-second-pause
        # data loss in the legacy schema (see migration 020 docstring).
        total_sec = (now - session.start_time_utc).total_seconds()
        paused_sec = (session.total_paused_minutes or 0.0) * 60.0
        active_elapsed_sec = int(max(0.0, total_sec - paused_sec))
        pause_event = PauseEvent(
            pause_event_id=str(uuid.uuid4()),
            session_id=session.session_id,
            user_id=session.user_id,
            paused_at_utc=now,
            pause_reason=pause_reason,
            pause_initiator=pause_initiator,
            active_elapsed_at_pause_seconds=active_elapsed_sec,
        )
        self.db.add(pause_event)

        # Transition task state EXECUTING → PAUSED. Inline state mutation
        # instead of state_machine.transition() to avoid its per-call
        # commit+refresh round-trip — we bundle everything into a single
        # commit below. The transition is already validated: the state
        # machine permits EXECUTING → PAUSED unconditionally, and the
        # pause endpoint already rejected non-EXECUTING callers via
        # get_pause_state + the active check above.
        task = self.db.query(Task).filter(Task.task_id == session.task_id).first()
        if task and task.state == TaskState.EXECUTING:
            task.state = TaskState.PAUSED
            task.last_modified_at = now

        # Single commit for session update + pause_event insert + task
        # state transition. One fsync instead of two — halves the SQLite
        # write latency on the pause path.
        self.db.commit()
        self._invalidate_task_ranges(user_id)
        self._publish_committed_pause(
            user_id=user_id,
            session=session,
            paused_at=now,
        )

        return {
            "paused": True,
            "elapsed_minutes": elapsed,
            "paused_at": now,
            "pause_reason": session.pause_reason,
            "pause_initiator": session.pause_initiator,
        }

    def resume(self) -> dict:
        """Resume a paused stopwatch. Accumulates paused duration."""
        user_id = self._user_key()
        active = self._get_active(user_id)
        if not active:
            raise NoActiveStopwatchError("No active stopwatch")

        pause_state = self.redis.get_pause_state(user_id)
        if not pause_state:
            session = self._get_session(active["session_id"])
            return {
                "resumed": True,
                "paused_minutes": 0.0,
                "total_paused_minutes": session.total_paused_minutes or 0.0,
            }

        now = now_utc()
        # strip_tz: Redis-stored ISO may parse to aware (see time_utils).
        paused_at = strip_tz(datetime.fromisoformat(pause_state["paused_at"]))
        # Float minutes — no sub-minute truncation (LYR-094).
        pause_duration = (now - paused_at).total_seconds() / 60.0

        # LYR-106 guard: timestamp-integrity invariant. A negative
        # pause_duration means resumed_at < paused_at — physically
        # impossible. Day-18 sweep found one production row (u=5,
        # pe=a3c8629f, -12.02 min). Root cause was clock-skew or a
        # mid-session timezone change in pause_state's paused_at ISO
        # string. Clamping to zero (rather than rejecting outright)
        # preserves the resume action for the user; logging the surrounding
        # state lets future occurrences be diagnosed. Either: clock skew
        # in the client→server pipeline, OR ContextVar drift between
        # pause and resume calls in the same session. The 5-second
        # tolerance prevents tiny clock-drift normal-cases from logging.
        if pause_duration < -5.0 / 60.0:
            logger.error(
                f"LYR-106: negative pause duration detected — "
                f"now={now.isoformat()} paused_at={paused_at.isoformat()} "
                f"computed_duration={pause_duration:.4f} min, "
                f"session_id={active.get('session_id', '?')} "
                f"user_id={user_id} task_id={active.get('task_id')}. Clamping to 0."
            )
        if pause_duration < 0:
            pause_duration = 0.0

        session = self._get_session(active["session_id"])
        task = self.db.query(Task).filter(Task.task_id == session.task_id).first()

        session.total_paused_minutes += pause_duration
        session.paused_at_utc = None
        task.pause_count = (task.pause_count or 0) + 1

        # Close the open pause_event row for this pause. Matches on the most
        # recent paused_at_utc to handle legacy rows or clock-skew edge cases
        # where paused_at_utc on the session drifted from the pause_event.
        open_event = (
            self.db.query(PauseEvent)
            .filter(
                PauseEvent.session_id == session.session_id,
                PauseEvent.resumed_at_utc.is_(None),
            )
            .order_by(PauseEvent.paused_at_utc.desc())
            .first()
        )
        if open_event:
            open_event.resumed_at_utc = now
            open_event.duration_minutes = pause_duration

        # Transition task state PAUSED → EXECUTING inline (see pause()
        # rationale — single-commit avoids the extra fsync).
        if task.state == TaskState.PAUSED:
            task.state = TaskState.EXECUTING
            task.last_modified_at = now

        # Single commit for session + task + pause_event close.
        self.db.commit()
        self._invalidate_task_ranges(user_id)
        self._clear_committed_resume_pause_state(user_id)

        return {
            "resumed": True,
            "paused_minutes": pause_duration,
            "total_paused_minutes": session.total_paused_minutes,
        }

    def switch_to_task(self, target_task_id: str) -> dict:
        """Atomically switch the active stopwatch to a different paused task.

        Multi-tasking swap (Apr 25): when the operator has run a task as an
        interruption (parent paused with open session, child executing), the
        only way back to the parent was previously to stop the child. This
        method enables direct swap — pause whatever's currently running,
        resume the target — in a single transaction.

        Pre-conditions:
          * Target task exists, belongs to the current user (auto-scoped),
            voided_at IS NULL
          * Target task state is PAUSED
          * Target task has an open StopwatchSession (i.e., paused mid-work,
            not just a planned task that's never been started)

        Effects (single atomic commit):
          * If currently EXECUTING task X exists in Redis: pause X (insert
            pause_event with reason='task_switch', set X.state=PAUSED,
            update session.paused_at_utc). Don't increment X.pause_count
            (matches existing pause() convention — count is incremented on
            resume).
          * If currently PAUSED task X exists in Redis: just clear Redis
            (X is already PAUSED in DB; no double pause_event).
          * If no current active: nothing to pause.
          * In all cases: resume the target — close target's open
            pause_event with resumed_at, accumulate pause duration into
            session.total_paused_minutes, set target.state=EXECUTING,
            increment target.pause_count, swap Redis active_stopwatch.

        Edge cases handled:
          * Target == current active (idempotency): if target is also paused
            in Redis, falls through to a regular resume(). Otherwise no-op
            success. Prevents double-clicks from breaking state.
          * Source voided since Redis was set: detect, skip the pause step
            (nothing legitimate to pause), proceed with target resume.
          * Target has no open session: reject — caller should /start the
            task instead of /switch.
          * Target not in PAUSED state: reject (only paused tasks are valid
            switch destinations).
          * Voided target: reject.
          * State machine: EXECUTING→PAUSED and PAUSED→EXECUTING are both
            permitted unconditionally per state_machine.py:20-27, so direct
            mutation is safe (matches the pause()/resume() convention of
            inline state transitions to avoid a second commit-fsync).
        """
        user_id = self._user_key()
        now = now_utc()

        # ---- Validate target ----
        target = self.db.query(Task).filter(Task.task_id == target_task_id).first()
        if not target:
            raise ValueError("Target task not found")
        if target.voided_at is not None:
            raise ValueError("Cannot switch to a voided task")
        if target.state != TaskState.PAUSED:
            raise ValueError(
                f"Target task must be PAUSED to switch (current state: "
                f"{target.state.name if hasattr(target.state, 'name') else target.state})"
            )
        target_session = (
            self.db.query(StopwatchSession)
            .filter(
                StopwatchSession.task_id == target_task_id,
                StopwatchSession.end_time_utc.is_(None),
            )
            .order_by(StopwatchSession.start_time_utc.desc())
            .first()
        )
        if not target_session:
            raise ValueError(
                "Target task has no open session — start it instead of switching"
            )

        # ---- Resolve current active ----
        active = self.redis.get_active_stopwatch(user_id)

        # Idempotency: target is currently the active task.
        if active and active.get("task_id") == target_task_id:
            # If target is paused (Redis pause_state), resume it normally.
            if self.redis.get_pause_state(user_id):
                resume_result = self.resume()
                return {
                    "switched": True,
                    "noop": False,
                    "from_task_id": None,
                    "from_session_id": None,
                    "to_task_id": target_task_id,
                    "to_session_id": active.get("session_id") or target_session.session_id,
                    "to_title": target.title,
                    "to_start_time": target_session.start_time_utc,
                    "target_pause_duration_minutes": resume_result.get(
                        "paused_minutes", 0.0
                    ),
                }
            # Already executing this task — no-op.
            return {
                "switched": True,
                "noop": True,
                "from_task_id": None,
                "from_session_id": None,
                "to_task_id": target_task_id,
                "to_session_id": active.get("session_id") or target_session.session_id,
                "to_title": target.title,
                "to_start_time": target_session.start_time_utc,
                "target_pause_duration_minutes": 0.0,
            }

        # ---- Pause the source (if any) ----
        source_task_id = None
        source_session_id = None
        if active:
            source_session_id = active.get("session_id")
            source_session = (
                self.db.query(StopwatchSession)
                .filter(StopwatchSession.session_id == source_session_id)
                .first()
            )
            source_task = self.db.query(Task).filter(
                Task.task_id == active.get("task_id")
            ).first()

            # Source could have been voided/terminal-stated since Redis was
            # set (race with /tasks/{id}/void or mark_abandoned). In that
            # case skip the pause step — there's nothing legitimate to
            # pause — and proceed straight to resuming target. The voided
            # task's session was already closed by void_cleanup.
            if source_task and source_task.voided_at is None and source_session:
                source_task_id = source_task.task_id
                source_pause_state = self.redis.get_pause_state(user_id)

                if source_pause_state:
                    # Source is already paused — Redis pause_state exists,
                    # state.PAUSED already in DB, pause_event already open.
                    # Don't insert a duplicate pause_event; the swap is
                    # purely a Redis-pointer change for source.
                    pass
                else:
                    # Source is EXECUTING — pause it now.
                    source_session.paused_at_utc = now
                    source_session.pause_reason = "task_switch"
                    source_session.pause_initiator = "self"

                    total_sec = (now - source_session.start_time_utc).total_seconds()
                    paused_sec = (source_session.total_paused_minutes or 0.0) * 60.0
                    active_elapsed_sec = int(max(0.0, total_sec - paused_sec))

                    pause_event = PauseEvent(
                        pause_event_id=str(uuid.uuid4()),
                        session_id=source_session.session_id,
                        user_id=source_session.user_id,
                        paused_at_utc=now,
                        pause_reason="task_switch",
                        pause_initiator="self",
                        active_elapsed_at_pause_seconds=active_elapsed_sec,
                    )
                    self.db.add(pause_event)

                    if source_task.state == TaskState.EXECUTING:
                        source_task.state = TaskState.PAUSED
                        source_task.last_modified_at = now

        # ---- Resume the target ----
        # Find target's open pause_event (created when target was paused
        # for interruption or by a previous switch). Close it.
        target_open_event = (
            self.db.query(PauseEvent)
            .filter(
                PauseEvent.session_id == target_session.session_id,
                PauseEvent.resumed_at_utc.is_(None),
            )
            .order_by(PauseEvent.paused_at_utc.desc())
            .first()
        )
        target_pause_duration = 0.0
        if target_open_event:
            target_pause_duration = (
                (now - target_open_event.paused_at_utc).total_seconds() / 60.0
            )
            target_open_event.resumed_at_utc = now
            target_open_event.duration_minutes = target_pause_duration
            target_session.total_paused_minutes = (
                target_session.total_paused_minutes or 0.0
            ) + target_pause_duration
        target_session.paused_at_utc = None

        target.state = TaskState.EXECUTING
        target.last_modified_at = now
        target.pause_count = (target.pause_count or 0) + 1

        # ---- Single atomic commit for source-pause + target-resume ----
        self.db.commit()
        self._invalidate_task_ranges(user_id)

        # ---- Publish the committed target to Redis ----
        self._publish_committed_switch(
            user_id=user_id,
            session=target_session,
            task=target,
        )
        return {
            "switched": True,
            "noop": False,
            "from_task_id": source_task_id,
            "from_session_id": source_session_id,
            "to_task_id": target.task_id,
            "to_session_id": target_session.session_id,
            "to_title": target.title,
            "to_start_time": target_session.start_time_utc,
            "target_pause_duration_minutes": target_pause_duration,
        }

    def get_paused_others(self) -> list[dict]:
        """Return paused-with-open-session tasks for this user that are NOT
        currently the active stopwatch.

        Used by the multi-tasking swap UX — each entry is a candidate the
        user can switch into via POST /v1/stopwatch/switch/{task_id}.
        Filters out voided tasks and any that aren't strictly state==PAUSED.

        Apr 26 perf fix: replaced N+1 (1 query for sessions + 1 query per
        session for the Task) with a single JOIN. Operator's Cairo→Supabase
        eu-west-1 RTT is ~100-200ms per query; with N paused sessions the
        old code added ~N×200ms to /v1/stopwatch/status (called every 10s
        by the frontend). Single JOIN cuts that to one round-trip.
        """
        user_id = self._user_key()
        active = self.redis.get_active_stopwatch(user_id)
        active_session_id = active.get("session_id") if active else None

        from app.db.scoping import get_current_user_id as _gcuid
        uid = _gcuid()
        if uid is None:
            return []

        # Single JOIN: pull the (session, task) pairs in one round-trip,
        # filtering at the SQL layer instead of per-row in Python.
        rows = (
            self.db.query(StopwatchSession, Task)
            .join(Task, Task.task_id == StopwatchSession.task_id)
            .filter(
                StopwatchSession.user_id == int(uid),
                StopwatchSession.end_time_utc.is_(None),
                Task.voided_at.is_(None),
                Task.state == TaskState.PAUSED,
            )
            .all()
        )

        others: list[dict] = []
        seen_task_ids: set[str] = set()
        for session, task in rows:
            if active_session_id and session.session_id == active_session_id:
                continue
            if session.task_id in seen_task_ids:
                # Defensive: a task with multiple open sessions (shouldn't
                # happen under normal flow). Surface only the most-recently-
                # paused one.
                continue
            # Strip tz defensively: Supabase may return aware datetimes
            # for these DateTime columns (TIMESTAMPTZ default). See
            # time_utils.strip_tz docstring.
            paused_at = strip_tz(session.paused_at_utc)
            session_start = strip_tz(session.start_time_utc)
            paused_mins = (
                int((now_utc() - paused_at).total_seconds() / 60)
                if paused_at else 0
            )
            # Active elapsed at the moment of the current pause — the
            # value the timer SHOULD show if the user resumes via swap.
            # Frontend uses this for the optimistic-mutation anchor so
            # the banner doesn't display 0:00 during the swap round-trip
            # (Apr 25: operator reported 16s "counting up from 0:00"
            # over Cloudflare Tunnel + Supabase before refetch reconciled).
            if paused_at and session_start:
                wall_sec = (paused_at - session_start).total_seconds()
                paused_sec = (session.total_paused_minutes or 0.0) * 60.0
                elapsed_sec = int(max(0.0, wall_sec - paused_sec))
                elapsed_min = elapsed_sec // 60
            else:
                elapsed_sec = 0
                elapsed_min = 0
            others.append({
                "task_id": task.task_id,
                "title": task.title,
                "session_id": session.session_id,
                "paused_minutes": paused_mins,
                "elapsed_minutes": elapsed_min,
                "elapsed_seconds": elapsed_sec,
                "start_time": session.start_time_utc.isoformat() if session.start_time_utc else None,
                "total_paused_minutes": session.total_paused_minutes or 0.0,
                "planned_duration_minutes": task.planned_duration_minutes,
            })
            seen_task_ids.add(session.task_id)

        # Stable order: most recently paused first (intuitive for the chip
        # row — "the thing I just paused" appears leftmost).
        others.sort(key=lambda x: -x["paused_minutes"])
        return others

    def stop(
        self,
        post_task_reflection: Optional[int] = None,
        task_completion_percentage: Optional[int] = None,
        scope_outcome: Optional[str] = None,
    ) -> tuple:
        """
        Stop active stopwatch. Returns (session, task, is_early_stop, legacy_external_sync,
        paused_parent, micro_mirror, calibration_nudge, mid_task_completion_pct).

        mid_task_completion_pct is the pre-existing completion % on the session
        (set during an overrun check-in via update-completion), or None if not set.

        If paused when stop is called, auto-resumes first (final pause counted).
        Subtracts total_paused_minutes from executed_duration so delta only
        reflects active work time.

        If no active stopwatch but post_task_reflection is provided, updates the
        most recently completed task (within 10 min) — supports the two-call pattern.
        """
        user_id = self._user_key()
        active = self.redis.get_active_stopwatch(user_id)
        if not active:
            recovered = self._recover_from_db(user_id)
            if recovered:
                active = recovered
            elif post_task_reflection is not None:
                cutoff = now_utc() - timedelta(minutes=10)
                task = (
                    self.db.query(Task)
                    .filter(Task.state == TaskState.EXECUTED, Task.executed_end_utc >= cutoff)
                    .order_by(Task.executed_end_utc.desc())
                    .first()
                )
                if task:
                    task.post_task_reflection = post_task_reflection
                    if scope_outcome is not None:
                        task.scope_outcome = scope_outcome
                    self.db.commit()
                    self._invalidate_task_ranges(task.user_id)
                    self.db.refresh(task)
                    session = (
                        self.db.query(StopwatchSession)
                        .filter(StopwatchSession.task_id == task.task_id)
                        .order_by(StopwatchSession.end_time_utc.desc())
                        .first()
                    )
                    if session and task_completion_percentage is not None:
                        session.task_completion_percentage = task_completion_percentage
                        self.db.commit()
                        self._invalidate_task_ranges(task.user_id)
                        self.db.refresh(session)
                    return session, task, False, True, None, None, None, None
                raise NoActiveStopwatchError(
                    "No active stopwatch and no recent task to update reflection"
                )
            else:
                raise NoActiveStopwatchError("No active stopwatch")

        session = self._get_session(active["session_id"])
        task = self.db.query(Task).filter(Task.task_id == session.task_id).first()
        if not task:
            raise ValueError("Task not found")
        if task.voided_at is not None:
            # Task was voided mid-session — clean up stopwatch state, don't complete.
            self.redis.clear_stopwatch_state(user_id)
            session.end_time_utc = now_utc()
            session.auto_closed = True
            self.db.commit()
            self._invalidate_task_ranges(user_id)
            raise ValueError("Task was voided — session auto-closed without completion")

        stop_time = now_utc()

        # If paused, auto-resume: count final pause duration
        pause_state = self.redis.get_pause_state(user_id)
        if pause_state:
            paused_at = strip_tz(datetime.fromisoformat(pause_state["paused_at"]))
            final_pause = (stop_time - paused_at).total_seconds() / 60.0  # float
            session.total_paused_minutes += final_pause
            session.paused_at_utc = None
            task.pause_count = (task.pause_count or 0) + 1
            self.redis.clear_pause_state(user_id)

        # If task is PAUSED in state machine, force-resume to EXECUTING before complete_task
        # (complete_task transitions EXECUTING → EXECUTED)
        if task.state == TaskState.PAUSED:
            self.task_manager.state_machine.transition(task, TaskState.EXECUTING)

        # Capture total_paused before complete_task() overwrites task
        total_paused = session.total_paused_minutes

        # Early stop check on active work time
        active_elapsed = self._active_elapsed(session, None)  # pause already cleared above
        is_early_stop = False
        if task.planned_duration_minutes and task.planned_duration_minutes > 0:
            if active_elapsed < (task.planned_duration_minutes * 0.5):
                is_early_stop = True

        # Zero-duration guard: no active work → SKIPPED, not EXECUTED.
        # BUT: if the user reports high completion (>= 80%), the task was
        # genuinely finished faster than the 60-second floor of
        # _active_elapsed — route to EXECUTED so delta is captured.
        # Without this override, every "planned long, executed short,
        # completed fully" session is miscategorized as SKIPPED and the
        # negative-delta signal (the most behaviorally interesting) is
        # silently destroyed. (P0 fix, Apr 12.)
        if active_elapsed == 0 and not (
            task_completion_percentage is not None
            and task_completion_percentage >= 80
        ):
            pre_existing_pct = session.task_completion_percentage
            session.end_time_utc = stop_time
            if task_completion_percentage is not None:
                session.task_completion_percentage = task_completion_percentage
            # LYR-105: close any lingering open pause_event so VT-17
            # aggregations see a complete pair. Redis pause_state is
            # cleared above (line ~676); the PauseEvent row was written
            # by the original pause call and still has resumed_at_utc
            # NULL. Helper is idempotent (no-op when no open rows).
            self._close_open_pause_events(session.session_id, stop_time)
            self.db.add(session)
            task.state = TaskState.SKIPPED
            task.initiation_status = "abandoned"
            task.last_modified_at = now_utc()
            self.db.commit()
            self._invalidate_task_ranges(user_id)
            self.db.refresh(session)
            self.db.refresh(task)
            self._clear_terminal_stopwatch_state(user_id)
            return session, task, is_early_stop, False, None, None, None, pre_existing_pct

        session.end_time_utc = stop_time
        # LYR-105: same invariant on the normal stop path. Helper is
        # idempotent — no-op when the session has no open pause_event.
        self._close_open_pause_events(session.session_id, stop_time)
        self.db.add(session)

        # complete_task() sets executed_duration = (end - start).minutes (wall clock)
        task, _legacy_external_sync = self.task_manager.complete_task(
            task_id=task.task_id,
            executed_start=session.start_time_utc,
            executed_end=stop_time,
        )

        # Deduct paused time so delta reflects only active work. Round here
        # — duration_delta_minutes downstream is an int column.
        if total_paused > 0:
            task.executed_duration_minutes = max(
                0, (task.executed_duration_minutes or 0) - int(round(total_paused))
            )
            self.task_manager.reconcile_calibration_nudge_outcome(
                task.task_id,
                int(task.executed_duration_minutes or 0),
            )
            self.db.commit()
            self._invalidate_task_ranges(user_id)
            self.db.refresh(task)

        if post_task_reflection is not None:
            task.post_task_reflection = post_task_reflection
        if scope_outcome is not None:
            task.scope_outcome = scope_outcome
        if post_task_reflection is not None or scope_outcome is not None:
            self.db.commit()
            self._invalidate_task_ranges(user_id)
            self.db.refresh(task)

        pre_existing_pct = session.task_completion_percentage
        if task_completion_percentage is not None:
            session.task_completion_percentage = task_completion_percentage
            self.db.commit()
            self._invalidate_task_ranges(user_id)
            self.db.refresh(session)

        interruption = task_interruption_metrics(self.db, task)
        micro_mirror = _compute_micro_mirror(task, interruption)
        calibration_nudge = _compute_calibration_nudge(task, self.db)

        self._clear_terminal_stopwatch_state(user_id)

        # Check for any paused parent session still open
        paused_parent = None
        orphan = (
            self.db.query(StopwatchSession)
            .filter(
                StopwatchSession.paused_at_utc != None,
                StopwatchSession.end_time_utc == None,
                StopwatchSession.task_id != task.task_id,
            )
            .first()
        )
        if orphan:
            parent_task = self.db.query(Task).filter(Task.task_id == orphan.task_id).first()
            if parent_task:
                paused_at = strip_tz(orphan.paused_at_utc)
                paused_mins = int((now_utc() - paused_at).total_seconds() / 60) if paused_at else 0
                paused_parent = {
                    "task_id": parent_task.task_id,
                    "title": parent_task.title,
                    "paused_minutes": paused_mins,
                }

        return session, task, is_early_stop, False, paused_parent, micro_mirror, calibration_nudge, pre_existing_pct

    def resolve_stale_pause(
        self,
        session_id: str,
        *,
        post_task_reflection: int,
        task_completion_percentage: int,
        scope_outcome: str,
        threshold_hours: int = STALE_PAUSE_RESOLUTION_HOURS,
    ) -> dict:
        """Close a long-paused session using explicit user reflection.

        This is intentionally not the normal stop path: the user is resolving a
        stale parked session after the fact. The session closes at the original
        pause timestamp, active duration excludes pauses, and the session is
        marked dirty so it stays out of clean calibration baselines.
        """
        if not 1 <= int(post_task_reflection) <= 5:
            raise ValueError("post_task_reflection must be between 1 and 5")
        if not 0 <= int(task_completion_percentage) <= 100:
            raise ValueError("task_completion_percentage must be between 0 and 100")
        if scope_outcome not in {"stuck_to_plan", "expanded", "reduced"}:
            raise ValueError("Invalid scope_outcome")

        user_id = self._user_key()
        user_id_int = int(user_id)
        now = now_utc()
        cutoff = now - timedelta(hours=threshold_hours)

        session = (
            self.db.query(StopwatchSession)
            .filter(
                StopwatchSession.session_id == session_id,
                StopwatchSession.user_id == user_id_int,
            )
            .first()
        )
        if session is None:
            raise ValueError("Stale pause session not found")
        if session.end_time_utc is not None:
            raise ValueError("Stale pause session is already closed")
        if session.paused_at_utc is None:
            raise ValueError("Only paused sessions can be resolved this way")

        paused_at = strip_tz(session.paused_at_utc)
        if paused_at > cutoff:
            raise ValueError(
                f"Pause must be at least {threshold_hours}h old before stale resolution"
            )

        task = (
            self.db.query(Task)
            .filter(Task.task_id == session.task_id, Task.user_id == user_id_int)
            .first()
        )
        if task is None or task.voided_at is not None:
            raise ValueError("Task not found")
        if task.state not in (
            TaskState.PAUSED,
            TaskState.EXECUTING,
            TaskState.SKIPPED,
        ):
            raise ValueError(
                "Only PAUSED, EXECUTING, or stale-recovered SKIPPED tasks can "
                f"be resolved this way (current state: {task.state})"
            )
        if task.state == TaskState.SKIPPED and task.initiation_status not in (
            "abandoned",
            "orphaned_recovery",
            "auto_abandoned",
            STALE_PAUSE_TASK_STATUS,
        ):
            raise ValueError("Only stale/abandoned skipped tasks can be resolved this way")

        end_time = paused_at

        open_events = (
            self.db.query(PauseEvent)
            .filter(
                PauseEvent.session_id == session.session_id,
                PauseEvent.resumed_at_utc.is_(None),
            )
            .all()
        )
        for evt in open_events:
            evt.resumed_at_utc = max(strip_tz(evt.paused_at_utc), end_time)
            evt.duration_minutes = max(
                0.0,
                (evt.resumed_at_utc - strip_tz(evt.paused_at_utc)).total_seconds()
                / 60.0,
            )
        self.db.flush()

        event_pause_total = float(
            self.db.query(sa.func.coalesce(sa.func.sum(PauseEvent.duration_minutes), 0))
            .filter(PauseEvent.session_id == session.session_id)
            .scalar()
            or 0
        )
        total_pause_minutes = max(float(session.total_paused_minutes or 0), event_pause_total)
        active_minutes = max(
            0,
            int(round((end_time - strip_tz(session.start_time_utc)).total_seconds() / 60.0 - total_pause_minutes)),
        )

        session.end_time_utc = end_time
        session.paused_at_utc = None
        session.total_paused_minutes = total_pause_minutes
        session.task_completion_percentage = int(task_completion_percentage)
        session.data_quality_flag = STALE_PAUSE_RESOLUTION_FLAG
        session.auto_closed = False

        task.post_task_reflection = int(post_task_reflection)
        task.scope_outcome = scope_outcome
        task.last_modified_at = now

        if task_completion_percentage >= 80:
            task.state = TaskState.EXECUTED
            task.executed_start_utc = strip_tz(session.start_time_utc)
            task.executed_end_utc = end_time
            task.executed_duration_minutes = active_minutes
            task.initiation_status = STALE_PAUSE_TASK_STATUS
        else:
            task.state = TaskState.SKIPPED
            task.executed_start_utc = strip_tz(session.start_time_utc)
            task.executed_end_utc = end_time
            task.executed_duration_minutes = active_minutes
            task.initiation_status = "abandoned"

        note = (
            "stale_pause_resolution: "
            f"session={session.session_id} "
            f"active_minutes={active_minutes} "
            f"completion={task_completion_percentage}% "
            f"focus={post_task_reflection} "
            f"scope={scope_outcome} "
            f"closed_at={end_time.isoformat()}"
        )
        task.notes = f"{task.notes or ''}\n{note}".strip()

        active = self.redis.get_active_stopwatch(user_id)
        if active and active.get("session_id") == session.session_id:
            self.redis.clear_stopwatch_state(user_id)
        pause_state = self.redis.get_pause_state(user_id)
        if pause_state and pause_state.get("session_id") == session.session_id:
            self.redis.clear_pause_state(user_id)

        self.db.commit()
        self.db.refresh(session)
        self.db.refresh(task)
        self._invalidate_task_ranges(user_id_int)

        return {
            "resolved": True,
            "task_id": task.task_id,
            "session_id": session.session_id,
            "new_state": task.state.value if hasattr(task.state, "value") else str(task.state),
            "active_minutes": active_minutes,
            "planned_duration_minutes": task.planned_duration_minutes,
            "paused_minutes": max(0, int(round((now - paused_at).total_seconds() / 60.0))),
            "task_completion_percentage": int(task_completion_percentage),
            "post_task_reflection": int(post_task_reflection),
            "scope_outcome": scope_outcome,
            "data_quality_flag": STALE_PAUSE_RESOLUTION_FLAG,
            "closed_at": to_local(session.end_time_utc),
        }

    def correct_readiness(
        self,
        pre_task_readiness: int,
    ) -> dict:
        """Correct pre_task_readiness on the active session. No time limit."""
        user_id = self._user_key()
        active = self._get_active(user_id)
        if not active:
            raise NoActiveStopwatchError("No active stopwatch")

        session = self._get_session(active["session_id"])
        task = self.db.query(Task).filter(Task.task_id == active["task_id"]).first()
        if not task:
            raise ValueError("Task not found")

        original = task.pre_task_readiness
        # Store original on session for audit trail (only first correction)
        if session.original_pre_task_readiness is None and original is not None:
            session.original_pre_task_readiness = original
        task.pre_task_readiness = pre_task_readiness
        self.db.commit()
        self._invalidate_task_ranges(user_id)
        self.db.refresh(task)

        return {"corrected": True, "original": original, "new": pre_task_readiness}

    def update_completion(self, task_completion_percentage: int) -> dict:
        """Update task_completion_percentage on the active session without stopping.

        Used by the timer overflow check-in flow: user reports progress mid-task
        without terminating the session. The value is preserved through to the
        eventual stop() call and recorded on the StopwatchSession row.
        """
        user_id = self._user_key()
        active = self._get_active(user_id)
        if not active:
            raise NoActiveStopwatchError("No active stopwatch")

        session = self._get_session(active["session_id"])
        task = self.db.query(Task).filter(Task.task_id == session.task_id).first()
        if task and task.voided_at is not None:
            raise ValueError("Cannot update completion on a voided task")
        session.task_completion_percentage = task_completion_percentage
        self.db.commit()
        self._invalidate_task_ranges(user_id)
        self.db.refresh(session)

        pause_state = self.redis.get_pause_state(user_id)
        elapsed = self._active_elapsed(session, pause_state)

        return {
            "updated": True,
            "task_id": active["task_id"],
            "task_title": active["title"],
            "task_completion_percentage": task_completion_percentage,
            "elapsed_minutes": elapsed,
        }

    def get_status(self) -> Optional[dict]:
        """Get current stopwatch status including pause state and paused_others.

        Uses _get_active() so Redis loss (restart, eviction) falls through
        to _recover_from_db() — prevents the banner-disappears-during-pause
        bug (LYR-095).

        Always returns a dict (never None now). When no active stopwatch,
        returns active=False but still populates paused_others — the
        multi-tasking UX needs to show "Other in-progress" candidates even
        from /today's empty state (e.g. user stops the child task; no
        active stopwatch; parent still PAUSED with open session and is
        resumable via /switch).
        """
        user_id = self._user_key()
        active = self._get_active(user_id)
        paused_others = self.get_paused_others()

        if not active:
            return {
                "active": False,
                "paused_others": paused_others,
            }

        session = self.db.query(StopwatchSession).filter(
            StopwatchSession.session_id == active["session_id"]
        ).first()

        pause_state = self.redis.get_pause_state(user_id)
        total_paused = session.total_paused_minutes if session else 0
        is_paused = pause_state is not None

        # Strip tz defensively: ISO strings stored in Redis may parse to
        # aware datetimes if the original isoformat included tz info.
        start_time = strip_tz(datetime.fromisoformat(active["start_time"]))
        # elapsed = active work time only (current pause not counted until resumed)
        if session:
            elapsed_seconds = self._active_elapsed_seconds(session, pause_state)
            elapsed_minutes = elapsed_seconds // 60
        else:
            # Sessionless fallback (recovery edge case) — minute-precision only.
            elapsed_minutes = max(
                0, int((now_utc() - start_time).total_seconds() / 60) - int(total_paused)
            )
            elapsed_seconds = elapsed_minutes * 60

        # When paused, expose how long the CURRENT pause has been running
        # (server-computed). Without this the frontend banner restarts the
        # "paused · MM:SS" counter from 00:00 every time the banner remounts
        # — which happens during multi-task swap, when the user stops one
        # task and recovery promotes the next paused task to active. Operator
        # observed this 2026-04-26 ("electronics paused early but counting
        # from 00:00 when I stopped the parallel task"). The active-work
        # elapsed (elapsed_seconds) was always correct; this fixes the
        # paused-duration display only.
        current_pause_seconds, current_pause_started_at = (
            _reflection_derive_current_pause_anchor(pause_state)
        )

        task = (
            self.db.query(Task)
            .filter(Task.task_id == active["task_id"])
            .first()
        )

        return {
            "active": True,
            "session_id": active["session_id"],
            "task_id": active["task_id"],
            "task_title": active["title"],
            "start_time": start_time,
            "elapsed_minutes": elapsed_minutes,
            "elapsed_seconds": elapsed_seconds,
            "planned_duration_minutes": (
                task.planned_duration_minutes if task is not None else None
            ),
            "paused": is_paused,
            "total_paused_minutes": total_paused,
            "current_pause_seconds": current_pause_seconds,
            "current_pause_started_at": current_pause_started_at,
            "paused_others": paused_others,
        }
