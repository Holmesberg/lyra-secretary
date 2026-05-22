"""Generator for the V0 stale unclosed timer scenario."""
from __future__ import annotations

import random

from scripts.lyrasim.models import HiddenState, ScenarioData, TraceEvent


SCENARIO_ID = "task_started_never_stopped"
SCENARIO_VERSION = "task_started_never_stopped:v0"


def generate(seed: int) -> ScenarioData:
    rng = random.Random(seed)
    synthetic_user_id = f"synthetic_{rng.randrange(1, 999999):06d}"
    task_id = f"task_{rng.randrange(1, 999999):06d}"
    session_id = f"session_{rng.randrange(1, 999999):06d}"
    stale_after_minutes = 48 * 60

    trace = (
        TraceEvent(
            event_type="task_created",
            occurred_at_minute=0,
            payload={
                "task_id": task_id,
                "title": "Study algorithms lecture",
                "planned_duration_minutes": 90,
                "provenance": "self_reported",
            },
        ),
        TraceEvent(
            event_type="timer_started",
            occurred_at_minute=5,
            payload={
                "task_id": task_id,
                "session_id": session_id,
                "provenance": "observed",
            },
        ),
        TraceEvent(
            event_type="stale_threshold_crossed",
            occurred_at_minute=stale_after_minutes + 5,
            payload={
                "task_id": task_id,
                "session_id": session_id,
                "threshold_minutes": stale_after_minutes,
                "provenance": "system_recovered",
            },
        ),
    )

    return ScenarioData(
        scenario_id=SCENARIO_ID,
        scenario_version=SCENARIO_VERSION,
        scenario_origin="synthetic",
        seed=seed,
        synthetic_user_id=synthetic_user_id,
        hidden_state=HiddenState(
            user_activity="unknown_after_timer_start",
            intended_activity="study_algorithms_lecture",
            notes="The simulator knows the timer never received a stop event; Lyra only sees the observable trace.",
        ),
        observable_trace=trace,
        generator_assumptions=(
            "No timer stop event was emitted.",
            "The stale threshold crossing is system recovery evidence, not observed execution.",
            "No provider or passive telemetry is present in this V0 scenario.",
        ),
        coverage_limitations=(
            "This scenario does not validate live product seams.",
            "This scenario does not model Baseet provider payloads.",
            "This scenario does not prove emotional safety or user trust.",
        ),
        allowed_outputs=(
            "descriptive_history",
            "stale_timer_repair_notice",
        ),
        forbidden_outputs=(
            "clean_measured_execution",
            "cognition_claim",
            "identity_claim",
        ),
        expected_authority_ceiling="interpretation",
        expected_clean_data_decision="exclude_from_planning_calibration",
        expected_safe_actions=(),
    )
