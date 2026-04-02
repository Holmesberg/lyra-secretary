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

class StopwatchManager:
    """Manage stopwatch sessions with Redis persistence."""
    
    def __init__(self, db: Session):
        self.db = db
        self.redis = RedisClient()
        self.task_manager = TaskManager(db)

    def check_early_stop(self, user_id: str = "user_primary") -> tuple[bool, int, int]:
        """
        Check if stopping now would be an early stop (< 50% of planned).
        
        Returns (is_early_stop, elapsed_minutes, planned_minutes).
        Does NOT stop the timer.
        """
        active = self.redis.get_active_stopwatch(user_id)
        if not active:
            active = self._recover_from_db(user_id)
        if not active:
            return False, 0, 0

        start_time = datetime.fromisoformat(active['start_time'])
        elapsed = int((now_utc() - start_time).total_seconds() / 60)

        task = self.db.query(Task).filter(Task.task_id == active['task_id']).first()
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
        
        return self.redis.get_active_stopwatch(user_id)
    
    def start(
        self,
        task_id: Optional[str] = None,
        title: Optional[str] = None,
        user_id: str = "user_primary",
        pre_task_readiness: Optional[int] = None,
    ) -> tuple[StopwatchSession, Task, bool]:
        """
        Start stopwatch.
        
        Returns (session, task, is_future_task).
        """
        # Check for active stopwatch
        active = self.redis.get_active_stopwatch(user_id)
        if not active:
            active = self._recover_from_db(user_id)
            
        if active:
            raise StopwatchAlreadyRunningError(
                f"Stopwatch already running for task {active['task_id']}"
            )
        
        # Get or create task
        if task_id:
            task = self.db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                raise ValueError("Task not found")
            
            # Transition to EXECUTING
            task = self.task_manager.start_task(task_id)
        else:
            # Create new unplanned task
            if not title:
                raise ValueError("Title required for unplanned task")
            
            # Create task with current time as start
            now = now_utc()
            task, _, _ = self.task_manager.create_task(
                title=title,
                start=now,
                end=now + timedelta(hours=1),  # Default 1h duration
                state=TaskState.EXECUTING
            )
        
        # LYR-021: detect future task
        is_future_task = False
        if hasattr(task, 'planned_start_utc') and task.planned_start_utc:
            if task.planned_start_utc > now_utc() + timedelta(minutes=5):
                is_future_task = True
        
        # Create stopwatch session (transaction safety)
        actual_start = now_utc()
        session = StopwatchSession(
            task_id=task.task_id,
            start_time_utc=actual_start,
            auto_closed=False
        )
        self.db.add(session)
        self.db.flush()

        # Discrepancy measurement fields
        task.pre_task_readiness = pre_task_readiness
        task.initiation_status = "initiated"
        if task.planned_start_utc:
            delay = int((actual_start - task.planned_start_utc).total_seconds() / 60)
            task.initiation_delay_minutes = delay
        self.db.add(task)

        self.db.commit()
        self.db.refresh(session)
        self.db.refresh(task)

        # Store in Redis
        self.redis.set_active_stopwatch(
            user_id=user_id,
            session_id=session.session_id,
            task_id=task.task_id,
            title=task.title,
            start_time=session.start_time_utc.isoformat()
        )

        return session, task, is_future_task
    
    def stop(
        self,
        user_id: str = "user_primary",
        post_task_reflection: Optional[int] = None,
    ) -> tuple[StopwatchSession, Task, bool, bool]:
        """
        Stop active stopwatch.

        Returns (session, task, is_early_stop, notion_synced).

        If no active stopwatch but post_task_reflection is provided, updates
        the most recently completed task (within 10 min) with the reflection score.
        This supports the two-call pattern: stop → ask reflection → stop again.
        """
        # Get active stopwatch from Redis
        active = self.redis.get_active_stopwatch(user_id)
        if not active:
            recovered = self._recover_from_db(user_id)
            if recovered:
                active = recovered
            elif post_task_reflection is not None:
                # Reflection-only update: find the most recently completed task
                from datetime import timedelta
                cutoff = now_utc() - timedelta(minutes=10)
                task = (
                    self.db.query(Task)
                    .filter(
                        Task.state == TaskState.EXECUTED,
                        Task.executed_end_utc >= cutoff
                    )
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
        
        # Get session from DB
        session = self.db.query(StopwatchSession).filter(
            StopwatchSession.session_id == active['session_id']
        ).first()
        
        if not session:
            # Redis/DB desync - clear Redis
            self.redis.clear_active_stopwatch(user_id)
            raise NoActiveStopwatchError("Stopwatch session not found")
        
        # Get task
        task = self.db.query(Task).filter(Task.task_id == session.task_id).first()
        if not task:
            raise ValueError("Task not found")
        
        # Stop stopwatch (transaction safety)
        stop_time = now_utc()
        
        # LYR-024: detect early stop (< 50% of planned duration)
        is_early_stop = False
        executed_minutes = int((stop_time - session.start_time_utc).total_seconds() / 60)
        if task.planned_duration_minutes and task.planned_duration_minutes > 0:
            if executed_minutes < (task.planned_duration_minutes * 0.5):
                is_early_stop = True
        
        # Close session
        session.end_time_utc = stop_time
        self.db.add(session)
        
        # Mark task as completed (commits both), LYR-044: capture sync status
        task, notion_synced = self.task_manager.complete_task(
            task_id=task.task_id,
            executed_start=session.start_time_utc,
            executed_end=stop_time
        )

        # Save reflection if provided in the same call
        if post_task_reflection is not None:
            task.post_task_reflection = post_task_reflection
            self.db.commit()
            self.db.refresh(task)

        # Clear Redis
        self.redis.clear_active_stopwatch(user_id)

        return session, task, is_early_stop, notion_synced
    
    def get_status(
        self,
        user_id: str = "user_primary"
    ) -> Optional[dict]:
        """
        Get current stopwatch status.
        """
        active = self.redis.get_active_stopwatch(user_id)
        if not active:
            return None
        
        # Calculate elapsed time
        start_time = datetime.fromisoformat(active['start_time'])
        elapsed = now_utc() - start_time
        elapsed_minutes = int(elapsed.total_seconds() / 60)
        
        return {
            "active": True,
            "session_id": active['session_id'],
            "task_id": active['task_id'],
            "task_title": active['title'],
            "start_time": start_time,
            "elapsed_minutes": elapsed_minutes
        }
