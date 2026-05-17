import ast
from pathlib import Path

from sqlalchemy.exc import OperationalError

from app.workers.jobs import llm_enrichment
from app.workers.jobs._scheduler_contract import (
    JobResult,
    NO_MUTATION_ATTEMPTED,
    reset_degradation_backoff,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEDULER_PATH = REPO_ROOT / "backend" / "app" / "workers" / "scheduler.py"


def _find_scheduler_job(job_id: str) -> ast.Call:
    tree = ast.parse(SCHEDULER_PATH.read_text(encoding="utf-8"))

    for call in [node for node in ast.walk(tree) if isinstance(node, ast.Call)]:
        if (
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "add_job"
            and any(
                keyword.arg == "id"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value == job_id
                for keyword in call.keywords
            )
        ):
            return call
    raise AssertionError(f"{job_id} scheduler job was not registered")


def _trigger_call(job: ast.Call) -> ast.Call:
    trigger_keyword = next(keyword for keyword in job.keywords if keyword.arg == "trigger")
    assert isinstance(trigger_keyword.value, ast.Call)
    return trigger_keyword.value


def _assert_max_instances_one(job: ast.Call) -> None:
    assert any(
        keyword.arg == "max_instances"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value == 1
        for keyword in job.keywords
    )


def test_llm_enrichment_is_auxiliary_bounded_work():
    assert llm_enrichment._MAX_TASKS_PER_CYCLE == 1


def test_scheduler_runs_llm_enrichment_on_slow_auxiliary_cadence():
    job = _find_scheduler_job("llm_enrichment")
    trigger_call = _trigger_call(job)
    assert any(
        keyword.arg == "seconds"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value >= 60
        for keyword in trigger_call.keywords
    )
    _assert_max_instances_one(job)


def test_scheduler_keeps_pause_prediction_single_inflight():
    job = _find_scheduler_job("pause_prediction")
    trigger_call = _trigger_call(job)
    assert any(
        keyword.arg == "minutes"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value == 1
        for keyword in trigger_call.keywords
    )
    _assert_max_instances_one(job)


def test_scheduler_keeps_reminders_single_inflight():
    job = _find_scheduler_job("reminders")
    trigger_call = _trigger_call(job)
    assert any(
        keyword.arg == "minutes"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value == 1
        for keyword in trigger_call.keywords
    )
    _assert_max_instances_one(job)


class _FailingPendingScanSession:
    def __init__(self):
        self.rollback_called = False
        self.close_called = False

    def query(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def all(self):
        raise OperationalError("SELECT task_id FROM task", {}, Exception("SSL EOF"))

    def rollback(self):
        self.rollback_called = True

    def close(self):
        self.close_called = True


class _FakeEngine:
    def __init__(self):
        self.dispose_calls = 0

    def dispose(self):
        self.dispose_calls += 1


def test_llm_enrichment_db_bootstrap_failure_degrades_without_raise(monkeypatch):
    session = _FailingPendingScanSession()
    engine = _FakeEngine()
    notifications = []

    monkeypatch.setattr(llm_enrichment, "SessionLocal", lambda: session)
    monkeypatch.setattr(llm_enrichment, "engine", engine)
    monkeypatch.setattr(
        llm_enrichment,
        "notify_operator",
        lambda *args, **kwargs: notifications.append((args, kwargs)) or True,
    )
    reset_degradation_backoff()

    assert llm_enrichment.run_llm_enrichment() == JobResult.DEGRADED_HANDLED

    assert session.rollback_called
    assert session.close_called
    assert engine.dispose_calls == 1
    assert len(notifications) == 1
    assert notifications[0][1]["source"] == "scheduler.llm-enrichment"
    assert "database bootstrap" in notifications[0][0][0]
    assert f"Data integrity risk: {NO_MUTATION_ATTEMPTED}" in notifications[0][0][0]
