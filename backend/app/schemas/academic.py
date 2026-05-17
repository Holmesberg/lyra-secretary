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
    moodle_deadlines: int
    native_deadlines: int
    google_calendar_connected: bool
    calendar_busy_minutes: int
    planned_lyra_minutes: int


class AcademicPressureMapResponse(BaseModel):
    generated_at_utc: datetime
    horizon_days: int
    headline: str
    items: list[AcademicPressureItem]
    estimated_low_minutes: int
    estimated_high_minutes: int
    source_summary: AcademicSourceSummary
    methodology: list[str]
    warnings: list[str]

    @field_serializer("generated_at_utc")
    def _serialize_generated_utc(self, v: datetime) -> str:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
