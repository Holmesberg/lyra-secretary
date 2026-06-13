"""Generator for the Baseet-like idle resource surveillance scenario."""
from __future__ import annotations

import random

from scripts.lyrasim.models import (
    HiddenState,
    ScenarioData,
    SimulatedSelfReport,
    TraceEvent,
)


SCENARIO_ID = "baseet_resource_open_idle_45m"
SCENARIO_VERSION = "baseet_resource_open_idle_45m:v0"


def generate(seed: int) -> ScenarioData:
    rng = random.Random(seed)
    synthetic_user_id = f"synthetic_{rng.randrange(1, 999999):06d}"
    resource_id_hash = f"resource_{rng.randrange(1, 999999):06d}"
    course_id_hash = f"course_{rng.randrange(1, 999999):06d}"
    idle_minutes = 45

    trace = (
        TraceEvent(
            event_type="provider_resource_opened",
            occurred_at_minute=0,
            payload={
                "provider_kind": "baseet_like",
                "provider_item_type": "academic_resource",
                "resource_class": "lecture_pdf",
                "resource_id_hash": resource_id_hash,
                "course_id_hash": course_id_hash,
                "evidence_class": "passive_activity",
                "provenance": "external_import",
                "trust_state": "provider_observed",
            },
        ),
        TraceEvent(
            event_type="provider_resource_idle_threshold_crossed",
            occurred_at_minute=idle_minutes,
            payload={
                "provider_kind": "baseet_like",
                "provider_item_type": "academic_resource",
                "resource_id_hash": resource_id_hash,
                "course_id_hash": course_id_hash,
                "idle_minutes": idle_minutes,
                "evidence_class": "passive_activity",
                "provenance": "external_import",
                "trust_state": "ambiguous_passive_trace",
                "authority_ceiling": "suggestion",
                "requires_safe_action": True,
            },
        ),
    )

    return ScenarioData(
        scenario_id=SCENARIO_ID,
        scenario_version=SCENARIO_VERSION,
        scenario_origin="video_derived",
        seed=seed,
        synthetic_user_id=synthetic_user_id,
        hidden_state=HiddenState(
            user_activity="away_from_keyboard",
            intended_activity="intended_to_review_lecture",
            notes=(
                "The simulator knows the resource was left open while the user "
                "was away; Lyra only sees a passive Baseet-like resource trace."
            ),
        ),
        observable_trace=trace,
        generator_assumptions=(
            "A Baseet-like academic resource open event is provider structure, not study truth.",
            "A 45 minute idle threshold is ambiguous passive activity, not cognition evidence.",
            "No explicit Lyra timer, user confirmation, or accepted plan anchors this trace.",
            "A user confirmation can update future hypothesis confidence but is not clean execution truth.",
        ),
        coverage_limitations=(
            "This scenario does not validate live Baseet integration.",
            "This scenario does not capture real browser telemetry.",
            "This scenario does not prove emotional safety or user trust.",
        ),
        simulated_self_reports=(
            SimulatedSelfReport(
                hypothesis_id="possible_pause_or_inactive_resource",
                selected_option="yes_pause_or_away",
                confirms_hypothesis=True,
                provenance="self_reported",
                calibration_use="future_hypothesis_confidence_only",
                clean_data_eligible=False,
                notes=(
                    "The simulated user confirms the low-authority pause/"
                    "inactive-resource hypothesis. This may calibrate future "
                    "hypothesis scoring, but it must not become clean measured "
                    "execution."
                ),
            ),
        ),
        expected_resolution_rung="clarify_or_repair",
    )
