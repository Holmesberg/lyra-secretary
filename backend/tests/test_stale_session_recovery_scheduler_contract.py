from sqlalchemy.exc import OperationalError

from app.workers.jobs import stale_session_recovery
from app.workers.jobs._scheduler_contract import (
    JobResult,
    NO_MUTATION_ATTEMPTED,
    reset_degradation_backoff,
)


def test_stale_session_bootstrap_db_failure_degrades_without_apscheduler_error(
    monkeypatch,
):
    class FailingSession:
        def query(self, *_args, **_kwargs):
            raise OperationalError("select", {}, Exception("db down"))

        def rollback(self):
            pass

        def close(self):
            pass

    notifications = []
    dispose_count = 0

    def fake_dispose(_logger=None):
        nonlocal dispose_count
        dispose_count += 1

    monkeypatch.setattr(stale_session_recovery, "SessionLocal", FailingSession)
    monkeypatch.setattr(stale_session_recovery, "dispose_engine_pool", fake_dispose)
    monkeypatch.setattr(
        stale_session_recovery,
        "time",
        type("Clock", (), {"sleep": staticmethod(lambda _seconds: None)}),
    )
    monkeypatch.setattr(
        "app.workers.jobs._scheduler_contract.notify_operator",
        lambda message, **kwargs: notifications.append((message, kwargs)) or True,
    )
    reset_degradation_backoff()

    assert stale_session_recovery.run_stale_session_recovery() == JobResult.DEGRADED_HANDLED
    assert dispose_count == stale_session_recovery.STALE_BOOTSTRAP_MAX_ATTEMPTS
    assert len(notifications) == 1
    assert notifications[0][1]["source"] == "scheduler.stale-sessions"
    assert f"Data integrity risk: {NO_MUTATION_ATTEMPTED}" in notifications[0][0]
