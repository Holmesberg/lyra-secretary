"""Stopwatch lifecycle management with Redis."""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import StopwatchSession, Task, TaskState
from app.services.task_manager import TaskManager
from app.utils.redis_client import RedisClient
from app.utils.time_utils import now_utc

class StopwatchAlreadyRunningError(Exception):
    pass

class NoActiveStopwatchError(Exception):
    pass

class StopwatchAlreadyPausedError(Exception):
    pass

class StopwatchNotPausedError(Exception):
    pass


class StopwatchManager:
    """Manage stopwatch sessions with Redis persistence."""

    def __init__(self, db: Session):
        self.db = db
        self.redis = RedisClient()
        self.task_manager = TaskManager(db)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_active(self, user_id: str) -> Optional[dict]:
        active = self.redis.get_active_stopwatch(user_id)
        if not active:
            active = self._recover_from_db(user_id)
        return active

    def _get_session(self, session_id: str) -> StopwatchSession:
        session = self.db.query(StopwatchSession).filter(
            StopwatchSession.session_id == session_id
        ).first()
        if not session:
            raise NoActiveStopwatchError("Stopwatch session not found in database")
        return session

    def _active_elapsed(self, session: StopwatchSession, pause_state: Optional[dict]) -> int:
        """Elapsed minutes of active work (excludes all paused time)."""
        now = now_utc()
        total = int((now - session.start_time_utc).total_seconds() / 60)
        total -= session.total_paused_minutes
        if pause_state:
            paused_at = datetime.fromisoformat(pause_state["paused_at"])
            current_pause = int((now - paused_at).total_seconds() / 60)
            total -= current_pause
        return max(0, total)

    def check_early_stop(self, user_id: str = "user_primary") -> tuple[bool, int, int]:
        """
        Check if stopping now would be an early stop (< 50% of planned).

        Returns (is_early_stop, active_elapsed_minutes, planned_minutes).
        Does NOT stop the timer.
        """
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
        session = self.db.query(StopwatchSession).filter(
            StopwatchSession.end_time_utc == None
        ).first()

        if not session:
            return None

        task = self.db.query(Task).filter(Task.task_id == session.task_id).first()
        if not task:
            return None

        self.redis.set_active_stopwatch(
            user_id=user_id,
            session_id=session.session_id,
            task_id=task.task_id,
            title=task.title,
            start_time=session.start_time_utc.isoformat()
        )

        # Recover pause state too if session was paused
        if session.paused_at_utc and not self.redis.get_pause_state(user_id):
            self.redis.set_pause_state(user_id, session.session_id, session.paused_at_utc.isoformat())

        return self.redis.get_active_stopwatch(user_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(
        self,
        task_id: Optional[str] = None,
        title: Optional[str] = None,
        user_id: str = "user_primary",
        pre_task_readiness: Optional[int] = None,
        interruption_type: Optional[str] = None,
    ) -> tuple[StopwatchSession, Task, bool]:
        """Start stopwatch. Returns (session, task, is_future_task).

        If the current stopwatch is PAUSED, the new task is linked as an
        interruption via parent_task_id. The paused session stays in DB
        (unclosed) and can be resumed later.
        """
        active = self._get_active(user_id)
        paused_task_id = None

        if active:
            pause_state = self.redis.get_pause_state(user_id)
            if pause_state:
                # Current timer is paused — allow starting a new task
                paused_task_id = active["task_id"]
                # Clear active stopwatch from Redis (DB session stays unclosed)
                self.redis.clear_active_stopwatch(user_id)
                self.redis.clear_pause_state(user_id)
            else:
                raise StopwatchAlreadyRunningError(
                    f"Stopwatch already running for task {active['task_id']}"
                )

        if task_id:
            task = self.db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                raise ValueError("Task not found")
            task = self.task_manager.start_task(task_id)
        else:
            if not title:
                raise ValueError("Title required for unplanned task")
            now = now_utc()
            task, _, _ = self.task_manager.create_task(
                title=title,
                start=now,
                end=now + timedelta(hours=1),
                state=TaskState.EXECUTING
            )

        is_future_task = False
        if hasattr(task, "planned_start_utc") and task.planned_start_utc:
            if task.planned_start_utc > now_utc() + timedelta(minutes=5):
                is_future_task = True

        actual_start = now_utc()
        session = StopwatchSession(
            task_id=task.task_id,
            start_time_utc=actual_start,
            auto_closed=False,
            total_paused_minutes=0,
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

        self.db.commit()
        self.db.refresh(session)
        self.db.refresh(task)

        self.redis.set_active_stopwatch(
            user_id=user_id,
            session_id=session.session_id,
            task_id=task.task_id,
            title=task.title,
            start_time=session.start_time_utc.isoformat()
        )

        return session, task, is_future_task

    def pause(
        self,
        user_id: str = "user_primary",
        pause_reason: Optional[str] = None,
        pause_initiator: Optional[str] = None,
    ) -> dict:
        """Pause the active stopwatch. Stores pause timestamp in DB and Redis."""
        active = self._get_active(user_id)
        if not active:
            raise NoActiveStopwatchError("No active stopwatch")

        if self.redis.get_pause_state(user_id):
            raise StopwatchAlreadyPausedError("Stopwatch is already paused")

        session = self._get_session(active["session_id"])
        now = now_utc()
        elapsed = self._active_elapsed(session, None)

        session.paused_at_utc = now
        if pause_reason:
            session.pause_reason = pause_reason
        if pause_initiator:
            session.pause_initiator = pause_initiator
        self.db.commit()

        self.redis.set_pause_state(user_id, session.session_id, now.isoformat())

        return {
            "paused": True,
            "elapsed_minutes": elapsed,
            "paused_at": now,
            "pause_reason": pause_reason,
            "pause_initiator": pause_initiator,
        }

    def resume(self, user_id: str = "user_primary") -> dict:
        """Resume a paused stopwatch. Accumulates paused duration."""
        active = self._get_active(user_id)
        if not active:
            raise NoActiveStopwatchError("No active stopwatch")

        pause_state = self.redis.get_pause_state(user_id)
        if not pause_state:
            raise StopwatchNotPausedError("Stopwatch is not paused")

        now = now_utc()
        paused_at = datetime.fromisoformat(pause_state["paused_at"])
        pause_duration = int((now - paused_at).total_seconds() / 60)

        session = self._get_session(active["session_id"])
        task = self.db.query(Task).filter(Task.task_id == session.task_id).first()

        session.total_paused_minutes += pause_duration
        session.paused_at_utc = None
        task.pause_count = (task.pause_count or 0) + 1

        self.db.commit()
        self.redis.clear_pause_state(user_id)

        return {
            "resumed": True,
            "paused_minutes": pause_duration,
            "total_paused_minutes": session.total_paused_minutes,
        }

    def stop(
        self,
        user_id: str = "user_primary",
        post_task_reflection: Optional[int] = None,
    ) -> tuple[StopwatchSession, Task, bool, bool]:
        """
        Stop active stopwatch. Returns (session, task, is_early_stop, notion_synced).

        If paused when stop is called, auto-resumes first (final pause counted).
        Subtracts total_paused_minutes from executed_duration so delta only
        reflects active work time.

        If no active stopwatch but post_task_reflection is provided, updates the
        most recently completed task (within 10 min) — supports the two-call pattern.
        """
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
                    self.db.commit()
                    self.db.refresh(task)
                    session = (
                        self.db.query(StopwatchSession)
                        .filter(StopwatchSession.task_id == task.task_id)
                        .order_by(StopwatchSession.end_time_utc.desc())
                        .first()
                    )
                    return session, task, False, True
                raise NoActiveStopwatchError(
                    "No active stopwatch and no recent task to update reflection"
                )
            else:
                raise NoActiveStopwatchError("No active stopwatch")

        session = self._get_session(active["session_id"])
        task = self.db.query(Task).filter(Task.task_id == session.task_id).first()
        if not task:
            raise ValueError("Task not found")

        stop_time = now_utc()

        # If paused, auto-resume: count final pause duration
        pause_state = self.redis.get_pause_state(user_id)
        if pause_state:
            paused_at = datetime.fromisoformat(pause_state["paused_at"])
            final_pause = int((stop_time - paused_at).total_seconds() / 60)
            session.total_paused_minutes += final_pause
            session.paused_at_utc = None
            task.pause_count = (task.pause_count or 0) + 1
            self.redis.clear_pause_state(user_id)

        # Capture total_paused before complete_task() overwrites task
        total_paused = session.total_paused_minutes

        # Early stop check on active work time
        active_elapsed = self._active_elapsed(session, None)  # pause already cleared above
        is_early_stop = False
        if task.planned_duration_minutes and task.planned_duration_minutes > 0:
            if active_elapsed < (task.planned_duration_minutes * 0.5):
                is_early_stop = True

        session.end_time_utc = stop_time
        self.db.add(session)

        # complete_task() sets executed_duration = (end - start).minutes (wall clock)
        task, notion_synced = self.task_manager.complete_task(
            task_id=task.task_id,
            executed_start=session.start_time_utc,
            executed_end=stop_time,
        )

        # Deduct paused time so delta reflects only active work
        if total_paused > 0:
            task.executed_duration_minutes = max(
                0, (task.executed_duration_minutes or 0) - total_paused
            )
            self.db.commit()
            self.db.refresh(task)

        if post_task_reflection is not None:
            task.post_task_reflection = post_task_reflection
            self.db.commit()
            self.db.refresh(task)

        self.redis.clear_active_stopwatch(user_id)

        return session, task, is_early_stop, notion_synced

    def correct_readiness(
        self,
        pre_task_readiness: int,
        user_id: str = "user_primary",
    ) -> dict:
        """Correct pre_task_readiness on the active session. No time limit."""
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
        self.db.refresh(task)

        return {"corrected": True, "original": original, "new": pre_task_readiness}

    def get_status(self, user_id: str = "user_primary") -> Optional[dict]:
        """Get current stopwatch status including pause state."""
        active = self.redis.get_active_stopwatch(user_id)
        if not active:
            return None

        session = self.db.query(StopwatchSession).filter(
            StopwatchSession.session_id == active["session_id"]
        ).first()

        pause_state = self.redis.get_pause_state(user_id)
        total_paused = session.total_paused_minutes if session else 0
        is_paused = pause_state is not None

        start_time = datetime.fromisoformat(active["start_time"])
        # elapsed = active work time only (current pause not counted until resumed)
        elapsed_minutes = self._active_elapsed(session, pause_state) if session else (
            max(0, int((now_utc() - start_time).total_seconds() / 60) - total_paused)
        )

        return {
            "active": True,
            "session_id": active["session_id"],
            "task_id": active["task_id"],
            "task_title": active["title"],
            "start_time": start_time,
            "elapsed_minutes": elapsed_minutes,
            "paused": is_paused,
            "total_paused_minutes": total_paused,
        }
