"""Deterministic evidence packets and claim compilation.

This module is deliberately downstream of analytics math and upstream of
user-facing render payloads. It does not infer new behavior. It turns already
computed outputs into inspectable evidence packets, then compiles only the
claims those packets permit.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Optional


PRIMARY_SYNTHESIS_ID = "primary_synthesis"
PRIMARY_SYNTHESIS_SURFACE_ID = "analytics.insights.primary_synthesis"
PRIMARY_SYNTHESIS_MIN_HISTORY_EVENTS = 30

DEFAULT_PROHIBITED_CLAIMS = (
    "identity_label",
    "causal_claim",
    "optimal_schedule",
    "psychological_truth",
    "adaptive_instruction",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _stable_hash(prefix: str, payload: dict[str, Any]) -> str:
    digest = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:24]}"


_ALLOWED_OBSERVED_METRIC_KEYS = {
    "insight_id",
    "data_points",
    "confidence",
    "strength",
    "facts",
}
_FORBIDDEN_METRIC_KEY_PARTS = (
    "url",
    "token",
    "oauth",
    "payload",
    "body",
    "baseet",
    "moodle",
    "provider_raw",
    "raw_provider",
    "secret",
)
_FORBIDDEN_FACT_KEY_PARTS = (
    "url",
    "token",
    "oauth",
    "payload",
    "body",
    "secret",
)


def _sanitize_scalar(value: Any, *, key: str) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"non_scalar_observed_metric:{key}")


def _sanitize_facts(facts: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in facts.items():
        key_text = str(key)
        lowered = key_text.lower()
        if any(part in lowered for part in _FORBIDDEN_FACT_KEY_PARTS):
            raise ValueError(f"forbidden_fact_key:{key_text}")
        sanitized[key_text] = _sanitize_scalar(value, key=key_text)
    return sanitized


def _sanitize_observed_metrics(observed_metrics: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in observed_metrics.items():
        key_text = str(key)
        lowered = key_text.lower()
        if key_text not in _ALLOWED_OBSERVED_METRIC_KEYS:
            raise ValueError(f"unknown_observed_metric:{key_text}")
        if any(part in lowered for part in _FORBIDDEN_METRIC_KEY_PARTS):
            raise ValueError(f"forbidden_observed_metric:{key_text}")
        if key_text == "facts":
            if not isinstance(value, dict):
                raise ValueError("facts_must_be_dict")
            sanitized[key_text] = _sanitize_facts(value)
        else:
            sanitized[key_text] = _sanitize_scalar(value, key=key_text)
    return sanitized


def _sanitize_source_refs(source_refs: list[dict[str, Any]]) -> list[dict[str, str]]:
    sanitized: list[dict[str, str]] = []
    for ref in source_refs:
        sanitized.append(
            {
                "type": str(ref.get("type") or ""),
                "id": str(ref.get("id") or ""),
                "surface_id": str(ref.get("surface_id") or ""),
            }
        )
    return sanitized


@dataclass(frozen=True)
class EvidencePacket:
    packet_id: str
    clean_profile: Optional[str]
    eligible_sample_count: int
    min_n_required: int
    observed_metrics: dict[str, Any]
    source_refs: list[dict[str, str]]
    prohibited_claims: list[str]
    suppression_reason: Optional[str] = None

    @classmethod
    def build(
        cls,
        *,
        clean_profile: Optional[str],
        eligible_sample_count: int,
        min_n_required: int,
        observed_metrics: dict[str, Any],
        source_refs: list[dict[str, Any]],
        prohibited_claims: Optional[list[str]] = None,
        suppression_reason: Optional[str] = None,
    ) -> "EvidencePacket":
        body = {
            "clean_profile": clean_profile,
            "eligible_sample_count": int(eligible_sample_count),
            "min_n_required": int(min_n_required),
            "observed_metrics": _sanitize_observed_metrics(observed_metrics),
            "source_refs": _sanitize_source_refs(source_refs),
            "prohibited_claims": prohibited_claims or list(DEFAULT_PROHIBITED_CLAIMS),
            "suppression_reason": suppression_reason,
        }
        return cls(packet_id=_stable_hash("evpkt", body), **body)

    def gate_suppression_reason(self) -> Optional[str]:
        if self.suppression_reason:
            return self.suppression_reason
        if not self.clean_profile:
            return "missing_clean_profile"
        if self.eligible_sample_count < self.min_n_required:
            return "insufficient_clean_samples"
        return None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClaimCandidate:
    claim_id: str
    surface_id: str
    observation: str
    data_points: int
    confidence: str
    strength: float
    evidence: list[dict[str, Any]]
    evidence_packet_ids: list[str]
    prohibited_claims: list[str]
    audit_envelope: dict[str, Any]
    suppression_reason: Optional[str] = None

    def to_insight_payload(self) -> Optional[dict[str, Any]]:
        if self.suppression_reason:
            return None
        payload = {
            "id": self.claim_id,
            "observation": self.observation,
            "data_points": self.data_points,
            "confidence": self.confidence,
            "strength": round(self.strength, 3),
            "_audit": self.audit_envelope,
        }
        if self.evidence:
            payload["evidence"] = self.evidence
        return payload


class ClaimCompiler:
    """Compile bounded claims from explicit evidence packets."""

    def compile_claim(
        self,
        *,
        claim_id: str,
        surface_id: str,
        observation: str,
        data_points: int,
        confidence: str,
        strength: float,
        evidence_packets: list[EvidencePacket],
        evidence: Optional[list[dict[str, Any]]] = None,
        claim_tags: Optional[tuple[str, ...]] = None,
        required_packet_count: int = 1,
    ) -> ClaimCandidate:
        claim_tags = claim_tags or ("descriptive_pattern",)
        prohibited_claims = sorted(
            {
                claim
                for packet in evidence_packets
                for claim in packet.prohibited_claims
            }
        )

        suppression_reason = None
        if len(evidence_packets) < required_packet_count:
            suppression_reason = "insufficient_evidence_packets"
        else:
            for packet in evidence_packets:
                suppression_reason = packet.gate_suppression_reason()
                if suppression_reason:
                    break

        if suppression_reason is None:
            blocked_tags = sorted(set(claim_tags).intersection(prohibited_claims))
            if blocked_tags:
                suppression_reason = f"prohibited_claim:{blocked_tags[0]}"

        return ClaimCandidate(
            claim_id=claim_id,
            surface_id=surface_id,
            observation=observation,
            data_points=data_points,
            confidence=confidence,
            strength=strength,
            evidence=evidence or [],
            evidence_packet_ids=[packet.packet_id for packet in evidence_packets],
            prohibited_claims=prohibited_claims,
            audit_envelope=claim_audit_envelope(
                evidence_packets,
                suppression_reason=suppression_reason,
            ),
            suppression_reason=suppression_reason,
        )


def evidence_packet_from_insight(
    insight: dict[str, Any],
) -> EvidencePacket:
    facts = insight.get("_facts") or {}
    source_ref_surface_id = (
        insight.get("surface_id")
        or f"analytics.insights.{insight.get('id')}"
    )
    observed_metrics = {
        "insight_id": insight.get("id"),
        "data_points": insight.get("data_points", 0),
        "confidence": insight.get("confidence"),
        "strength": insight.get("strength", 0.0),
    }
    if facts:
        observed_metrics["facts"] = facts
    return EvidencePacket.build(
        clean_profile=insight.get("clean_profile"),
        eligible_sample_count=int(insight.get("eligible_sample_count") or 0),
        min_n_required=int(insight.get("min_n_required") or 0),
        observed_metrics=observed_metrics,
        source_refs=[
            {
                "type": "insight",
                "id": insight.get("id"),
                "surface_id": source_ref_surface_id,
            }
        ],
        suppression_reason=insight.get("suppressed_reason"),
    )


def claim_audit_envelope(
    packets: list[EvidencePacket],
    *,
    suppression_reason: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "evidence_packet_ids": [packet.packet_id for packet in packets],
        "source_refs": [
            ref
            for packet in packets
            for ref in packet.source_refs
        ],
        "suppression_reason": suppression_reason,
        "admissibility": {
            "packet_count": len(packets),
            "clean_profiles": sorted(
                {
                    packet.clean_profile
                    for packet in packets
                    if packet.clean_profile
                }
            ),
            "eligible_sample_count_min": (
                min(packet.eligible_sample_count for packet in packets)
                if packets
                else 0
            ),
            "min_n_required_max": (
                max(packet.min_n_required for packet in packets)
                if packets
                else 0
            ),
        },
    }


def _evidence_item(label: str, value: str, source_insight_id: str) -> dict[str, str]:
    return {
        "label": label,
        "value": value,
        "source_insight_id": source_insight_id,
    }


def _abandonment_evidence_value(insight: dict[str, Any]) -> Optional[str]:
    facts = insight.get("_facts") or {}
    label = facts.get("label")
    not_started = facts.get("not_started")
    total = facts.get("total")
    percent = facts.get("percent")
    if label is None or not_started is None or total is None or percent is None:
        return None
    if facts.get("kind") == "tod":
        return f"{not_started}/{total} planned {label} tasks not started ({percent}%)"
    return f"{not_started}/{total} {label} tasks not started ({percent}%)"


def _time_of_day_evidence_value(insight: dict[str, Any]) -> Optional[str]:
    facts = insight.get("_facts") or {}
    tod = facts.get("time_of_day")
    avg = facts.get("average_delta_minutes")
    if tod is None or avg is None:
        return None
    direction = "under plan" if avg > 0 else "over plan"
    return f"{tod} tasks {round(abs(avg))} min {direction} on average"


def _estimation_trend_evidence_value(insight: dict[str, Any]) -> Optional[str]:
    facts = insight.get("_facts") or {}
    change = facts.get("change_minutes")
    if change is None:
        return None
    if change > 0:
        return f"estimate error down {abs(change):g} min over the last 10 sessions"
    return f"estimate error up {abs(change):g} min over the last 10 sessions"


def _initiation_delay_evidence_value(insight: dict[str, Any]) -> Optional[str]:
    facts = insight.get("_facts") or {}
    avg = facts.get("average_delay_minutes")
    if avg is None:
        return None
    direction = "after schedule" if avg > 0 else "before schedule"
    return f"starts averaged {round(abs(avg))} min {direction}"


def _primary_synthesis_observation(
    abandonment: dict[str, Any],
    supports: list[dict[str, Any]],
) -> str:
    abandonment_facts = abandonment.get("_facts") or {}
    category = (
        abandonment_facts.get("label")
        if abandonment_facts.get("kind") == "cat"
        else None
    )
    time_support = next(
        (
            support
            for support in supports
            if support.get("id") == "time_of_day_bias"
        ),
        None,
    )
    time_facts = (time_support or {}).get("_facts") or {}
    tod = time_facts.get("time_of_day")
    late_day = tod in {"evening", "night"}

    if category and late_day:
        return (
            f"Planning drift is currently clustering around {category} tasks "
            "and late-day execution."
        )
    if category:
        return (
            f"Planning drift is currently clustering around {category} tasks, "
            "with supporting execution signals in the same window."
        )
    if tod:
        return (
            f"Planning drift is currently clustering around {tod} task placement, "
            "with supporting execution signals in the same window."
        )
    return (
        "Several current signals point to one planning-reliability cluster "
        "rather than a single isolated metric."
    )


def compile_primary_synthesis(
    candidates: list[dict[str, Any]],
    *,
    history_events_analyzed: int,
) -> Optional[dict[str, Any]]:
    """Compile the existing primary synthesis from evidence packets.

    This preserves the previous public payload while moving claim assembly into
    the deterministic compiler layer.
    """
    by_id = {candidate.get("id"): candidate for candidate in candidates}
    abandonment = by_id.get("abandonment_pattern")
    if (
        abandonment is None
        or history_events_analyzed < PRIMARY_SYNTHESIS_MIN_HISTORY_EVENTS
    ):
        return None

    support_order = [
        "time_of_day_bias",
        "estimation_accuracy_trend",
        "initiation_delay",
    ]
    supports = [
        by_id[insight_id]
        for insight_id in support_order
        if insight_id in by_id
    ]
    if not supports:
        return None

    evidence = []
    abandonment_value = _abandonment_evidence_value(abandonment)
    if abandonment_value:
        evidence.append(
            _evidence_item(
                "Not-started pattern",
                abandonment_value,
                "abandonment_pattern",
            )
        )

    evidence_builders = {
        "time_of_day_bias": ("Time placement", _time_of_day_evidence_value),
        "estimation_accuracy_trend": (
            "Estimate drift",
            _estimation_trend_evidence_value,
        ),
        "initiation_delay": ("Start timing", _initiation_delay_evidence_value),
    }
    for support in supports:
        insight_id = support.get("id")
        label_and_builder = evidence_builders.get(insight_id)
        if label_and_builder is None:
            continue
        label, builder = label_and_builder
        value = builder(support)
        if value:
            evidence.append(_evidence_item(label, value, insight_id))

    if len(evidence) < 2:
        return None

    sources = [abandonment, *supports]
    data_points = max(source.get("data_points", 0) for source in sources)
    strength = max(source.get("strength", 0.0) for source in sources) + 50.0
    packets = [evidence_packet_from_insight(source) for source in sources]
    claim = ClaimCompiler().compile_claim(
        claim_id=PRIMARY_SYNTHESIS_ID,
        surface_id=PRIMARY_SYNTHESIS_SURFACE_ID,
        observation=_primary_synthesis_observation(abandonment, supports),
        data_points=data_points,
        confidence=(
            "high"
            if data_points >= 11
            else "medium"
            if data_points >= 6
            else "low"
        ),
        strength=strength,
        evidence_packets=packets,
        evidence=evidence[:4],
        claim_tags=("descriptive_pattern", "bounded_synthesis"),
        required_packet_count=2,
    )
    payload = claim.to_insight_payload()
    if payload is None:
        return None
    return payload
