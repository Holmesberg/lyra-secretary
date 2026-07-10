"""Active stopwatch Redis/DB recovery and cleanup store."""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from sqlalchemy.orm import Session

from app.db.models import PauseEvent, StopwatchSession, Task, TaskState
from app.utils.redis_client import RedisClient
from app.utils.time_utils import now_utc


class ActiveStopwatchStore:
    """Own active stopwatch recovery and orphan cleanup.

    This collaborator is intentionally narrower than StopwatchManager. It does
    not start, pause, resume, stop, or finalize tasks; it only reconciles Redis
    active-state with open StopwatchSession rows.
    """

    def __init__(
        self,
        *,
        db: Session,
        redis: RedisClient,
        invalidate_task_ranges: Callable[[str | int], None],
    ) -> None:
        self.db = db
        self.redis = redis
        self.invalidate_task_ranges = invalidate_task_ranges

    def get_active(self, user_id: str) -> Optional[dict]:
        active = self.redis.get_active_stopwatch(user_id)
        if not active:
            active = self.recover_from_db(user_id)
        if active:
            # Self-heal: if the bound task has been voided or reached a
            # terminal state since the session started, close the orphan
            # session and clear Redis so the next status poll returns None.
            # Without this the frontend banner keeps showing a PAUSED timer
            # for a voided/skipped task forever. Originally only checked
            # voided_at (CO-block 65h incident); expanded to cover SKIPPED
            # after mark-abandoned left ghost banners (Apr 12).
            task = self.db.query(Task).filter(
                Task.task_id == active["task_id"]
            ).first()
            if task is None or task.voided_at is not None or task.state in (
                TaskState.SKIPPED, TaskState.EXECUTED, TaskState.DELETED,
            ):
                self.close_orphan_session(active["session_id"])
                self.redis.clear_stopwatch_state(user_id)
                return None
        return active

    def close_orphan_session(self, session_id: str) -> None:
        """Close an unclosed StopwatchSession without touching task metrics.

        Used when a task was voided out from under an active session; we just
        want the row marked closed so recover_from_db stops finding it. No
        duration/delta math, no micro-mirror, no external sync.

        Also closes any open pause_event rows for this session (resumed_at_utc
        IS NULL) so pause-history analytics don't see dangling opens. The
        session's auto_closed=True flag on the parent row is the data-quality
        signal; analytics filtering on clean data should exclude auto-closed
        sessions rather than filtering open/closed pause_events directly.
        """
        session = self.db.query(StopwatchSession).filter(
            StopwatchSession.session_id == session_id
        ).first()
        if session and session.end_time_utc is None:
            end = now_utc()
            session.end_time_utc = end
            session.auto_closed = True
            session.paused_at_utc = None
            self.close_open_pause_events(session_id, end)
            self.db.commit()
            self.invalidate_task_ranges(session.user_id)

    def close_open_pause_events(self, session_id: str, closed_at: datetime) -> None:
        """Close any PauseEvent rows for this session that are still open.

        Called from orphan/stale cleanup paths. Sets resumed_at_utc=closed_at
        and computes duration_minutes from paused_at_utc. Does not commit;
        caller owns the transaction.
        """
        open_events = (
            self.db.query(PauseEvent)
            .filter(
                PauseEvent.session_id == session_id,
                PauseEvent.resumed_at_utc.is_(None),
            )
            .all()
        )
        for evt in open_events:
            evt.resumed_at_utc = closed_at
            evt.duration_minutes = (
                (closed_at - evt.paused_at_utc).total_seconds() / 60.0
            )

    def void_cleanup(self, *, task_id: str, user_id: str) -> None:
        """Clear stopwatch state bound to a task that is being voided."""
        session = (
            self.db.query(StopwatchSession)
            .filter(
                StopwatchSession.task_id == task_id,
                StopwatchSession.end_time_utc.is_(None),
            )
            .first()
        )
        if session:
            self.close_orphan_session(session.session_id)
        active = self.redis.get_active_stopwatch(user_id)
        if active and active.get("task_id") == task_id:
            self.redis.clear_stopwatch_state(user_id)

    def recover_from_db(self, user_id: str) -> Optional[dict]:
        """Rehydrate Redis active_stopwatch from DB after Redis loss/eviction.

        Multi-tasking awareness (Apr 25 fix): with the swap endpoint, a user
        can have multiple open StopwatchSessions at once; one per task that was
        paused-mid-work. The currently-active task is the one whose Task.state
        is EXECUTING; all other open sessions belong to PAUSED tasks.

        Recovery priority:
          1. Find the unique session whose task is in state==EXECUTING.
          2. If no executing task exists, fall back to the PAUSED task with
             the most recent paused_at_utc and rehydrate pause_state.
          3. If neither exists, return None.
        """
        try:
            uid_int = int(user_id)
        except (TypeError, ValueError):
            return None

        executing_session = (
            self.db.query(StopwatchSession)
            .join(Task, Task.task_id == StopwatchSession.task_id)
            .filter(
                StopwatchSession.user_id == uid_int,
                StopwatchSession.end_time_utc.is_(None),
                Task.state == TaskState.EXECUTING,
                Task.voided_at.is_(None),
            )
            .order_by(StopwatchSession.start_time_utc.desc())
            .first()
        )

        if executing_session:
            task = self.db.query(Task).filter(
                Task.task_id == executing_session.task_id
            ).first()
            self.redis.activate_stopwatch(
                user_id=user_id,
                session_id=executing_session.session_id,
                task_id=task.task_id,
                title=task.title,
                start_time=executing_session.start_time_utc.isoformat(),
            )
            return self.redis.get_active_stopwatch(user_id)

        paused_session = (
            self.db.query(StopwatchSession)
            .join(Task, Task.task_id == StopwatchSession.task_id)
            .filter(
                StopwatchSession.user_id == uid_int,
                StopwatchSession.end_time_utc.is_(None),
                Task.state == TaskState.PAUSED,
                Task.voided_at.is_(None),
            )
            .order_by(StopwatchSession.paused_at_utc.desc())
            .first()
        )

        if paused_session:
            task = self.db.query(Task).filter(
                Task.task_id == paused_session.task_id
            ).first()
            if paused_session.paused_at_utc:
                self.redis.activate_paused_stopwatch(
                    user_id=user_id,
                    session_id=paused_session.session_id,
                    task_id=task.task_id,
                    title=task.title,
                    start_time=paused_session.start_time_utc.isoformat(),
                    paused_at=paused_session.paused_at_utc.isoformat(),
                )
            else:
                self.redis.activate_stopwatch(
                    user_id=user_id,
                    session_id=paused_session.session_id,
                    task_id=task.task_id,
                    title=task.title,
                    start_time=paused_session.start_time_utc.isoformat(),
                )
            return self.redis.get_active_stopwatch(user_id)

        return None
