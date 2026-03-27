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
        user_id: str = "user_primary"
    ) -> tuple[StopwatchSession, Task]:
        """
        Start stopwatch.
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
        
        # Create stopwatch session (transaction safety)
        session = StopwatchSession(
            task_id=task.task_id,
            start_time_utc=now_utc(),
            auto_closed=False
        )
        self.db.add(session)
        self.db.flush()
        self.db.commit()
        self.db.refresh(session)
        
        # Store in Redis
        self.redis.set_active_stopwatch(
            user_id=user_id,
            session_id=session.session_id,
            task_id=task.task_id,
            title=task.title,
            start_time=session.start_time_utc.isoformat()
        )
        
        return session, task
    
    def stop(
        self,
        user_id: str = "user_primary"
    ) -> tuple[StopwatchSession, Task]:
        """
        Stop active stopwatch.
        """
        # Get active stopwatch from Redis
        active = self.redis.get_active_stopwatch(user_id)
        if not active:
            recovered = self._recover_from_db(user_id)
            if recovered:
                active = recovered
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
        
        # Close session
        session.end_time_utc = stop_time
        self.db.add(session)
        
        # Mark task as completed (commits both)
        task = self.task_manager.complete_task(
            task_id=task.task_id,
            executed_start=session.start_time_utc,
            executed_end=stop_time
        )
        
        # Clear Redis
        self.redis.clear_active_stopwatch(user_id)
        
        return session, task
    
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
