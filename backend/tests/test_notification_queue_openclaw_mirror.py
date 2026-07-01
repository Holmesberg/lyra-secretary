"""OpenClaw operator mirror for user notification queue events."""
import json
from uuid import uuid4

from app.db.models import (
    ExposureAckEvent,
    ExposureRenderEvent,
    NotificationLifecycleEvent,
    User,
)
from app.services import notification_queue
from app.services.output_surfaces import create_output_surface_decision


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

    assert len(pushes) == 1
    assert pushes[0][0] == "notifications:pending:42"
    queued_payload = json.loads(pushes[0][1])
    assert queued_payload["notification_id"]
    assert {k: v for k, v in queued_payload.items() if k != "notification_id"} == payload
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


def test_web_channel_preserves_operator_alerts_for_openclaw(monkeypatch):
    class QueueRedis:
        def __init__(self):
            self.items = [
                json.dumps({"notification_id": "op-1", "type": "operator_alert", "message": "internal triage"}),
                json.dumps({"notification_id": "web-1", "type": "timer_overflow", "message": "Open the task."}),
                json.dumps({"notification_id": "op-2", "type": "operator_alert", "message": "second alert"}),
            ]
            self.rpushed = []

        def lrange(self, _key, _start, _end):
            return list(self.items)

        def lpop(self, _key):
            if not self.items:
                return None
            return self.items.pop(0)

        def delete(self, _key):
            self.items = []

        def rpush(self, key, value):
            self.rpushed.append((key, value))
            self.items.append(value)

    queue = QueueRedis()

    class QueueRedisClient:
        client = queue

    monkeypatch.setattr(
        notification_queue,
        "RedisClient",
        lambda: QueueRedisClient(),
    )

    web_items = notification_queue.peek_user_notifications(1, channel="web")
    assert web_items == [
        {
            "notification_id": "web-1",
            "type": "timer_overflow",
            "message": "Open the task.",
        }
    ]
    assert [json.loads(raw)["type"] for raw in queue.items] == [
        "operator_alert",
        "timer_overflow",
        "operator_alert",
    ]

    assert notification_queue.ack_user_notifications(1, ["web-1"]) == 1
    assert [json.loads(raw)["type"] for raw in queue.items] == [
        "operator_alert",
        "operator_alert",
    ]

    openclaw_items = notification_queue.drain_user_notifications(1)
    assert [item["message"] for item in openclaw_items] == [
        "internal triage",
        "second alert",
    ]


class _LifecycleRedis:
    def __init__(self):
        self.items = []

    def rpush(self, _key, value):
        self.items.append(value)

    def lrange(self, _key, _start, _end):
        return list(self.items)

    def delete(self, _key):
        self.items = []


class _LifecycleRedisClient:
    def __init__(self, redis):
        self.client = redis


def test_web_pending_reserves_and_render_ack_marks_only_rendered(db, monkeypatch):
    redis = _LifecycleRedis()
    monkeypatch.setattr(
        notification_queue,
        "RedisClient",
        lambda: _LifecycleRedisClient(redis),
    )
    user = User(email=f"notification-lifecycle-{uuid4()}@example.test")
    db.add(user)
    db.commit()

    payload = {"type": "timer_overflow", "message": "Open the task."}
    notification_queue.enqueue_user_notification(user.user_id, payload, db=db)
    db.commit()

    pending = notification_queue.peek_user_notifications(user.user_id, db=db)
    db.commit()
    notification_id = pending[0]["notification_id"]

    lifecycle = (
        db.query(NotificationLifecycleEvent)
        .filter(NotificationLifecycleEvent.notification_id == notification_id)
        .one()
    )
    assert lifecycle.status == "reserved"
    assert lifecycle.reserved_at is not None
    assert lifecycle.rendered_at is None

    removed = notification_queue.ack_user_notifications(
        user.user_id,
        [notification_id],
        db=db,
        event_type="rendered",
    )
    db.commit()

    db.refresh(lifecycle)
    assert removed == 1
    assert lifecycle.status == "rendered"
    assert lifecycle.rendered_at is not None
    assert lifecycle.lost_unrendered_at is None
    assert redis.items == []


def test_notification_lifecycle_bounds_legacy_overlong_ids(db, monkeypatch):
    redis = _LifecycleRedis()
    monkeypatch.setattr(
        notification_queue,
        "RedisClient",
        lambda: _LifecycleRedisClient(redis),
    )
    user = User(email=f"notification-overlong-{uuid4()}@example.test")
    db.add(user)
    db.commit()

    overlong_task_id = f"legacy-task-id-{uuid4()}-{uuid4()}"
    notification_queue.enqueue_user_notification(
        user.user_id,
        {
            "notification_id": f"notif-{uuid4()}",
            "type": "resume_prediction",
            "task_id": overlong_task_id,
            "session_id": f"legacy-session-id-{uuid4()}-{uuid4()}",
            "firing_id": f"legacy-firing-id-{uuid4()}-{uuid4()}",
            "message": "Legacy bridge payload",
        },
        db=db,
    )
    db.commit()

    lifecycle = (
        db.query(NotificationLifecycleEvent)
        .filter(NotificationLifecycleEvent.user_id == user.user_id)
        .one()
    )
    assert lifecycle.status == "queued"
    assert lifecycle.task_id.startswith("hash:")
    assert lifecycle.session_id.startswith("hash:")
    assert lifecycle.firing_id.startswith("hash:")
    assert len(lifecycle.task_id) <= 36
    assert len(lifecycle.session_id) <= 36
    assert len(lifecycle.firing_id) <= 36
    assert overlong_task_id not in {lifecycle.task_id, lifecycle.session_id, lifecycle.firing_id}


def test_lost_unrendered_ack_does_not_mark_rendered(db, monkeypatch):
    redis = _LifecycleRedis()
    monkeypatch.setattr(
        notification_queue,
        "RedisClient",
        lambda: _LifecycleRedisClient(redis),
    )
    user = User(email=f"notification-lifecycle-{uuid4()}@example.test")
    db.add(user)
    db.commit()

    notification_queue.enqueue_user_notification(
        user.user_id,
        {"type": "unknown_new_type", "message": "Unsupported payload"},
        db=db,
    )
    db.commit()

    pending = notification_queue.peek_user_notifications(user.user_id, db=db)
    db.commit()
    notification_id = pending[0]["notification_id"]

    removed = notification_queue.ack_user_notifications(
        user.user_id,
        [notification_id],
        db=db,
        event_type="lost_unrendered",
    )
    db.commit()

    lifecycle = (
        db.query(NotificationLifecycleEvent)
        .filter(NotificationLifecycleEvent.notification_id == notification_id)
        .one()
    )
    assert removed == 1
    assert lifecycle.status == "lost_unrendered"
    assert lifecycle.lost_unrendered_at is not None
    assert lifecycle.rendered_at is None


def test_notification_action_and_expiry_update_after_render_removal(db, monkeypatch):
    redis = _LifecycleRedis()
    monkeypatch.setattr(
        notification_queue,
        "RedisClient",
        lambda: _LifecycleRedisClient(redis),
    )
    user = User(email=f"notification-terminal-{uuid4()}@example.test")
    db.add(user)
    db.commit()

    acted_id = f"acted-{uuid4()}"
    expired_id = f"expired-{uuid4()}"
    notification_queue.enqueue_user_notification(
        user.user_id,
        {
            "notification_id": acted_id,
            "type": "timer_overflow",
            "message": "Open the task.",
            "planned_minutes": 30,
            "elapsed_minutes": 45,
        },
        db=db,
    )
    notification_queue.enqueue_user_notification(
        user.user_id,
        {
            "notification_id": expired_id,
            "type": "reminder",
            "message": "Check the next block.",
        },
        db=db,
    )
    db.commit()

    pending = notification_queue.peek_user_notifications(user.user_id, db=db)
    assert {row["notification_id"] for row in pending} == {acted_id, expired_id}
    assert notification_queue.ack_user_notifications(
        user.user_id,
        [acted_id, expired_id],
        db=db,
        event_type="rendered",
    ) == 2
    db.commit()
    assert redis.items == []

    assert notification_queue.ack_user_notifications(
        user.user_id,
        [acted_id],
        db=db,
        event_type="acted",
    ) == 0
    assert notification_queue.ack_user_notifications(
        user.user_id,
        [expired_id],
        db=db,
        event_type="expired",
    ) == 0
    db.commit()

    acted = (
        db.query(NotificationLifecycleEvent)
        .filter(NotificationLifecycleEvent.notification_id == acted_id)
        .one()
    )
    expired = (
        db.query(NotificationLifecycleEvent)
        .filter(NotificationLifecycleEvent.notification_id == expired_id)
        .one()
    )
    assert acted.status == "acted"
    assert acted.rendered_at is not None
    assert acted.acted_at is not None
    assert acted.dismissed_at is None
    assert expired.status == "expired"
    assert expired.rendered_at is not None
    assert expired.expired_at is not None
    assert expired.acted_at is None


def test_linked_notification_render_records_exposure_once(db, monkeypatch):
    redis = _LifecycleRedis()
    monkeypatch.setattr(
        notification_queue,
        "RedisClient",
        lambda: _LifecycleRedisClient(redis),
    )
    user = User(email=f"notification-linked-exposure-{uuid4()}@example.test")
    db.add(user)
    db.flush()
    decision = create_output_surface_decision(
        db,
        surface_id="worker.resume_prediction",
        user_id=user.user_id,
        decision_status="delivered",
        content_template_id="resume_prediction",
        trigger_source="worker.resume_prediction",
    )
    db.commit()

    notification_id = f"linked-exposure-{uuid4()}"
    notification_queue.enqueue_user_notification(
        user.user_id,
        {
            "notification_id": notification_id,
            "type": "resume_prediction",
            "message": "Pick it back up?",
            "surface_id": "worker.resume_prediction",
            "exposure_id": decision.exposure_id,
        },
        db=db,
        surface_id="worker.resume_prediction",
        exposure_id=decision.exposure_id,
        content_snapshot="Pick it back up?",
    )
    db.commit()

    pending = notification_queue.peek_user_notifications(user.user_id, db=db)
    assert [row["notification_id"] for row in pending] == [notification_id]
    removed = notification_queue.ack_user_notifications(
        user.user_id,
        [notification_id],
        db=db,
        event_type="rendered",
    )
    db.commit()

    db.refresh(decision)
    render_rows = (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.exposure_id == decision.exposure_id)
        .all()
    )
    ack_rows = (
        db.query(ExposureAckEvent)
        .filter(ExposureAckEvent.exposure_id == decision.exposure_id)
        .all()
    )
    lifecycle = (
        db.query(NotificationLifecycleEvent)
        .filter(NotificationLifecycleEvent.notification_id == notification_id)
        .one()
    )
    assert removed == 1
    assert redis.items == []
    assert decision.decision_status == "rendered"
    assert lifecycle.status == "rendered"
    assert lifecycle.exposure_id == decision.exposure_id
    assert lifecycle.surface_id == "worker.resume_prediction"
    assert len(render_rows) == 1
    assert render_rows[0].surface == "worker.resume_prediction"
    assert render_rows[0].channel == "notification_queue"
    assert render_rows[0].content_snapshot == "Pick it back up?"
    assert len(ack_rows) == 1
    assert ack_rows[0].event_type == "render"
    assert ack_rows[0].client_event_id == f"notification:{notification_id}"

    assert notification_queue.ack_user_notifications(
        user.user_id,
        [notification_id],
        db=db,
        event_type="acted",
    ) == 0
    assert notification_queue.ack_user_notifications(
        user.user_id,
        [notification_id],
        db=db,
        event_type="rendered",
    ) == 0
    db.commit()

    assert (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.exposure_id == decision.exposure_id)
        .count()
    ) == 1
    assert (
        db.query(ExposureAckEvent)
        .filter(ExposureAckEvent.exposure_id == decision.exposure_id)
        .count()
    ) == 1
    db.refresh(lifecycle)
    assert lifecycle.status == "acted"
    assert lifecycle.acted_at is not None
