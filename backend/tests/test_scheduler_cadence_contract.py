"""Cadence and single-inflight guards for behavior-shaping scheduler jobs."""

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEDULER_PATH = REPO_ROOT / "backend/app/workers/scheduler.py"


def _find_scheduler_job(job_id: str) -> ast.Call:
    tree = ast.parse(SCHEDULER_PATH.read_text(encoding="utf-8"))
    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        if not isinstance(call.func, ast.Attribute) or call.func.attr != "add_job":
            continue
        if any(
            keyword.arg == "id"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value == job_id
            for keyword in call.keywords
        ):
            return call
    raise AssertionError(f"{job_id} scheduler job was not registered")


def _assert_interval_and_single_inflight(
    job_id: str,
    *,
    interval_name: str,
    interval_value: int,
) -> None:
    job = _find_scheduler_job(job_id)
    trigger = next(keyword.value for keyword in job.keywords if keyword.arg == "trigger")
    assert isinstance(trigger, ast.Call)
    assert any(
        keyword.arg == interval_name
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value == interval_value
        for keyword in trigger.keywords
    )
    assert any(
        keyword.arg == "max_instances"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value == 1
        for keyword in job.keywords
    )


def test_reminders_run_each_minute_single_inflight():
    _assert_interval_and_single_inflight(
        "reminders", interval_name="minutes", interval_value=1
    )


def test_pause_prediction_runs_each_minute_single_inflight():
    _assert_interval_and_single_inflight(
        "pause_prediction", interval_name="minutes", interval_value=1
    )


def test_resume_prediction_keeps_two_minute_single_inflight_cadence():
    _assert_interval_and_single_inflight(
        "resume_prediction", interval_name="minutes", interval_value=2
    )
