"""Execution anomaly generalization scenarios."""
from __future__ import annotations

from scripts.lyrasim.models import HiddenState, ScenarioData, TraceEvent


SCENARIO_ID = "execution_outlier_single_trace_does_not_generalize"


def _clean_session_event(index: int) -> TraceEvent:
    return TraceEvent(
        event_type="execution_session_observed",
        occurred_at_minute=index,
        payload={
            "task_key": f"baseline_study_{index:02d}",
            "category": "study",
            "day_offset": index,
            "hour": 9,
            "planned_duration_minutes": 60,
            "executed_duration_minutes": 65,
            "state": "executed",
            "initiation_status": "started",
            "provenance": "observed",
            "evidence_class": "measured_execution",
            "clean_data_eligible": True,
            "authority_ceiling": "interpretation",
        },
    )


def _corrected_outlier_event() -> TraceEvent:
    return TraceEvent(
        event_type="execution_anomaly_observed",
        occurred_at_minute=11,
        payload={
            "task_key": "corrected_planning_outlier",
            "category": "study",
            "day_offset": 11,
            "hour": 9,
            "planned_duration_minutes": 10,
            "executed_duration_minutes": 180,
            "corrected_executed_duration_minutes": 15,
            "state": "executed",
            "initiation_status": "started",
            "provenance": "user_repaired",
            "evidence_class": "execution_anomaly",
            "clean_data_eligible": False,
            "correction_reason": "accidental_left_running",
            "generalization_probe": "single_outlier",
            "authority_ceiling": "interpretation",
        },
    )


def generate(seed: int) -> ScenarioData:
    return ScenarioData(
        scenario_id=SCENARIO_ID,
        scenario_version=f"{SCENARIO_ID}:v0",
        scenario_origin="repo_derived",
        seed=seed,
        synthetic_user_id=f"synthetic_{seed % 997:03d}",
        hidden_state=HiddenState(
            user_activity="corrected_planning_outlier_not_representative",
            intended_activity="baseline_study_sessions_plus_one_repaired_record",
            notes=(
                "A single corrected overrun exists beside otherwise stable "
                "study sessions. Product seams may see only trace provenance, "
                "not the hidden representativeness judgment."
            ),
        ),
        observable_trace=(
            *tuple(_clean_session_event(index) for index in range(10)),
            _corrected_outlier_event(),
        ),
        generator_assumptions=(
            "Normal study sessions are observed execution traces.",
            "The extreme overrun is repaired evidence and is not clean calibration.",
            "One anomaly should not become a stable user or category claim.",
            "The product seam receives observable trace/provenance only.",
        ),
        coverage_limitations=(
            "This scenario does not validate adaptive scheduling.",
            "This scenario does not validate live provider progress.",
            "This scenario validates the analytics insights seam after rows exist.",
        ),
        expected_resolution_rung="suppress",
    )
