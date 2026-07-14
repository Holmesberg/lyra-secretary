from datetime import datetime, timedelta

from app.services import pause_predictor as runtime_predictor
from app.services.pause_predictor import _build as runtime_build
from app.services.pause_policy_replay import (
    HISTORY_GATE_DAYS,
    LOOKBACK_DAYS,
    MIN_LEAD_MINUTES,
    MIN_SAMPLES,
    _confidence,
    build_dataset,
    calibration_grid,
    chronological_split,
    definitions_hash,
    replay_candidates,
    summarize,
)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _export(*, days: int = 20, sessions_per_day: int = 2) -> dict:
    base = datetime(2026, 1, 1, 9, 0)
    tasks = []
    sessions = []
    pauses = []
    for day in range(days):
        for index in range(sessions_per_day):
            start = base + timedelta(days=day, hours=index * 3)
            task_id = f"task-{day}-{index}"
            session_id = f"session-{day}-{index}"
            tasks.append(
                {
                    "task_id": task_id,
                    "category": "study",
                    "voided_at": None,
                }
            )
            sessions.append(
                {
                    "session_id": session_id,
                    "task_id": task_id,
                    "start_time_utc": _iso(start),
                    "end_time_utc": _iso(start + timedelta(minutes=60)),
                    "auto_closed": False,
                    "data_quality_flag": None,
                }
            )
            pauses.append(
                {
                    "session_id": session_id,
                    "paused_at_utc": _iso(start + timedelta(minutes=30)),
                    "self_reported_retroactively": False,
                }
            )
    return {
        "tasks": tasks,
        "stopwatch_sessions": sessions,
        "pause_events": pauses,
        "exposure_decision_events": [],
        "exposure_render_events": [],
        "suppression_events": [],
        "reflection_view_logs": [],
        "pause_prediction_logs": [],
        "resume_prediction_logs": [],
    }


def test_dataset_excludes_noncanonical_sessions_and_split_is_chronological():
    exported = _export(days=10, sessions_per_day=1)
    exported["tasks"][0]["voided_at"] = _iso(datetime(2026, 1, 2))
    exported["stopwatch_sessions"][1]["auto_closed"] = True
    exported["stopwatch_sessions"][2]["data_quality_flag"] = "suspect"
    exported["stopwatch_sessions"][3]["end_time_utc"] = None

    dataset = build_dataset(exported)
    calibration, holdout = chronological_split(dataset.sessions)

    assert len(dataset.sessions) == 6
    assert len(calibration) == 4
    assert len(holdout) == 2
    assert calibration[-1].start < holdout[0].start


def test_replay_formula_and_fixed_gates_match_shipped_predictor():
    assert HISTORY_GATE_DAYS == runtime_predictor.HISTORY_GATE_DAYS
    assert LOOKBACK_DAYS == runtime_predictor.LOOKBACK_DAYS
    assert MIN_SAMPLES == runtime_predictor.MIN_SAMPLES
    assert MIN_LEAD_MINUTES == runtime_predictor.MIN_LEAD_MINUTES
    for samples in ([30.0] * 5, [20.0, 25.0, 30.0, 35.0, 40.0], [10.0] * 15):
        runtime = runtime_build(
            user_id=1,
            mechanism="work_rhythm",
            now=datetime(2026, 1, 1, 9, 0),
            predicted_at=datetime(2026, 1, 1, 9, 3),
            lead_minutes=3,
            samples=list(samples),
            active_task=None,
        )
        assert _confidence(list(samples)) == runtime.confidence


def test_replay_uses_only_prior_history_and_one_candidate_per_session():
    dataset = build_dataset(_export())
    calibration, _ = chronological_split(dataset.sessions)
    candidates = replay_candidates(
        dataset,
        calibration,
        confidence_floor=0.20,
        max_lead_minutes=10,
    )

    assert candidates
    assert len({row.session_id for row in candidates}) == len(candidates)
    assert all(row.fired_at < row.predicted_at for row in candidates)
    assert all(row.mechanism in {"clock_anchor", "work_rhythm"} for row in candidates)
    assert min(row.fired_at for row in candidates) >= datetime(2026, 1, 8)


def test_predictive_exposure_removes_pause_from_training():
    exported = _export(days=10, sessions_per_day=1)
    pause_at = exported["pause_events"][0]["paused_at_utc"]
    fired = datetime.fromisoformat(pause_at) - timedelta(minutes=5)
    exported["pause_prediction_logs"].append(
        {"firing_id": "legacy", "fired_at": _iso(fired)}
    )

    dataset = build_dataset(exported)

    assert datetime.fromisoformat(pause_at) in dataset.dirty_training_pause_times


def test_retroactive_pause_can_open_history_gate_but_is_not_training_or_outcome_truth():
    exported = _export(days=10, sessions_per_day=1)
    retro = datetime.fromisoformat(exported["pause_events"][0]["paused_at_utc"])
    exported["pause_events"][0]["self_reported_retroactively"] = True

    dataset = build_dataset(exported)

    assert retro in dataset.history_gate_pause_times
    assert retro not in dataset.training_pause_times
    assert retro not in dataset.qualifying_pause_times


def test_suppressed_v0_decision_does_not_dirty_training_pause():
    exported = _export(days=10, sessions_per_day=1)
    pause_at = datetime.fromisoformat(exported["pause_events"][0]["paused_at_utc"])
    exported["exposure_decision_events"].append(
        {
            "exposure_id": "suppressed",
            "exposure_category": "predictive_alert",
            "decision_status": "suppressed",
            "eligible_at": _iso(pause_at - timedelta(minutes=5)),
        }
    )
    exported["suppression_events"].append({"exposure_id": "suppressed"})

    dataset = build_dataset(exported)

    assert pause_at not in dataset.dirty_training_pause_times


def test_summary_separates_hit_late_and_miss_without_identifiers():
    dataset = build_dataset(_export())
    calibration, _ = chronological_split(dataset.sessions)
    candidates = replay_candidates(
        dataset,
        calibration,
        confidence_floor=0.20,
        max_lead_minutes=10,
    )
    metrics = summarize(dataset, calibration, candidates)

    assert metrics["opportunities"] == metrics["hits"] + metrics["late"] + metrics["misses"]
    assert "session_id" not in str(metrics)
    assert "task_id" not in str(metrics)


def test_calibration_grid_freezes_definitions_and_never_reads_holdout():
    result = calibration_grid(_export())

    assert result["definitions_hash"] == definitions_hash()
    assert result["holdout_evaluated"] is False
    assert result["status"] == "calibration_only"
    assert result["scope"] == "founder_only"
    assert result["transportability"] == "unknown"
    assert len(result["configurations"]) == 15
    assert all("metrics" in row for row in result["configurations"])
