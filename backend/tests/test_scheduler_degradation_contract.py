from app.workers.jobs import _scheduler_contract as contract
from app.workers.jobs._scheduler_contract import (
    JobResult,
    MUTATION_MAY_HAVE_STARTED,
    NO_MUTATION_ATTEMPTED,
    SchedulerJobDegraded,
)


def test_scheduler_job_taxonomy_names_safe_degraded_and_failed_states():
    assert JobResult.OK.value == "ok"
    assert JobResult.DEGRADED_HANDLED.value == "degraded_handled"
    assert JobResult.FAILED_UNHANDLED.value == "failed_unhandled"


def test_run_scheduler_job_returns_degraded_for_handled_degradation():
    def _job():
        raise SchedulerJobDegraded("unit", "scheduler.unit")

    assert (
        contract.run_scheduler_job("unit", "scheduler.unit", _job)
        == JobResult.DEGRADED_HANDLED
    )


def test_run_scheduler_job_classifies_unhandled_failure_without_swallowing_by_default():
    def _job():
        raise RuntimeError("boom")

    assert (
        contract.run_scheduler_job(
            "unit",
            "scheduler.unit",
            _job,
            raise_unhandled=False,
        )
        == JobResult.FAILED_UNHANDLED
    )


def test_run_scheduler_job_raises_unhandled_failure_for_apscheduler_health():
    def _job():
        raise RuntimeError("boom")

    try:
        contract.run_scheduler_job("unit", "scheduler.unit", _job)
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("unhandled scheduler failure must reach APScheduler")


def test_degradation_alert_requires_exact_mutation_phrase():
    try:
        contract.notify_degraded_once(
            job_id="unit",
            subsystem="scheduler.unit",
            message="unit degraded",
            affected="scheduler.unit / bootstrap",
            scope="unknown",
            retry="retry later",
            user_action="none",
            data_integrity="No writes happened before bootstrap.",
            source="scheduler.unit",
            severity="warn",
            dedupe_key="unit",
        )
    except ValueError as exc:
        assert "data_integrity" in str(exc)
    else:
        raise AssertionError("scheduler degradation must use exact mutation phrases")


def test_degradation_alert_dedupes_inside_backoff_window(monkeypatch):
    sent = []
    clock = {"now": 100.0}

    monkeypatch.setattr(contract.time, "monotonic", lambda: clock["now"])
    contract.reset_degradation_backoff()

    kwargs = dict(
        job_id="unit",
        subsystem="scheduler.unit",
        message="unit degraded",
        affected="scheduler.unit / bootstrap",
        scope="unknown",
        retry="retry later",
        user_action="none",
        data_integrity=NO_MUTATION_ATTEMPTED,
        source="scheduler.unit",
        severity="warn",
        dedupe_key="unit",
        notifier=lambda *args, **kwargs: sent.append((args, kwargs)) or True,
    )

    assert contract.notify_degraded_once(**kwargs) is True
    assert contract.notify_degraded_once(**kwargs) is False
    assert len(sent) == 1
    assert f"Data integrity risk: {NO_MUTATION_ATTEMPTED}" in sent[0][0][0]

    clock["now"] += contract.DB_DEGRADATION_BACKOFF_SECONDS + 1
    assert contract.notify_degraded_once(
        **{**kwargs, "data_integrity": MUTATION_MAY_HAVE_STARTED}
    ) is True
    assert len(sent) == 2
    assert f"Data integrity risk: {MUTATION_MAY_HAVE_STARTED}" in sent[1][0][0]
