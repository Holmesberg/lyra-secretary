"""Task state machine enforcement."""
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import Task, TaskState

class ImmutableTaskError(Exception):
    pass

class InvalidStateTransitionError(Exception):
    pass

class StateMachine:
    """Enforce task state transition rules."""
    
    # Valid transitions
    TRANSITIONS = {
        TaskState.PLANNED: {
            TaskState.EXECUTING,
            TaskState.EXECUTED,
            TaskState.SKIPPED,
            TaskState.DELETED
        },
        TaskState.EXECUTING: {
            TaskState.EXECUTED
        },
        TaskState.EXECUTED: set(),  # Immutable
        TaskState.SKIPPED: set(),   # Immutable
        TaskState.DELETED: set(),   # Immutable
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def transition(
        self,
        task: Task,
        new_state: TaskState,
        notes: Optional[str] = None
    ) -> Task:
        """
        Transition task to new state if valid.
        
        Args:
            task: Task to transition
            new_state: Target state
            notes: Optional notes
            
        Returns:
            Updated task
            
        Raises:
            ImmutableTaskError: If task is immutable
            InvalidStateTransitionError: If transition invalid
        """
        # Check if task is immutable
        if not task.is_mutable:
            raise ImmutableTaskError(
                f"Task {task.task_id} is {task.state.value} and cannot be modified"
            )
        
        # Check if transition is valid
        if new_state not in self.TRANSITIONS.get(task.state, set()):
            raise InvalidStateTransitionError(
                f"Cannot transition from {task.state.value} to {new_state.value}"
            )
        
        # Perform transition
        task.state = new_state
        task.last_modified_at = datetime.utcnow()
        
        if notes:
            task.notes = f"{task.notes or ''}\n{notes}".strip()
        
        self.db.commit()
        self.db.refresh(task)
        
        return task
    
    def can_transition(self, task: Task, new_state: TaskState) -> bool:
        """Check if transition is valid without raising exception."""
        if not task.is_mutable:
            return False
        return new_state in self.TRANSITIONS.get(task.state, set())
