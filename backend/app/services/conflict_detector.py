"""Time conflict detection."""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import Task, TaskState


class ConflictDetector:
    """Detect overlapping tasks."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def detect(
        self,
        start: datetime,
        end: datetime,
        exclude_task_id: Optional[str] = None
    ) -> list[Task]:
        """
        Detect tasks that overlap with given time range.
        
        Overlap logic:
            Task A: [start_A, end_A)
            Task B: [start_B, end_B)
            Overlap if: start_A < end_B AND start_B < end_A
        
        Args:
            start: Range start (UTC)
            end: Range end (UTC)
            exclude_task_id: Optional task to exclude from check
            
        Returns:
            List of conflicting tasks
        """
        query = self.db.query(Task).filter(
            Task.state.in_([TaskState.PLANNED, TaskState.EXECUTING, TaskState.EXECUTED]),
            Task.planned_start_utc < end,
            Task.planned_end_utc > start
        )
        
        if exclude_task_id:
            query = query.filter(Task.task_id != exclude_task_id)
        
        return query.all()
