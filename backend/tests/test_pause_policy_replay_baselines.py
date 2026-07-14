from datetime import datetime, timedelta

from app.services import pause_policy_replay_baselines as baselines
from app.services.pause_policy_replay import build_dataset, chronological_split
from app.services.pause_policy_replay_baselines import evaluate_founder_holdout


def _iso(value: datetime) -> str:
    return value.isoformat()


def _history(*, days: int = 20) -> dict:
    base = datetime(2026, 1, 1, 9, 0)
    tasks = []
    sessions = []
    pauses = []
    for day in range(days):
        for index, hour in enumerate((9, 13)):
            start = base.replace(hour=hour) + timedelta(days=day)
            task_id = f"task-{day}-{index}"
            session_id = f"session-{day}-{index}"
            tasks.append({"task_id": task_id, "category": "study", "voided_at": None})
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


def test_fixed_and_random_comparators_obey_one_prompt_per_session():
    dataset = build_dataset(_history())
    _, holdout = chronological_split(dataset.sessions)

    fixed = baselines._fixed_candidates(
        dataset,
        holdout,
        pause_offset_minutes=30,
        max_lead_minutes=10,
        mechanism="fixed",
    )
    random_rows = baselines._random_candidates(
        dataset, holdout, max_lead_minutes=10, seed=0
    )

    assert len({row.session_id for row in fixed}) == len(fixed)
    assert len({row.session_id for row in random_rows}) == len(random_rows)
    assert all(row.fired_at < row.predicted_at for row in fixed + random_rows)


def test_full_holdout_evaluation_is_bounded_and_identifier_free(monkeypatch):
    monkeypatch.setattr(baselines, "RANDOM_NULL_REPETITIONS", 100)
    monkeypatch.setattr(baselines, "BOOTSTRAP_REPETITIONS", 100)

    result = evaluate_founder_holdout(_history(days=30))

    assert result["holdout_evaluated"] is True
    assert result["visible_runtime_enabled"] is False
    assert result["random_null"]["repetitions"] == 100
    assert result["status"] in {
        "founder_visible_candidate",
        "no_incremental_signal_demonstrated",
    }
    serialized = str(result)
    assert "session-" not in serialized
    assert "task-" not in serialized
    assert "study" not in serialized


def test_insufficient_history_never_reads_holdout(monkeypatch):
    monkeypatch.setattr(baselines, "RANDOM_NULL_REPETITIONS", 5)
    monkeypatch.setattr(baselines, "BOOTSTRAP_REPETITIONS", 5)

    result = evaluate_founder_holdout(_history(days=4))

    assert result["status"] == "inconclusive"
    assert result["holdout_evaluated"] is False
    assert "v2" not in result
