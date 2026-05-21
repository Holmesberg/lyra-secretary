"""Schemas for the academic pressure map.

This is an explanatory product surface, not a research-learning surface.
The response intentionally carries ranges, assumptions, and trust state
instead of a single "AI knows the answer" estimate.
"""
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_serializer


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
    calendar_busy_minutes: int
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
    known_busy_minutes: int
    planned_lyra_minutes: int
    estimated_academic_low_minutes: int
    estimated_academic_high_minutes: int
    google_calendar_connected: bool
    caveat: str


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
    render_id: Optional[str] = None

    @field_serializer("generated_at_utc")
    def _serialize_generated_utc(self, v: datetime) -> str:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
