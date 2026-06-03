"""OpenClaw operator mirror for user notification queue events."""
import json

from app.services import notification_queue


class _FakeRedisClient:
    def __init__(self, pushes):
        self.client = _FakeRedis(pushes)


class _FakeRedis:
    def __init__(self, pushes):
        self._pushes = pushes

    def rpush(self, key, value):
        self._pushes.append((key, value))


def test_enqueue_user_notification_mirrors_redacted_metadata(monkeypatch):
    pushes = []
    calls = []
    payload = {
        "type": "resume_prediction",
        "task_title": "secret thesis rewrite",
        "message": "Pick the private task back up?",
        "task_id": "task-private-123",
        "firing_id": "fire-private-456",
        "confidence": 0.84,
    }

    monkeypatch.setattr(
        notification_queue,
        "RedisClient",
        lambda: _FakeRedisClient(pushes),
    )
    monkeypatch.setattr(
        notification_queue.settings,
        "OPENCLAW_MIRROR_USER_NOTIFICATIONS",
        True,
    )
    monkeypatch.setattr(
        notification_queue,
        "notify_operator",
        lambda message, **kwargs: calls.append((message, kwargs)) or True,
    )

    notification_queue.enqueue_user_notification(42, payload)

    assert pushes == [("notifications:pending:42", json.dumps(payload))]
    assert len(calls) == 1
    message, kwargs = calls[0]
    assert kwargs["source"] == "user.notification-queue"
    assert kwargs["severity"] == "info"
    assert "User notification queued." in message
    assert "User: user#" in message
    assert "Type: `resume_prediction`" in message
    assert "confidence=`0.84`" in message
    assert "task_id=#" in message
    assert "firing_id=#" in message
    assert "Content redacted:" in message
    assert "secret thesis rewrite" not in message
    assert "Pick the private task back up?" not in message
    assert "task-private-123" not in message
    assert "fire-private-456" not in message


def test_enqueue_user_notification_survives_operator_mirror_failure(monkeypatch):
    pushes = []
    monkeypatch.setattr(
        notification_queue,
        "RedisClient",
        lambda: _FakeRedisClient(pushes),
    )
    monkeypatch.setattr(
        notification_queue.settings,
        "OPENCLAW_MIRROR_USER_NOTIFICATIONS",
        True,
    )

    def fail_notify(*_args, **_kwargs):
        raise RuntimeError("telegram down")

    monkeypatch.setattr(notification_queue, "notify_operator", fail_notify)

    notification_queue.enqueue_user_notification(
        17, {"type": "reminder", "message": "private reminder"}
    )

    assert len(pushes) == 1
    assert pushes[0][0] == "notifications:pending:17"


def test_user_notification_operator_mirror_can_be_disabled(monkeypatch):
    calls = []
    monkeypatch.setattr(
        notification_queue.settings,
        "OPENCLAW_MIRROR_USER_NOTIFICATIONS",
        False,
    )
    monkeypatch.setattr(
        notification_queue,
        "notify_operator",
        lambda message, **kwargs: calls.append((message, kwargs)) or True,
    )

    assert not notification_queue.mirror_user_notification_to_operator(
        99, {"type": "timer_overflow"}
    )
    assert calls == []


def test_user_notification_operator_mirror_skips_operator_owned_queue(monkeypatch):
    calls = []
    monkeypatch.setattr(
        notification_queue.settings,
        "OPENCLAW_MIRROR_USER_NOTIFICATIONS",
        True,
    )
    monkeypatch.setattr(
        notification_queue.settings,
        "OPENCLAW_OPERATOR_USER_ID",
        1,
    )
    monkeypatch.setattr(
        notification_queue,
        "notify_operator",
        lambda message, **kwargs: calls.append((message, kwargs)) or True,
    )

    assert not notification_queue.mirror_user_notification_to_operator(
        1, {"type": "reminder", "message": "operator-owned reminder"}
    )
    assert calls == []


def test_user_notification_mirror_hashes_unsafe_safe_field_values(monkeypatch):
    calls = []
    payload = {
        "type": "https://private.example.test/task",
        "mechanism": "bearer secret-token-value",
        "message": "private message",
    }

    monkeypatch.setattr(
        notification_queue.settings,
        "OPENCLAW_MIRROR_USER_NOTIFICATIONS",
        True,
    )
    monkeypatch.setattr(
        notification_queue,
        "notify_operator",
        lambda message, **kwargs: calls.append((message, kwargs)) or True,
    )

    assert notification_queue.mirror_user_notification_to_operator(5, payload)

    message, _kwargs = calls[0]
    assert "https://private.example.test/task" not in message
    assert "bearer secret-token-value" not in message
    assert "private message" not in message
    assert "Type: `#" in message
    assert "mechanism=`#" in message
