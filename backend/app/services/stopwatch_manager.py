"""Stopwatch lifecycle management with Redis."""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

import logging

from app.db.models import StopwatchSession, Task, TaskState
from app.services.task_manager import TaskManager
from app.utils.redis_client import RedisClient
from app.utils.time_utils import now_utc, to_local

logger = logging.getLogger(__name__)

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
        """Elapsed minutes of active work (excludes all paused time).

        Float-seconds arithmetic then convert to int minutes at the end so
        sub-minute pauses don't truncate to zero (LYR-094). The integer
        return preserves the existing early-stop gate and status payload.
        """
        now = now_utc()
        total_seconds = (now - session.start_time_utc).total_seconds()
        paused_seconds = (session.total_paused_minutes or 0.0) * 60.0
        if pause_state:
            paused_at = datetime.fromisoformat(pause_state["paused_at"])
            paused_seconds += (now - paused_at).total_seconds()
        active_seconds = max(0.0, total_seconds - paused_seconds)
        return int(active_seconds // 60)

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
        unclosed = self.db.query(StopwatchSession).filter(
            StopwatchSession.end_time_utc == None
        ).order_by(StopwatchSession.start_time_utc.desc()).all()

        if not unclosed:
            return None

        if len(unclosed) > 1:
            logger.warning(
                f"Multiple unclosed sessions found ({len(unclosed)}) — "
                f"recovering most recent. Others may be orphaned."
            )

        session = unclosed[0]

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
        pre_task_readiness: Optional[int] = None,
        interruption_type: Optional[str] = None,
    ) -> tuple[StopwatchSession, Task, bool]:
        """Start stopwatch. Returns (session, task, is_future_task).

        If the current stopwatch is PAUSED, the new task is linked as an
        interruption via parent_task_id. The paused session stays in DB
        (unclosed) and can be resumed later.
        """
        user_id = self._user_key()
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
            # create_task() expects Cairo local time (calls to_utc internally)
            local_now = to_local(now_utc())
            task, _, _ = self.task_manager.create_task(
                title=title,
                start=local_now,
                end=local_now + timedelta(hours=1),
                state=TaskState.EXECUTING
            )

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
        pause_reason: Optional[str] = None,
        pause_initiator: Optional[str] = None,
    ) -> dict:
        """Pause the active stopwatch. Stores pause timestamp in DB and Redis."""
        user_id = self._user_key()
        active = self._get_active(user_id)
        if not active:
            raise NoActiveStopwatchError("No active stopwatch")

        if self.redis.get_pause_state(user_id):
            raise StopwatchAlreadyPausedError("Stopwatch is already paused")

        session = self._get_session(active["session_id"])
        now = now_utc()
        elapsed = self._active_elapsed(session, None)

        session.paused_at_utc = now
        session.pause_reason = pause_reason or "intentional_break"
        session.pause_initiator = pause_initiator or "self"
        self.db.commit()

        # Transition task state EXECUTING → PAUSED + Notion sync
        task = self.db.query(Task).filter(Task.task_id == session.task_id).first()
        if task and task.state == TaskState.EXECUTING:
            self.task_manager.state_machine.transition(task, TaskState.PAUSED)
            try:
                self.task_manager.notion.sync_task(task, db=self.db)
            except Exception as e:
                logger.error(f"Notion sync failed on pause: {e}", exc_info=True)

        self.redis.set_pause_state(user_id, session.session_id, now.isoformat())

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
            raise StopwatchNotPausedError("Stopwatch is not paused")

        now = now_utc()
        paused_at = datetime.fromisoformat(pause_state["paused_at"])
        # Float minutes — no sub-minute truncation (LYR-094).
        pause_duration = (now - paused_at).total_seconds() / 60.0

        session = self._get_session(active["session_id"])
        task = self.db.query(Task).filter(Task.task_id == session.task_id).first()

        session.total_paused_minutes += pause_duration
        session.paused_at_utc = None
        task.pause_count = (task.pause_count or 0) + 1

        self.db.commit()

        # Transition task state PAUSED → EXECUTING + Notion sync
        if task.state == TaskState.PAUSED:
            self.task_manager.state_machine.transition(task, TaskState.EXECUTING)
            try:
                self.task_manager.notion.sync_task(task, db=self.db)
            except Exception as e:
                logger.error(f"Notion sync failed on resume: {e}", exc_info=True)

        self.redis.clear_pause_state(user_id)

        return {
            "resumed": True,
            "paused_minutes": pause_duration,
            "total_paused_minutes": session.total_paused_minutes,
        }

    def stop(
        self,
        post_task_reflection: Optional[int] = None,
        task_completion_percentage: Optional[int] = None,
    ) -> tuple[StopwatchSession, Task, bool, bool]:
        """
        Stop active stopwatch. Returns (session, task, is_early_stop, notion_synced).

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
                    self.db.commit()
                    self.db.refresh(task)
                    session = (
                        self.db.query(StopwatchSession)
                        .filter(StopwatchSession.task_id == task.task_id)
                        .order_by(StopwatchSession.end_time_utc.desc())
                        .first()
                    )
                    return session, task, False, True, None, None, None
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

        # Zero-duration guard: no active work → SKIPPED, not EXECUTED
        if active_elapsed == 0:
            session.end_time_utc = stop_time
            self.db.add(session)
            task.state = TaskState.SKIPPED
            task.initiation_status = "abandoned"
            task.last_modified_at = now_utc()
            self.db.commit()
            self.db.refresh(session)
            self.db.refresh(task)
            self.redis.clear_active_stopwatch(user_id)
            notion_synced_zero = False
            try:
                self.task_manager.notion.sync_task(task, db=self.db)
                notion_synced_zero = True
            except Exception as e:
                logger.error(f"Notion sync failed on zero-duration skip: {e}", exc_info=True)
            return session, task, True, notion_synced_zero, None, None, None

        session.end_time_utc = stop_time
        self.db.add(session)

        # complete_task() sets executed_duration = (end - start).minutes (wall clock)
        task, notion_synced = self.task_manager.complete_task(
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
            self.db.commit()
            self.db.refresh(task)

        if post_task_reflection is not None:
            task.post_task_reflection = post_task_reflection
            self.db.commit()
            self.db.refresh(task)

        if task_completion_percentage is not None:
            session.task_completion_percentage = task_completion_percentage
            self.db.commit()
            self.db.refresh(session)

        # Micro-mirror: one-line behavioral observation (priority: initiation > delta > pauses)
        micro_mirror = None
        delay = task.initiation_delay_minutes
        delta = task.duration_delta_minutes
        duration = task.executed_duration_minutes or 0
        pauses = task.pause_count or 0

        if delay is not None and delay > 10:
            micro_mirror = f"Started {delay} min late."
        elif delay is not None and delay <= 0:
            micro_mirror = "Started on time."
        elif delta is not None and delta < -20:
            micro_mirror = f"Ran {abs(delta)} min over plan."
        elif delta is not None and delta > 20:
            micro_mirror = f"Finished {delta} min early."
        elif pauses == 0 and duration > 30:
            micro_mirror = "No pauses — strong focus block."
        elif pauses >= 3:
            micro_mirror = f"{pauses} pauses — fragmented session."

        # Calibration nudge: reference class forecasting for same category (F6)
        calibration_nudge = None
        if task.category and delta is not None:
            history = (
                self.db.query(Task)
                .filter(
                    Task.category == task.category,
                    Task.state == TaskState.EXECUTED,
                    Task.initiation_status != "system_error",
                    Task.voided_at.is_(None),
                    Task.duration_delta_minutes != None,
                    Task.task_id != task.task_id,
                )
                .all()
            )
            n = len(history)
            if n >= 3:
                avg_delta = sum(t.duration_delta_minutes for t in history) / n
                underestimate_count = sum(1 for t in history if t.duration_delta_minutes < 0)
                direction = "over" if delta < 0 else "under"
                calibration_nudge = (
                    f"Ran {abs(delta)} min {direction} plan. "
                    f"Your {task.category} avg: {avg_delta:+.0f} min ({n} sessions). "
                    f"You've underestimated this category {underestimate_count}/{n} times."
                )

        self.redis.clear_active_stopwatch(user_id)

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
                paused_at = orphan.paused_at_utc
                paused_mins = int((now_utc() - paused_at).total_seconds() / 60) if paused_at else 0
                paused_parent = {
                    "task_id": parent_task.task_id,
                    "title": parent_task.title,
                    "paused_minutes": paused_mins,
                }

        return session, task, is_early_stop, notion_synced, paused_parent, micro_mirror, calibration_nudge

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
        self.db.refresh(task)

        return {"corrected": True, "original": original, "new": pre_task_readiness}

    def get_status(self) -> Optional[dict]:
        """Get current stopwatch status including pause state."""
        user_id = self._user_key()
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
