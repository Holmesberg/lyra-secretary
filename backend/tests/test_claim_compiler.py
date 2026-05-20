from app.services.claim_compiler import (
    ClaimCompiler,
    EvidencePacket,
    PRIMARY_SYNTHESIS_ID,
    compile_primary_synthesis,
)


def _packet(**overrides):
    base = {
        "source_surface_id": "analytics.insights.time_of_day_bias",
        "signal_family": "planning_calibration",
        "truth_class": "interpretation",
        "clean_profile": "planning_calibration",
        "eligible_sample_count": 12,
        "min_n_required": 3,
        "confidence_tier": "high",
        "observed_metrics": {"insight_id": "time_of_day_bias", "data_points": 12},
        "source_refs": [
            {
                "type": "insight",
                "id": "time_of_day_bias",
                "surface_id": "analytics.insights.time_of_day_bias",
            }
        ],
    }
    base.update(overrides)
    return EvidencePacket.build(**base)


def test_evidence_packet_hash_is_stable_for_same_payload():
    first = _packet(
        observed_metrics={"data_points": 12, "insight_id": "time_of_day_bias"}
    )
    second = _packet(
        observed_metrics={"insight_id": "time_of_day_bias", "data_points": 12}
    )

    assert first.packet_id == second.packet_id


def test_missing_clean_profile_suppresses_claim():
    packet = _packet(clean_profile=None)
    claim = ClaimCompiler().compile_claim(
        claim_id="test_claim",
        surface_id="analytics.insights.test",
        observation="Several signals point to the same pattern.",
        data_points=12,
        confidence="high",
        strength=1.0,
        evidence_packets=[packet],
    )

    assert claim.suppression_reason == "missing_clean_profile"
    assert claim.to_insight_payload() is None


def test_insufficient_sample_count_suppresses_claim():
    packet = _packet(eligible_sample_count=2, min_n_required=3)
    claim = ClaimCompiler().compile_claim(
        claim_id="test_claim",
        surface_id="analytics.insights.test",
        observation="Several signals point to the same pattern.",
        data_points=2,
        confidence="low",
        strength=1.0,
        evidence_packets=[packet],
    )

    assert claim.suppression_reason == "insufficient_clean_samples"
    assert claim.to_insight_payload() is None


def test_prohibited_claim_tag_cannot_render():
    packet = _packet(prohibited_claims=["causal_claim"])
    claim = ClaimCompiler().compile_claim(
        claim_id="test_claim",
        surface_id="analytics.insights.test",
        observation="This would overstate the evidence.",
        data_points=12,
        confidence="high",
        strength=1.0,
        evidence_packets=[packet],
        claim_tags=("causal_claim",),
    )

    assert claim.suppression_reason == "prohibited_claim:causal_claim"
    assert claim.to_insight_payload() is None


def test_competing_hypotheses_survive_compilation():
    packet = _packet(
        competing_hypotheses=[
            "scope inflation",
            "structural task dependency",
        ]
    )
    claim = ClaimCompiler().compile_claim(
        claim_id="test_claim",
        surface_id="analytics.insights.test",
        observation="Several signals point to the same pattern.",
        data_points=12,
        confidence="high",
        strength=1.0,
        evidence_packets=[packet],
    )
    payload = claim.to_insight_payload()

    assert payload is not None
    assert payload["_competing_hypotheses"] == [
        "scope inflation",
        "structural task dependency",
    ]


def test_primary_synthesis_compiles_from_evidence_packets():
    candidates = [
        {
            "id": "abandonment_pattern",
            "observation": "Study tasks were not started.",
            "data_points": 30,
            "confidence": "high",
            "strength": 10.0,
            "surface_id": "analytics.insights.abandonment_pattern",
            "truth_class": "interpretation",
            "clean_profile": "planning_calibration",
            "eligible_sample_count": 30,
            "min_n_required": 3,
            "_facts": {
                "kind": "cat",
                "label": "study",
                "not_started": 12,
                "total": 30,
                "percent": 40,
            },
        },
        {
            "id": "time_of_day_bias",
            "observation": "Evening tasks run over plan.",
            "data_points": 18,
            "confidence": "high",
            "strength": 8.0,
            "surface_id": "analytics.insights.time_of_day_bias",
            "truth_class": "interpretation",
            "clean_profile": "planning_calibration",
            "eligible_sample_count": 30,
            "min_n_required": 3,
            "_facts": {
                "time_of_day": "evening",
                "average_delta_minutes": -50,
            },
        },
    ]

    payload = compile_primary_synthesis(candidates, history_events_analyzed=30)

    assert payload is not None
    assert payload["id"] == PRIMARY_SYNTHESIS_ID
    assert "study tasks" in payload["observation"]
    assert "late-day execution" in payload["observation"]
    assert payload["evidence"][0]["source_insight_id"] == "abandonment_pattern"
    assert len(payload["_evidence_packets"]) == 2
    assert all(
        packet["packet_id"].startswith("evpkt_")
        for packet in payload["_evidence_packets"]
    )
