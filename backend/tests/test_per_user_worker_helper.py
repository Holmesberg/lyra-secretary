from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import object_session

from app.db.models import User
from app.db.scoping import get_current_user_id, set_current_user_id
from app.workers.jobs import _per_user
from tests.conftest import TestingSession


@pytest.fixture(autouse=True)
def _reset_bootstrap_backoff(monkeypatch):
    monkeypatch.setattr(_per_user, "_bootstrap_backoff_until_monotonic", 0.0)
    yield


def test_for_each_user_passes_session_attached_user(db, monkeypatch):
    db.rollback()
    db.query(User).delete()
    db.commit()
    user = User(
        email="worker-user@example.com",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    user_id = user.user_id

    monkeypatch.setattr(_per_user, "SessionLocal", TestingSession)

    def _mutate_user(job_db, scoped_user):
        assert object_session(scoped_user) is job_db
        assert get_current_user_id() == user_id
        scoped_user.moodle_base_url = "https://lms.example.edu"
        job_db.commit()

    _per_user.for_each_user(_mutate_user)

    db.expire_all()
    refreshed = db.query(User).filter(User.user_id == user_id).one()
    assert refreshed.moodle_base_url == "https://lms.example.edu"
    assert get_current_user_id() is None
    set_current_user_id(None)


def test_for_each_user_notifies_on_user_failure(db, monkeypatch):
    db.rollback()
    db.query(User).delete()
    db.commit()
    user = User(
        email="worker-failure@example.com",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()

    monkeypatch.setattr(_per_user, "SessionLocal", TestingSession)
    calls = []

    def _notify(*args, **kwargs):
        calls.append((args, kwargs))
        return True

    monkeypatch.setattr(_per_user, "notify_operator", _notify)

    def _bad_job(job_db, scoped_user):
        raise RuntimeError("boom")

    _per_user.for_each_user(_bad_job)

    assert len(calls) == 1
    assert calls[0][1]["source"] == "scheduler.per-user"
    assert calls[0][1]["severity"] == "error"
    assert "Affected provider/subsystem:" in calls[0][0][0]
    assert "user_id `" not in calls[0][0][0]
    assert get_current_user_id() is None
    set_current_user_id(None)


def _db_operational_error() -> OperationalError:
    return OperationalError("SELECT user_id FROM user", {}, Exception("SSL EOF"))


class _FailingBootstrapSession:
    def __init__(self):
        self.rollback_called = False
        self.close_called = False

    def query(self, *_args, **_kwargs):
        return self

    def all(self):
        raise _db_operational_error()

    def rollback(self):
        self.rollback_called = True

    def close(self):
        self.close_called = True


class _SuccessfulBootstrapSession:
    def __init__(self, user_ids):
        self.user_ids = user_ids
        self.close_called = False

    def query(self, *_args, **_kwargs):
        return self

    def all(self):
        return [(user_id,) for user_id in self.user_ids]

    def close(self):
        self.close_called = True


class _UserSession:
    def __init__(self, user_id):
        self.user = SimpleNamespace(user_id=user_id)
        self.close_called = False

    def query(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def one_or_none(self):
        return self.user

    def close(self):
        self.close_called = True


class _FailingUserLoadSession:
    def __init__(self):
        self.rollback_called = False
        self.close_called = False

    def query(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def one_or_none(self):
        raise _db_operational_error()

    def rollback(self):
        self.rollback_called = True

    def close(self):
        self.close_called = True


class _FakeEngine:
    def __init__(self):
        self.dispose_calls = 0

    def dispose(self):
        self.dispose_calls += 1


def test_for_each_user_retries_bootstrap_operational_error(monkeypatch):
    fake_engine = _FakeEngine()
    sessions = [
        _FailingBootstrapSession(),
        _SuccessfulBootstrapSession([42]),
        _UserSession(42),
    ]
    sleeps = []
    calls = []

    monkeypatch.setattr(_per_user, "SessionLocal", lambda: sessions.pop(0))
    monkeypatch.setattr(_per_user, "engine", fake_engine)
    monkeypatch.setattr(_per_user.time, "sleep", lambda seconds: sleeps.append(seconds))

    def _job(job_db, scoped_user):
        calls.append((job_db, scoped_user.user_id))

    _per_user.for_each_user(_job)

    assert len(calls) == 1
    assert isinstance(calls[0][0], _UserSession)
    assert calls[0][1] == 42
    assert fake_engine.dispose_calls == 1
    assert sleeps == [_per_user.BOOTSTRAP_RETRY_DELAY_SECONDS]
    assert get_current_user_id() is None
    set_current_user_id(None)


def test_for_each_user_notifies_and_skips_after_bootstrap_operational_error(
    monkeypatch,
):
    fake_engine = _FakeEngine()
    sessions = [
        _FailingBootstrapSession()
        for _ in range(_per_user.BOOTSTRAP_MAX_ATTEMPTS)
    ]
    notifications = []
    sleeps = []
    calls = []

    monkeypatch.setattr(_per_user, "SessionLocal", lambda: sessions.pop(0))
    monkeypatch.setattr(_per_user, "engine", fake_engine)
    monkeypatch.setattr(_per_user.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(
        _per_user,
        "notify_operator",
        lambda *args, **kwargs: notifications.append((args, kwargs)) or True,
    )

    _per_user.for_each_user(lambda job_db, scoped_user: calls.append(scoped_user))

    assert calls == []
    assert len(notifications) == 1
    assert notifications[0][1]["source"] == "scheduler.per-user"
    assert notifications[0][1]["severity"] == "error"
    assert notifications[0][1]["dedupe_key"] == "bootstrap-user-ids:OperationalError"
    assert "Affected provider/subsystem:" in notifications[0][0][0]
    assert "Data integrity risk:" in notifications[0][0][0]
    assert fake_engine.dispose_calls == _per_user.BOOTSTRAP_MAX_ATTEMPTS
    assert sleeps == [_per_user.BOOTSTRAP_RETRY_DELAY_SECONDS]
    assert _per_user._bootstrap_backoff_until_monotonic > 0
    assert get_current_user_id() is None
    set_current_user_id(None)


def test_for_each_user_honors_bootstrap_db_backoff(monkeypatch):
    calls = []
    notifications = []

    monkeypatch.setattr(_per_user.time, "monotonic", lambda: 100.0)
    monkeypatch.setattr(_per_user, "_bootstrap_backoff_until_monotonic", 150.0)
    monkeypatch.setattr(
        _per_user,
        "SessionLocal",
        lambda: (_ for _ in ()).throw(AssertionError("DB should not be touched")),
    )
    monkeypatch.setattr(
        _per_user,
        "notify_operator",
        lambda *args, **kwargs: notifications.append((args, kwargs)) or True,
    )

    _per_user.for_each_user(lambda job_db, scoped_user: calls.append(scoped_user))
    _per_user.for_each_user(
        lambda job_db, scoped_user: calls.append(scoped_user),
        user_ids=[123],
        job_name="candidate_job",
    )

    assert calls == []
    assert notifications == []
    assert get_current_user_id() is None
    set_current_user_id(None)


def test_for_each_user_iteration_operational_error_opens_backoff_and_stops_fanout(
    monkeypatch,
):
    fake_engine = _FakeEngine()
    failing_user_session = _FailingUserLoadSession()
    unused_second_user = _UserSession(2)
    sessions = [
        _SuccessfulBootstrapSession([1, 2]),
        failing_user_session,
        unused_second_user,
    ]
    notifications = []
    calls = []

    monkeypatch.setattr(_per_user, "SessionLocal", lambda: sessions.pop(0))
    monkeypatch.setattr(_per_user, "engine", fake_engine)
    monkeypatch.setattr(
        _per_user,
        "notify_operator",
        lambda *args, **kwargs: notifications.append((args, kwargs)) or True,
    )

    _per_user.for_each_user(
        lambda job_db, scoped_user: calls.append(scoped_user),
        job_name="timer_overflow",
    )

    assert calls == []
    assert failing_user_session.rollback_called
    assert failing_user_session.close_called
    assert unused_second_user.close_called is False
    assert len(sessions) == 1
    assert fake_engine.dispose_calls == 1
    assert _per_user._bootstrap_backoff_until_monotonic > 0
    assert len(notifications) == 1
    assert notifications[0][1]["dedupe_key"] == "timer_overflow:OperationalError"
    assert "scheduler.per-user / timer_overflow" in notifications[0][0][0]
    assert "remaining users" in notifications[0][0][0]
    assert get_current_user_id() is None
    set_current_user_id(None)
