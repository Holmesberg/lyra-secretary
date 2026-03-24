"""
Task Manager - SINGLE MUTATION AUTHORITY.

ALL task modifications MUST go through this service.
No other service should modify Task objects directly.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import Task, TaskState, TaskSource
from app.services.parser import TaskParser
from app.services.state_machine import StateMachine
from app.services.conflict_detector import ConflictDetector
from app.services.notion_client import NotionClient
from app.utils.redis_client import RedisClient
from app.utils.time_utils import to_utc, now_utc
from app.core.exceptions import ImmutableTaskError


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
        # Detect conflicts
        conflicts = self.conflict_detector.detect(start, end)
        
        if conflicts and not force_conflicts:
            return None, conflicts, False
        
        # Calculate duration
        duration_minutes = int((end - start).total_seconds() / 60)
        
        # Create task (transaction safety)
        task = Task(
            title=title,
            planned_start_utc=start,
            planned_end_utc=end,
            planned_duration_minutes=duration_minutes,
            category=category,
            state=state,
            source=source,
            confidence_score=confidence_score,
            created_at=now_utc(),
            last_modified_at=now_utc()
        )
        
        self.db.add(task)
        self.db.flush()  # Get task_id
        self.db.commit()
        self.db.refresh(task)
        
        # Sync to Notion (non-blocking)
        notion_synced = False
        try:
            self.notion.sync_task(task)
            notion_synced = True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notion sync failed during create_task: {e}", exc_info=True)
        
        # Cache for undo
        self.redis.cache_undo_action("create_task", task.task_id, {
            "task_id": task.task_id,
            "title": task.title
        })
        
        return task, [], notion_synced
    
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
            self.notion.sync_task(task)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notion sync failed during start_task: {e}", exc_info=True)
            pass
        
        return task
    
    def complete_task(
        self,
        task_id: str,
        executed_start: datetime,
        executed_end: datetime
    ) -> Task:
        """
        Mark task as completed.
        
        Args:
            task_id: Task to complete
            executed_start: Actual start time (UTC)
            executed_end: Actual end time (UTC)
            
        Returns:
            Updated task
        """
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        
        executed_duration = int((executed_end - executed_start).total_seconds() / 60)
        
        task.executed_start_utc = executed_start
        task.executed_end_utc = executed_end
        task.executed_duration_minutes = executed_duration
        task = self.state_machine.transition(task, TaskState.EXECUTED)
        
        # Sync to Notion
        try:
            self.notion.sync_task(task)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notion sync failed during complete_task: {e}", exc_info=True)
            pass
        
        return task
    
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
        
        task = self.state_machine.transition(task, TaskState.SKIPPED, notes=reason)
        
        # Sync to Notion
        try:
            self.notion.sync_task(task)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notion sync failed during skip_task: {e}", exc_info=True)
            pass
        
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
        
        if not task.is_mutable:
            raise ImmutableTaskError("Cannot delete immutable task")
        
        task = self.state_machine.transition(task, TaskState.DELETED)
        
        # Remove from Notion
        try:
            if task.notion_page_id:
                self.notion.archive_page(task.notion_page_id)
        except Exception:
            pass
        
        # Cache for undo
        self.redis.cache_undo_action("delete_task", task.task_id, {
            "task_id": task.task_id,
            "title": task.title,
            "previous_state": task.state.value
        })
        
        return task
    
    def reschedule_task(
        self,
        task_id: str,
        new_start: datetime,
        new_end: Optional[datetime] = None
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
        
        if not task.is_mutable:
            raise ImmutableTaskError("Cannot reschedule immutable task")
        
        # Calculate new end if not provided
        if new_end is None:
            duration = task.planned_end_utc - task.planned_start_utc
            new_end = new_start + duration
        
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
        task.last_modified_at = now_utc()
        self.db.commit()
        self.db.refresh(task)
        
        # Sync to Notion
        try:
            self.notion.sync_task(task)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notion sync failed during reschedule_task: {e}", exc_info=True)
            pass
        
        return task, conflicts
