"""Pydantic schemas for stopwatch operations."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class StopwatchStartRequest(BaseModel):
    """Request to start stopwatch."""
    task_id: Optional[str] = Field(
        None,
        description="If None, creates new unplanned task"
    )
    title: Optional[str] = Field(
        None,
        description="Required if task_id is None"
    )


class StopwatchStartResponse(BaseModel):
    """Response from starting stopwatch."""
    session_id: str
    task_id: str
    start_time: datetime


class StopwatchStopResponse(BaseModel):
    """Response from stopping stopwatch."""
    task_id: str
    session_id: str
    duration_minutes: int
    planned_duration_minutes: Optional[int]
    delta_minutes: Optional[int]
    executed_at: datetime


class StopwatchStatusResponse(BaseModel):
    """Current stopwatch status."""
    active: bool
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    start_time: Optional[datetime] = None
    elapsed_minutes: Optional[int] = None
