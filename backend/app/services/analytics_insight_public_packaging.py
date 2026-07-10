"""Public packaging helpers for analytics Insights cards.

These helpers are intentionally pure: they translate already-computed insight
candidates into public response cards and redacted render snapshots. They do
not decide eligibility, write exposure rows, or own claim authority.
"""
from __future__ import annotations

from app.schemas.insights import (
    InsightAuditEnvelope,
    PublicEvidenceRow,
    UserFacingInsightCard,
)

INSIGHT_TITLES = {
    "primary_synthesis": "Primary pattern",
    "time_of_day_bias": "Time of day",
    "readiness_predicts_outcome": "Readiness signal",
    "readiness_time_of_day": "Readiness timing",
    "abandonment_pattern": "Not started",
    "estimation_accuracy_trend": "Estimation trend",
    "best_category": "Best category",
    "worst_category": "Worst category",
    "discrepancy_signal": "Discrepancy",
    "pause_pattern": "Pause pattern",
    "occupancy_footprint": "Planning footprint",
    "morning_anchor_cascade": "Morning plan",
    "retroactive_rate": "Retroactive rate",
    "initiation_delay": "Start delay",
    "archetype_divergence": "Starting profile drift",
    "calibration_maturation": "Personal calibration",
}

CONFIDENCE_LABELS = {
    "high": "High confidence",
    "medium": "Medium confidence",
    "low": "Watching this pattern",
}

AUTHORITY_LABELS = {
    "observed_trace": "Observed trace",
    "derived_metric": "Derived metric",
    "interpretation": "Interpretation",
    "suggestion": "Suggestion",
    "intervention": "Intervention",
    "adaptation": "Future-gated adaptation",
    "mutation": "Mutation",
    "operator_only_action": "Operator-only action",
}


def public_insight_card(result: dict) -> dict:
    """Translate an internal insight candidate into an explicit public card."""
    insight_id = str(result["id"])
    confidence = result.get("confidence") or "low"
    if confidence not in CONFIDENCE_LABELS:
        confidence = "low"
    data_points = int(result.get("data_points") or 0)
    evidence_rows = [
        PublicEvidenceRow(
            label=str(row.get("label", "")),
            value=str(row.get("value", "")),
            source_insight_id=str(row.get("source_insight_id", "")),
        )
        for row in (result.get("evidence") or [])
    ]
    authority_rung = result.get("authority_rung") or "interpretation"
    card = UserFacingInsightCard(
        id=insight_id,
        surface_id=result.get("surface_id"),
        title=INSIGHT_TITLES.get(insight_id, insight_id.replace("_", " ").title()),
        body=str(result.get("observation") or ""),
        confidence_label=CONFIDENCE_LABELS[confidence],
        authority_label=AUTHORITY_LABELS.get(authority_rung, "Interpretation"),
        sample_label=f"{data_points} history event{'s' if data_points != 1 else ''}",
        observation=str(result.get("observation") or ""),
        data_points=data_points,
        confidence=confidence,
        strength=round(float(result.get("strength") or 0.0), 3),
        seen=bool(result.get("seen")),
        evidence=evidence_rows or None,
        evidence_rows=evidence_rows,
        truth_class=result.get("truth_class"),
        usage_class=result.get("usage_class"),
        clean_profile=result.get("clean_profile"),
        eligible_sample_count=result.get("eligible_sample_count"),
        min_n_required=result.get("min_n_required"),
        suppressed_reason=result.get("suppressed_reason"),
        fallback_mode=result.get("fallback_mode"),
        legacy_adapter=result.get("legacy_adapter"),
        exposure_id=result.get("exposure_id"),
        render_id=result.get("render_id"),
        authority_rung=result.get("authority_rung"),
        mutation_permission=result.get("mutation_permission"),
        public_translator=result.get("public_translator"),
    )
    return card.public_dict()


def insights_exposure_snapshot(
    response_payload: dict,
    candidates: list[dict],
) -> dict:
    """Build the non-public, redacted exposure render snapshot.

    Public cards keep the legacy response shape. The render ledger only needs
    enough structure to prove what was shown and which safe audit handles backed
    it, without storing observation copy or packet internals.
    """
    public_insights = response_payload.get("insights") or []
    rendered_ids = [
        str(insight.get("id"))
        for insight in public_insights
        if insight.get("id") is not None
    ]
    rendered_id_set = set(rendered_ids)
    suppressed_generators = response_payload.get("suppressed_generators") or []

    audit_envelopes = []
    for candidate in candidates:
        insight_id = str(candidate.get("id") or "")
        if insight_id not in rendered_id_set:
            continue
        audit = candidate.get("_audit")
        if not isinstance(audit, dict):
            continue
        try:
            envelope = InsightAuditEnvelope(**audit)
        except Exception:
            continue
        audit_envelopes.append(
            {
                "insight_id": insight_id,
                "surface_id": candidate.get("surface_id"),
                **envelope.model_dump(exclude_none=True),
            }
        )

    return {
        "schema_version": "analytics_insights_exposure_snapshot_v1",
        "surface_id": response_payload.get("surface_id"),
        "truth_class": response_payload.get("truth_class"),
        "usage_class": response_payload.get("usage_class"),
        "clean_profile": response_payload.get("clean_profile"),
        "ready": bool(response_payload.get("ready")),
        "insight_count": len(public_insights),
        "insight_ids": rendered_ids,
        "suppressed_generator_count": len(suppressed_generators),
        "suppressed_generator_ids": [
            str(row.get("id"))
            for row in suppressed_generators
            if row.get("id") is not None
        ],
        "eligible_sample_count": response_payload.get("eligible_sample_count"),
        "min_n_required": response_payload.get("min_n_required"),
        "sessions_analyzed": response_payload.get("sessions_analyzed"),
        "history_events_analyzed": response_payload.get("history_events_analyzed"),
        "audit_envelopes": audit_envelopes,
    }
