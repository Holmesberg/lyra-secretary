"""Pydantic schemas for task operations."""
from datetime import datetime
from typing import Literal, Optional
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
    # Loop 1 (alembic 034, 2026-04-27) — calibration nudge decision logging.
    # Set by NewTaskModal when the user clicks "Use [suggested]" or
    # "Keep [typed]" on the bias_factor suggestion. All four fields must
    # appear together OR all four must be absent — partial sets are rejected
    # by TaskManager. When present, TaskManager writes one
    # CalibrationNudgeEvent row in the same transaction as the task.
    nudge_decision: Optional[Literal["accepted", "dismissed"]] = Field(
        None,
        description="'accepted' (used LyraOS's suggestion) or 'dismissed' (kept typed duration)",
    )
    nudge_suggested_duration_minutes: Optional[int] = Field(
        None, ge=1, le=480, description="What LyraOS suggested at nudge-fire time"
    )
    nudge_bias_factor: Optional[float] = Field(
        None, ge=0.1, le=10.0, description="bias_factor used to compute the suggestion"
    )
    nudge_sample_size: Optional[int] = Field(
        None, ge=0, description="n_sessions_in_cell at nudge-fire time"
    )
    nudge_viewed_at: Optional[datetime] = Field(
        None,
        description=(
            "Phase 6 V3 prerequisite: when did the modal calibration "
            "nudge first appear in the UI? Optional. When supplied, "
            "TaskManager writes dwell_seconds on the ReflectionViewLog "
            "row alongside the CalibrationNudgeEvent."
        ),
    )

    @validator('end')
    def end_after_start(cls, v, values):
        if 'start' in values and v <= values['start']:
            raise ValueError('end must be after start')
        return v

    @validator('nudge_sample_size', always=True)
    def nudge_fields_all_or_none(cls, v, values):
        """All-four-or-none discipline. Partial sets indicate a frontend bug."""
        nudge_fields = (
            values.get('nudge_decision'),
            values.get('nudge_suggested_duration_minutes'),
            values.get('nudge_bias_factor'),
            v,
        )
        present = sum(1 for f in nudge_fields if f is not None)
        if present not in (0, 4):
            raise ValueError(
                f"nudge_* fields must all be present or all absent; got {present}/4. "
                "If a calibration nudge fired, the modal must capture decision + "
                "suggested + bias_factor + sample_size together."
            )
        return v


class TaskRescheduleRequest(BaseModel):
    """Request to reschedule a task."""
    task_id: str = Field(..., min_length=36, max_length=36)
    new_start: datetime
    new_end: Optional[datetime] = None  # If None, preserves duration
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    # Edit-modal parity (2026-04-28): description + deadline_id were
    # write-only via /v1/create; the edit modal could not change them.
    # Now reschedule accepts both. When description changes,
    # llm_parse_status is reset to 'pending' so the enrichment worker
    # re-runs against the new text. deadline_id binding mirrors /create:
    # validates ownership + bindable state, sets deadline_match_source
    # to 'user_explicit'.
    description: Optional[str] = Field(None, max_length=2000)
    deadline_id: Optional[str] = Field(
        None, min_length=36, max_length=36,
        description="Optional UUID of the deadline to bind to. None = no change.",
    )
    clear_deadline: bool = Field(
        False,
        description=(
            "Explicitly clear the current deadline binding. False/absent = no change. "
            "Cannot be combined with deadline_id."
        ),
    )

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
    effective_executed_end: Optional[datetime] = None
    effective_executed_duration_minutes: Optional[int] = None
    effective_duration_delta_minutes: Optional[int] = None
    execution_duration_provenance: str = "observed"
    execution_correction_id: Optional[str] = None
    
    state: TaskState
    source: TaskSource
    confidence_score: Optional[float]
    notes: Optional[str]
    is_anchor: bool = False
    rct_arm: Optional[str] = None
    
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


class MarkDoneResponse(BaseModel):
    """Response from retroactively marking an overdue task done.

    This is deliberately separate from stopwatch completion: it is a
    retrospective product affordance for overdue PLANNED/SKIPPED rows, not a
    measured execution trace.
    """
    task_id: str
    done: bool
    retrospective: bool
    previous_state: TaskState
    new_state: TaskState
    initiation_status: str


EXECUTION_CORRECTION_REASONS = {
    "forgot_to_stop_timer",
    "accidental_left_running",
}


class ExecutionCorrectionRequest(BaseModel):
    """Retroactively correct an EXECUTED task's effective execution window.

    Exactly one of corrected_end_time or corrected_duration_minutes must be
    supplied. The backend records an append-only correction row and does not
    mutate the original task/session timestamps. Stopwatch-backed tasks are
    constrained to forgotten-stop corrections; retroactive self-reported tasks
    can correct the reported end/duration without stopwatch evidence.
    """

    corrected_end_time: Optional[datetime] = None
    corrected_duration_minutes: Optional[int] = Field(None, ge=1)
    reason: str = Field("forgot_to_stop_timer", max_length=40)
    note: Optional[str] = Field(None, max_length=500)

    @validator("reason")
    def _reason_must_be_enum(cls, v: str) -> str:
        if v not in EXECUTION_CORRECTION_REASONS:
            raise ValueError(
                f"reason must be one of {sorted(EXECUTION_CORRECTION_REASONS)}"
            )
        return v

    @validator("corrected_duration_minutes", always=True)
    def _exactly_one_correction_input(
        cls,
        v: Optional[int],
        values: dict,
    ) -> Optional[int]:
        has_end = values.get("corrected_end_time") is not None
        has_duration = v is not None
        if has_end == has_duration:
            raise ValueError(
                "Supply exactly one of corrected_end_time or corrected_duration_minutes"
            )
        return v


class ExecutionCorrectionResponse(BaseModel):
    task_id: str
    correction_id: str
    corrected: bool
    provenance: str
    reason: str
    original_executed_end: datetime
    original_executed_duration_minutes: int
    corrected_executed_end: datetime
    corrected_executed_duration_minutes: int
    effective_duration_delta_minutes: int
    vt17_eligible: bool


class SwapRequest(BaseModel):
    """Request to swap a SKIPPED task and a PLANNED task."""
    task_a_id: str
    task_b_id: str


class SwapResponse(BaseModel):
    """Response from swapping two tasks."""
    swapped: bool
    reactivated_task_id: str
    skipped_task_id: str


class LlmConfirmRequest(BaseModel):
    """User clicked "keep" or "use this" on the LLM-suggested chip
    (Workstream 1, magic-for-alpha). Copies LLM-suggested fields into
    the canonical task fields per the operator-locked guardrail #2 —
    the user must explicitly accept; we never silently auto-bind.

    `accepted_fields` is the subset of LLM suggestions to commit:
      - 'deadline'   — copy llm_inferred_deadline_id → deadline_id
                       (sets deadline_match_source='llm_auto_confirmed')
      - 'priority'   — copy llm_priority → priority (when priority col ships)

    `chosen_deadline_id` overrides the LLM's top candidate when the user
    picks a different one from the Tier 2 multi-option chip.
    """
    accepted_fields: list[str] = Field(default_factory=list)
    chosen_deadline_id: Optional[str] = Field(
        None,
        description=(
            "Override for the LLM's top candidate. When None (Tier 1 flow), "
            "uses task.llm_inferred_deadline_id. When set (Tier 2 flow), "
            "uses this explicit value — must be in llm_deadline_candidates."
        ),
    )


class LlmConfirmResponse(BaseModel):
    task_id: str
    deadline_id_after: Optional[str] = None
    deadline_match_source_after: Optional[str] = None
    priority_set: bool = False


class LlmRejectRequest(BaseModel):
    """User explicitly clicked 'no, just keep mine' on the LLM chip.
    Records the rejection (audit) and clears the LLM suggestion so the
    chip stops rendering."""
    pass


class LlmRejectResponse(BaseModel):
    task_id: str
    rejected_at: datetime


class TaskDeadlineBindingRequest(BaseModel):
    """Narrow metadata correction for task ↔ deadline context.

    This intentionally does not use the full reschedule/edit path: live
    and executed tasks may need semantic deadline correction after the
    user discovers the right context, but title/time/execution metrics
    must stay untouched.
    """
    deadline_id: Optional[str] = Field(
        None,
        min_length=36,
        max_length=36,
        description="Deadline UUID to bind. Omit/null only when clear_deadline=true.",
    )
    clear_deadline: bool = Field(
        False,
        description="Clear the current binding. Cannot be combined with deadline_id.",
    )


class TaskDeadlineBindingResponse(BaseModel):
    task_id: str
    deadline_id_after: Optional[str] = None
    deadline_title_after: Optional[str] = None
    deadline_match_source_after: Optional[str] = None
    metadata_correction: bool = True
