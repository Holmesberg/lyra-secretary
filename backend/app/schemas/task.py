"""Pydantic schemas for task operations."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from app.db.models import TaskState, TaskSource


# Request schemas
class TaskParseRequest(BaseModel):
    """Request to parse natural language into task."""
    text: str = Field(..., min_length=1, max_length=500)


class TaskCreateRequest(BaseModel):
    """Request to create a new task."""
    title: str = Field(..., min_length=1, max_length=255)
    start: datetime
    end: datetime
    category: Optional[str] = Field(None, max_length=100)
    state: TaskState = TaskState.PLANNED
    source: TaskSource = TaskSource.MANUAL
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    force: bool = Field(False, description="Ignore conflicts if true")
    
    @validator('end')
    def end_after_start(cls, v, values):
        if 'start' in values and v <= values['start']:
            raise ValueError('end must be after start')
        return v


class TaskRescheduleRequest(BaseModel):
    """Request to reschedule a task."""
    task_id: str = Field(..., min_length=36, max_length=36)
    new_start: datetime
    new_end: Optional[datetime] = None  # If None, preserves duration
    
    @validator('new_end')
    def end_after_start(cls, v, values):
        if v is not None and 'new_start' in values and v <= values['new_start']:
            raise ValueError('new_end must be after new_start')
        return v


class TaskDeleteRequest(BaseModel):
    """Request to delete a task."""
    task_id: str = Field(..., min_length=36, max_length=36)


class TaskQueryRequest(BaseModel):
    """Request to query tasks."""
    q: Optional[str] = Field(None, description="Search keyword")
    state: Optional[TaskState] = None
    category: Optional[str] = None
    timeframe: Optional[str] = Field(
        None,
        description="today|this_week|last_week|this_month|last_month"
    )
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(1, ge=1)
    limit: int = Field(50, ge=1, le=100)


# Response schemas
class ConflictInfo(BaseModel):
    """Information about a conflicting task."""
    task_id: str
    title: str
    start: datetime
    end: datetime
    state: TaskState


class TaskParseResponse(BaseModel):
    """Response from parsing natural language."""
    title: str
    start: datetime
    end: Optional[datetime]
    duration_minutes: Optional[int]
    category: Optional[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
    ambiguities: list[str] = Field(default_factory=list)


class TaskCreateResponse(BaseModel):
    """Response from creating a task."""
    task_id: Optional[str]
    created: bool
    conflicts: list[ConflictInfo] = Field(default_factory=list)
    can_proceed: bool = True


class TaskDetail(BaseModel):
    """Detailed task information."""
    task_id: str
    title: str
    category: Optional[str]
    
    planned_start: datetime
    planned_end: datetime
    planned_duration_minutes: int
    
    executed_start: Optional[datetime]
    executed_end: Optional[datetime]
    executed_duration_minutes: Optional[int]
    
    state: TaskState
    source: TaskSource
    confidence_score: Optional[float]
    notes: Optional[str]
    
    created_at: datetime
    last_modified_at: datetime
    
    # Computed fields
    duration_delta_minutes: Optional[int]
    is_mutable: bool
    
    class Config:
        from_attributes = True


class TaskQueryResponse(BaseModel):
    """Response from querying tasks."""
    tasks: list[TaskDetail]
    total: int
    page: int
    has_more: bool


class TaskRescheduleResponse(BaseModel):
    """Response from rescheduling a task."""
    task_id: str
    rescheduled: bool
    new_start: datetime
    new_end: datetime
    conflicts: list[ConflictInfo] = Field(default_factory=list)


class TaskDeleteResponse(BaseModel):
    """Response from deleting a task."""
    task_id: str
    deleted: bool
