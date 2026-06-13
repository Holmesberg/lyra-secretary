"""Public insight DTOs.

Internal analytics candidates may carry governance/debug evidence. This schema
is the explicit publication boundary for `/v1/analytics/insights`.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


TruthClass = Literal["trace", "metric", "interpretation", "intervention", "diagnostic_only"]
Confidence = Literal["low", "medium", "high"]


class PublicEvidenceRow(BaseModel):
    label: str
    value: str
    source_insight_id: str


class UserFacingInsightCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    surface_id: Optional[str] = None
    title: str
    body: str
    confidence_label: str
    authority_label: str
    sample_label: str
    evidence_rows: list[PublicEvidenceRow] = Field(default_factory=list)

    # Legacy-compatible fields for the current frontend/API contract.
    observation: str
    data_points: int
    confidence: Confidence
    strength: float
    seen: bool = False
    evidence: Optional[list[PublicEvidenceRow]] = None

    truth_class: Optional[TruthClass] = None
    usage_class: Optional[str] = None
    clean_profile: Optional[str] = None
    eligible_sample_count: Optional[int] = None
    min_n_required: Optional[int] = None
    suppressed_reason: Optional[str] = None
    fallback_mode: Optional[str] = None
    legacy_adapter: Optional[str] = None
    exposure_id: Optional[str] = None
    render_id: Optional[str] = None
    authority_rung: Optional[str] = None
    mutation_permission: Optional[str] = None
    public_translator: Optional[str] = None

    def public_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class InsightAuditEnvelope(BaseModel):
    """Non-public audit metadata for claim/evidence lineage."""

    model_config = ConfigDict(extra="forbid")

    evidence_packet_ids: list[str] = Field(default_factory=list)
    source_refs: list[dict[str, str]] = Field(default_factory=list)
    suppression_reason: Optional[str] = None
    admissibility: dict[str, Any] = Field(default_factory=dict)
