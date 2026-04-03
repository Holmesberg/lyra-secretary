"""Pydantic schemas for stopwatch operations."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class StopwatchStartRequest(BaseModel):
    task_id: Optional[str] = Field(None, description="If None, creates new unplanned task")
    title: Optional[str] = Field(None, description="Required if task_id is None")
    pre_task_readiness: Optional[int] = Field(None, ge=1, le=5)


class StopwatchStopRequest(BaseModel):
    post_task_reflection: Optional[int] = Field(None, ge=1, le=5)


class StopwatchStartResponse(BaseModel):
    session_id: str
    task_id: str
    start_time: datetime
    is_future_task: bool = False
    planned_start: Optional[datetime] = None
    pre_task_readiness: Optional[int] = None
    initiation_delay_minutes: Optional[int] = None


class StopwatchStopResponse(BaseModel):
    task_id: str
    session_id: str
    duration_minutes: int
    planned_duration_minutes: Optional[int]
    delta_minutes: Optional[int]
    executed_at: datetime
    is_early_stop: bool = False
    notion_synced: bool = True
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None
    post_task_reflection: Optional[int] = None
    discrepancy_score: Optional[int] = None


class StopwatchPauseResponse(BaseModel):
    paused: bool
    elapsed_minutes: int
    paused_at: datetime


class StopwatchResumeResponse(BaseModel):
    resumed: bool
    paused_minutes: int
    total_paused_minutes: int


class StopwatchStatusResponse(BaseModel):
    active: bool
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    start_time: Optional[datetime] = None
    elapsed_minutes: Optional[int] = None
    paused: bool = False
    total_paused_minutes: int = 0
