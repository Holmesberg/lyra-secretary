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


PAUSE_REASONS = {"mental_fatigue", "distraction", "task_difficulty", "external_interruption", "intentional_break", "prayer"}
PAUSE_INITIATORS = {"self", "external"}


class StopwatchPauseRequest(BaseModel):
    pause_reason: Optional[str] = Field(None, description="One of: mental_fatigue, distraction, task_difficulty, external_interruption, intentional_break, prayer")
    pause_initiator: Optional[str] = Field(None, description="self or external")


class StopwatchPauseResponse(BaseModel):
    paused: bool
    elapsed_minutes: int
    paused_at: datetime
    pause_reason: Optional[str] = None
    pause_initiator: Optional[str] = None


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


class ReadinessCorrectionRequest(BaseModel):
    pre_task_readiness: int = Field(..., ge=1, le=5)


class ReadinessCorrectionResponse(BaseModel):
    corrected: bool
    original: Optional[int] = None
    new: int


class RetroactiveRequest(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    pre_task_readiness: Optional[int] = Field(None, ge=1, le=5)
    post_task_reflection: Optional[int] = Field(None, ge=1, le=5)
    category: Optional[str] = None


class RetroactiveResponse(BaseModel):
    task_id: str
    title: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    delta_minutes: int = 0
    initiation_status: str = "retroactive"
    pre_task_readiness: Optional[int] = None
    post_task_reflection: Optional[int] = None
    discrepancy_score: Optional[int] = None
    notion_synced: bool = True
