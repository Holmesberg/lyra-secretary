"""Schemas for the academic pressure map.

This is an explanatory product surface, not a research-learning surface.
The response intentionally carries ranges, assumptions, and trust state
instead of a single "AI knows the answer" estimate.
"""
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_serializer, model_validator


AcademicTrustState = Literal[
    "verified_exact",
    "verified_reachable",
    "ambiguous",
    "requires_user_confirmation",
    "stale",
    "dead_link",
    "access_denied",
]

AcademicComplexityTier = Literal["low", "medium", "high", "unknown"]
AcademicConfidence = Literal["low", "medium", "high"]
AcademicPressureLevel = Literal["low", "medium", "high", "overdue"]
AcademicSourceClass = Literal["external", "native", "lyra_task"]
AcademicProviderReadStatus = Literal[
    "available",
    "partial",
    "unavailable",
    "not_connected",
]
AcademicEvidenceClass = Literal[
    "external_obligation",
    "native_obligation",
    "scheduled_intention",
]
AcademicCompressionKind = Literal[
    "due_soon",
    "overdue",
    "cluster",
    "known_load",
    "uncertain_coverage",
]
AcademicRecoveryAction = Literal[
    "confirm_coverage",
    "split_into_blocks",
    "create_plan",
    "review_calendar",
    "clear_or_ignore",
]
AcademicProjectionRole = Literal[
    "deadline_obligation",
    "standalone_task_obligation",
]


class AcademicPressureEstimate(BaseModel):
    low_minutes: int
    high_minutes: int
    confidence: AcademicConfidence
    assumptions: list[str]


class AcademicPressureItem(BaseModel):
    obligation_id: str
    title: str
    due_at_utc: datetime
    source: str
    source_class: AcademicSourceClass
    evidence_class: AcademicEvidenceClass
    provider_kind: Optional[str] = None
    raw_authority_level: str
    redaction_status: str
    obligation_type: str
    trust_state: AcademicTrustState
    complexity_tier: AcademicComplexityTier
    complexity_source: str
    pressure_level: AcademicPressureLevel
    days_until_due: float
    estimate: AcademicPressureEstimate
    warnings: list[str] = Field(default_factory=list)

    @field_serializer("due_at_utc")
    def _serialize_due_utc(self, v: datetime) -> str:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class AcademicSourceSummary(BaseModel):
    deadlines_total: int
    external_obligation_count: int
    native_obligation_count: int
    academic_task_count: int = 0
    study_task_count: int = 0
    academic_task_minutes: int = 0
    study_task_minutes: int = 0
    google_calendar_connected: bool
    google_calendar_read_status: AcademicProviderReadStatus
    calendar_busy_minutes: Optional[int]
    planned_lyra_minutes: int


class AcademicCompressionPoint(BaseModel):
    kind: AcademicCompressionKind
    title: str
    detail: str
    obligation_ids: list[str] = Field(default_factory=list)


class AcademicRecoveryOption(BaseModel):
    action: AcademicRecoveryAction
    label: str
    detail: str
    obligation_ids: list[str] = Field(default_factory=list)


class AcademicCoverageQuestion(BaseModel):
    obligation_id: str
    question: str
    reason: str
    trust_state: AcademicTrustState


class AcademicCapacityContext(BaseModel):
    known_busy_minutes: Optional[int]
    planned_lyra_minutes: int
    estimated_academic_low_minutes: int
    estimated_academic_high_minutes: int
    google_calendar_connected: bool
    google_calendar_read_status: AcademicProviderReadStatus
    caveat: str


class AcademicMinuteEnvelope(BaseModel):
    low_minutes: int = Field(ge=0)
    high_minutes: int = Field(ge=0)

    @model_validator(mode="after")
    def _ordered_bounds(self) -> "AcademicMinuteEnvelope":
        if self.low_minutes > self.high_minutes:
            raise ValueError("low_minutes cannot exceed high_minutes")
        return self


class AcademicObligationDemandProjection(BaseModel):
    obligation_id: str
    projection_role: AcademicProjectionRole
    source_class: AcademicSourceClass
    total_estimate: AcademicMinuteEnvelope
    completed_scope_credit: AcademicMinuteEnvelope
    remaining_demand: AcademicMinuteEnvelope
    feasible_future_coverage: AcademicMinuteEnvelope
    applied_coverage: AcademicMinuteEnvelope
    unscheduled_demand: AcademicMinuteEnvelope
    overcoverage: AcademicMinuteEnvelope
    linked_task_ids: list[str] = Field(default_factory=list)
    coverage_task_ids: list[str] = Field(default_factory=list)
    noncontributing_linked_task_ids: list[str] = Field(default_factory=list)
    estimate_inconsistent: bool = False


class AcademicUnlinkedPlanningContext(BaseModel):
    status: Literal["context_only_not_demand_or_coverage"] = (
        "context_only_not_demand_or_coverage"
    )
    task_count: int = Field(ge=0)
    union_minutes: int = Field(ge=0)
    task_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _task_ids_match_count(self) -> "AcademicUnlinkedPlanningContext":
        if len(self.task_ids) != self.task_count:
            raise ValueError("task_count must match task_ids")
        if len(set(self.task_ids)) != len(self.task_ids):
            raise ValueError("task_ids must be unique")
        return self


class AcademicDemandCoverageProjection(BaseModel):
    schema_version: Literal["academic_demand_coverage_projection_v1"] = (
        "academic_demand_coverage_projection_v1"
    )
    projection_status: Literal["provisional_demand_only"] = (
        "provisional_demand_only"
    )
    capacity_status: Literal["unavailable_no_authority"] = (
        "unavailable_no_authority"
    )
    collision_state: Literal["unknown"] = "unknown"
    obligation_count: int = Field(ge=0)
    scenario_count: int = Field(ge=1)
    total_estimate: AcademicMinuteEnvelope
    completed_scope_credit: AcademicMinuteEnvelope
    remaining_demand: AcademicMinuteEnvelope
    feasible_future_coverage: AcademicMinuteEnvelope
    applied_coverage: AcademicMinuteEnvelope
    unscheduled_demand: AcademicMinuteEnvelope
    overcoverage: AcademicMinuteEnvelope
    unlinked_planning_context: AcademicUnlinkedPlanningContext
    inconsistent_obligation_ids: list[str] = Field(default_factory=list)
    obligations: list[AcademicObligationDemandProjection] = Field(
        default_factory=list
    )


class AcademicPressureMapResponse(BaseModel):
    generated_at_utc: datetime
    horizon_days: int
    headline: str
    pressure_summary: str
    items: list[AcademicPressureItem]
    compression_points: list[AcademicCompressionPoint]
    recovery_options: list[AcademicRecoveryOption]
    coverage_questions: list[AcademicCoverageQuestion]
    capacity_context: AcademicCapacityContext
    estimated_low_minutes: int
    estimated_high_minutes: int
    demand_coverage_projection: AcademicDemandCoverageProjection
    source_summary: AcademicSourceSummary
    methodology: list[str]
    warnings: list[str]
    surface_id: Optional[str] = None
    truth_class: Optional[str] = None
    signal_targets: Optional[list[str]] = None
    clean_profile: Optional[str] = None
    fallback_mode: Optional[str] = None
    authority_rung: Optional[str] = None
    mutation_permission: Optional[str] = None
    public_translator: Optional[str] = None
    surface_role: Optional[str] = None
    allowed_authority: list[str] = Field(default_factory=list)
    denied_authority: list[str] = Field(default_factory=list)
    exposure_id: Optional[str] = None
    render_snapshot: Optional[dict[str, Any]] = None

    @field_serializer("generated_at_utc")
    def _serialize_generated_utc(self, v: datetime) -> str:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
