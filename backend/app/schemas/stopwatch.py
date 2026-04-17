"""Pydantic schemas for stopwatch operations."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class StopwatchStartRequest(BaseModel):
    task_id: Optional[str] = Field(None, description="If None, creates new unplanned task")
    title: Optional[str] = Field(None, description="Required if task_id is None")
    pre_task_readiness: Optional[int] = Field(None, ge=1, le=5)
    interruption_type: Optional[str] = Field(None, description="urgent|scheduled_override|distraction|unknown")


class StopwatchStopRequest(BaseModel):
    post_task_reflection: Optional[int] = Field(None, ge=1, le=5)
    task_completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    scope_outcome: Optional[str] = Field(None, pattern="^(stuck_to_plan|expanded|reduced)$")


class StopwatchStartResponse(BaseModel):
    session_id: str
    task_id: str
    start_time: datetime
    is_future_task: bool = False
    planned_start: Optional[datetime] = None
    pre_task_readiness: Optional[int] = None
    initiation_delay_minutes: Optional[int] = None
    parent_task_id: Optional[str] = None
    interruption_type: Optional[str] = None


class PausedParentInfo(BaseModel):
    task_id: str
    title: str
    paused_minutes: int


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
    paused_parent: Optional[PausedParentInfo] = None
    micro_mirror: Optional[str] = None
    # LYR-098 Commit 2b: reflection_view_log row id for this firing.
    # Client stamps viewed_at/dismissed_at against it. NULL when the
    # corresponding signal did not fire.
    micro_mirror_view_id: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None
    calibration_nudge: Optional[str] = None
    calibration_nudge_view_id: Optional[str] = None
    task_completion_percentage: Optional[int] = None
    mid_task_completion_pct: Optional[int] = None


PAUSE_REASONS = {"mental_fatigue", "distraction", "task_difficulty", "external_interruption", "intentional_break", "prayer"}
PAUSE_INITIATORS = {"self", "external"}


class StopwatchPauseRequest(BaseModel):
    # Required — no silent defaults permitted on research-relevant fields.
    # See do_not_add.md §Hardcoded default values. The endpoint MUST reject
    # pauses without both fields supplied.
    pause_reason: str = Field(..., description="Required. One of: mental_fatigue, distraction, task_difficulty, external_interruption, intentional_break, prayer")
    pause_initiator: str = Field(..., description="Required. self or external")


class StopwatchPauseResponse(BaseModel):
    paused: bool
    elapsed_minutes: int
    paused_at: datetime
    pause_reason: str
    pause_initiator: str


class StopwatchResumeResponse(BaseModel):
    resumed: bool
    paused_minutes: float
    total_paused_minutes: float


class StopwatchStatusResponse(BaseModel):
    active: bool
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    start_time: Optional[datetime] = None
    elapsed_minutes: Optional[int] = None
    paused: bool = False
    total_paused_minutes: float = 0


class ReadinessCorrectionRequest(BaseModel):
    pre_task_readiness: int = Field(..., ge=1, le=5)


class ReadinessCorrectionResponse(BaseModel):
    corrected: bool
    original: Optional[int] = None
    new: int


class UpdateCompletionRequest(BaseModel):
    task_completion_percentage: int = Field(..., ge=0, le=100)


class UpdateCompletionResponse(BaseModel):
    updated: bool
    task_id: str
    task_title: str
    task_completion_percentage: int
    elapsed_minutes: int


class RetroactiveRequest(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    pre_task_readiness: Optional[int] = Field(None, ge=1, le=5)
    post_task_reflection: Optional[int] = Field(None, ge=1, le=5)
    category: Optional[str] = None
    planned_duration_minutes: Optional[int] = None
    unplanned_reason: Optional[str] = None
    total_paused_minutes: Optional[int] = Field(None, ge=0)


class RetroactiveResponse(BaseModel):
    task_id: str
    title: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    planned_duration_minutes: int
    delta_minutes: int
    initiation_status: str = "retroactive"
    pre_task_readiness: Optional[int] = None
    post_task_reflection: Optional[int] = None
    discrepancy_score: Optional[int] = None
    notion_synced: bool = True
