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
    description: Optional[str] = Field(None, max_length=2000)
    state: TaskState = TaskState.PLANNED
    source: TaskSource = TaskSource.MANUAL
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    force: bool = Field(False, description="Ignore conflicts if true")
    # Loop 11 — explicit deadline binding (parser Pass 1).
    # If provided, TaskManager validates ownership + bindable state and sets
    # deadline_match_source='user_explicit' with confidence=1.0.
    deadline_id: Optional[str] = Field(
        None,
        min_length=36,
        max_length=36,
        description="Optional UUID of the deadline this task should bind to",
    )
    
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
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)

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
    """Information about a conflicting task.

    `gate_id` (Path A, Apr 16 2026): which gate fired for this conflict —
    `"active_overlap"` (HARD), `"planned_overlap"` (SOFT), or
    `"duplicate_title"` (SOFT). Lets the dogfood override-rate analytics
    monitoring (Day 10 interrogation item) attribute overrides per gate.
    """
    task_id: str
    title: str
    start: datetime
    end: datetime
    state: TaskState
    gate_id: Optional[str] = None


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
    """Response from creating a task.

    Severity model (Path A, Apr 16 2026):
      - `severity = "hard"` + `can_proceed = False`: EXECUTING-overlap conflict.
        Single-mutation-authority is structural; no force-override available.
        Frontend must surface error without an override button.
      - `severity = "soft"` + `can_proceed = True`: PLANNED/PAUSED overlap or
        duplicate title. Frontend can offer `force=true` retry.
      - `severity = None` + `can_proceed = True`: no conflict, normal create.

    `soft_reasons` lists which soft gates fired: `"overlap"` and/or
    `"duplicate_title"` — drives the warning copy on the frontend.
    """
    task_id: Optional[str]
    created: bool
    notion_synced: bool = False
    conflicts: list[ConflictInfo] = Field(default_factory=list)
    can_proceed: bool = True
    severity: Optional[str] = None
    soft_reasons: list[str] = Field(default_factory=list)


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

    # Loop 11 — deadline binding + scope-bullet instruments (alembic 033).
    # All optional → backward-compat with consumers that ignore these fields.
    deadline_id: Optional[str] = None
    deadline_match_confidence: Optional[float] = None
    deadline_match_source: Optional[str] = None
    scope_bullet_count_at_plan: Optional[int] = None
    scope_bullet_count_at_execute: Optional[int] = None

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


VOID_REASONS = {
    "test_contamination",
    "duplicate",
    "system_error",
    "data_quality",
    "other",
}


class TaskVoidRequest(BaseModel):
    """Request to void a task.

    Allowed on any non-DELETED task (Phase 3.2 redesign). `voided_reason`
    is now a constrained enum; `void_reason_detail` is required iff
    voided_reason == 'other'.
    """
    voided_reason: str = Field(..., description="Enum", max_length=40)
    void_reason_detail: Optional[str] = Field(None, max_length=500)

    @validator("voided_reason")
    def _reason_must_be_enum(cls, v: str) -> str:
        if v not in VOID_REASONS:
            raise ValueError(
                f"voided_reason must be one of {sorted(VOID_REASONS)}"
            )
        return v

    @validator("void_reason_detail", always=True)
    def _detail_required_for_other(cls, v: Optional[str], values: dict) -> Optional[str]:
        if values.get("voided_reason") == "other" and not (v and v.strip()):
            raise ValueError("void_reason_detail is required when voided_reason='other'")
        return v


class TaskVoidResponse(BaseModel):
    """Response from voiding a task."""
    task_id: str
    voided: bool
    previous_state: str
    previous_initiation_status: str
    voided_at: datetime
    voided_reason: str
    void_reason_detail: Optional[str] = None


class MarkAbandonedRequest(BaseModel):
    """Request to mark an EXECUTING, PAUSED, or PLANNED task as skipped."""
    reason: Optional[str] = Field(None, max_length=200)


class MarkAbandonedResponse(BaseModel):
    """Response from marking a task skipped/abandoned."""
    task_id: str
    abandoned: bool
    previous_state: TaskState
    new_state: TaskState


class SwapRequest(BaseModel):
    """Request to swap a SKIPPED task and a PLANNED task."""
    task_a_id: str
    task_b_id: str


class SwapResponse(BaseModel):
    """Response from swapping two tasks."""
    swapped: bool
    reactivated_task_id: str
    skipped_task_id: str
