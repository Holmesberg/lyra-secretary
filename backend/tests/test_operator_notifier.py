import json

import pytest

from app.services import operator_notifier
from app.services.operator_notifier import (
    clear_operator_notification_dedupe,
    format_alert_context,
    notify_operator,
    redacted_user_ref,
)


class _FakeRedisClient:
    def __init__(self, pushes, store=None):
        self.client = _FakeRedis(pushes, store if store is not None else {})


class _FakeRedis:
    def __init__(self, pushes, store):
        self._pushes = pushes
        self._store = store

    def rpush(self, key, value):
        self._pushes.append((key, value))

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self._store:
            return None
        self._store[key] = {"value": value, "ex": ex}
        return True

    def delete(self, key):
        return 1 if self._store.pop(key, None) is not None else 0


@pytest.fixture(autouse=True)
def _clear_dedupe():
    clear_operator_notification_dedupe()
    yield
    clear_operator_notification_dedupe()


def test_notify_operator_queues_openclaw_operator_alert(monkeypatch):
    pushes = []
    monkeypatch.setattr(
        operator_notifier,
        "RedisClient",
        lambda: _FakeRedisClient(pushes),
    )
    monkeypatch.setattr(
        operator_notifier.settings,
        "OPENCLAW_OPERATOR_USER_ID",
        1,
    )
    monkeypatch.setattr(
        operator_notifier.settings,
        "OPENCLAW_OPERATOR_NOTIFICATIONS_ENABLED",
        True,
    )

    assert notify_operator("hello", source="unit.test", severity="warn")

    assert len(pushes) == 1
    key, raw = pushes[0]
    payload = json.loads(raw)
    assert key == "notifications:pending:1"
    assert payload["type"] == "operator_alert"
    assert payload["source"] == "unit.test"
    assert payload["severity"] == "warn"
    assert "[warn] [unit.test]" in payload["message"]
    assert "hello" in payload["message"]
    assert payload["created_at"]


def test_notify_operator_dedupes_with_cooldown(monkeypatch):
    pushes = []
    store = {}
    monkeypatch.setattr(
        operator_notifier,
        "RedisClient",
        lambda: _FakeRedisClient(pushes, store),
    )
    monkeypatch.setattr(
        operator_notifier.settings,
        "OPENCLAW_OPERATOR_NOTIFICATIONS_ENABLED",
        True,
    )

    assert notify_operator(
        "first",
        source="unit.test",
        severity="error",
        dedupe_key="same",
        cooldown_seconds=60,
    )
    assert not notify_operator(
        "second",
        source="unit.test",
        severity="error",
        dedupe_key="same",
        cooldown_seconds=60,
    )

    assert len(pushes) == 1
    assert len(store) == 1


def test_notify_operator_dedupe_survives_process_restart(monkeypatch):
    pushes = []
    store = {}
    monkeypatch.setattr(
        operator_notifier,
        "RedisClient",
        lambda: _FakeRedisClient(pushes, store),
    )
    monkeypatch.setattr(
        operator_notifier.settings,
        "OPENCLAW_OPERATOR_NOTIFICATIONS_ENABLED",
        True,
    )

    assert notify_operator(
        "first",
        source="unit.test",
        severity="error",
        dedupe_key="same",
        cooldown_seconds=60,
    )

    clear_operator_notification_dedupe()

    assert not notify_operator(
        "second",
        source="unit.test",
        severity="error",
        dedupe_key="same",
        cooldown_seconds=60,
    )
    assert len(pushes) == 1


def test_notify_operator_never_raises_on_queue_failure(monkeypatch):
    class BrokenRedisClient:
        @property
        def client(self):
            raise RuntimeError("redis down")

    monkeypatch.setattr(operator_notifier, "RedisClient", BrokenRedisClient)

    assert not notify_operator("hello", source="unit.test", severity="error")


def test_notify_operator_can_be_disabled(monkeypatch):
    pushes = []
    monkeypatch.setattr(
        operator_notifier,
        "RedisClient",
        lambda: _FakeRedisClient(pushes),
    )
    monkeypatch.setattr(
        operator_notifier.settings,
        "OPENCLAW_OPERATOR_NOTIFICATIONS_ENABLED",
        False,
    )

    assert not notify_operator("hello", source="unit.test", severity="info")
    assert pushes == []


def test_redacted_user_ref_is_stable_and_non_raw():
    first = redacted_user_ref(17)
    second = redacted_user_ref(17)

    assert first == second
    assert first.startswith("user#")
    assert "17" not in first


def test_format_alert_context_includes_triage_fields():
    context = format_alert_context(
        affected="scheduler.per-user / database bootstrap",
        scope="unknown user count",
        retry="Retries once, then skips this scheduler tick.",
        user_action="No user action; operator should inspect backend logs.",
        data_integrity="No mutation attempted before bootstrap completed.",
    )

    assert "Affected provider/subsystem:" in context
    assert "Affected user scope:" in context
    assert "Retry behavior:" in context
    assert "User action needed:" in context
    assert "Data integrity risk:" in context
