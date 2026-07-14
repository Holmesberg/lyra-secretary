from datetime import timedelta
from uuid import uuid4

from sqlalchemy import text

from app.db.models import (
    ExposureAckEvent,
    ExposureDecisionEvent,
    ExposureRenderEvent,
    NotificationLifecycleEvent,
    StopwatchSession,
    Task,
    TaskState,
    User,
)
from app.db.scoping import set_current_user_id
from app.services import notification_queue
from app.utils.time_utils import now_utc
from app.workers.jobs import timer_overflow


class _FakeRedis:
    def __init__(self):
        self.set_keys = []

    def exists(self, _key):
        return False

    def setex(self, key, ttl, value):
        self.set_keys.append((key, ttl, value))


class _FakeRedisClient:
    def __init__(self, redis):
        self.client = redis


def _clean(db):
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM exposure_ack_event"))
    db.execute(text("DELETE FROM exposure_render_event"))
    db.execute(text("DELETE FROM notification_lifecycle_event"))
    db.execute(text("DELETE FROM exposure_decision_event"))
    db.execute(text("DELETE FROM stopwatch_session"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM user"))
    db.commit()


def test_timer_overflow_web_copy_is_not_openclaw_reply_copy(db, monkeypatch):
    _clean(db)
    now = now_utc()
    user = User(
        user_id=8801,
        email="timer-overflow-copy@example.test",
        is_operator=True,
        created_at=now,
    )
    task = Task(
        task_id=str(uuid4()),
        user_id=user.user_id,
        title="Lyra waves",
        category="study",
        planned_start_utc=now - timedelta(minutes=50),
        planned_end_utc=now - timedelta(minutes=20),
        planned_duration_minutes=30,
        state=TaskState.EXECUTING,
        source="manual",
        created_at=now - timedelta(minutes=50),
        last_modified_at=now - timedelta(minutes=50),
    )
    session = StopwatchSession(
        session_id=str(uuid4()),
        user_id=user.user_id,
        task_id=task.task_id,
        start_time_utc=now - timedelta(minutes=50),
        total_paused_minutes=0,
        auto_closed=False,
    )
    db.add_all([user, task, session])
    db.commit()

    fake_redis = _FakeRedis()
    queued = []
    operator_alerts = []

    monkeypatch.setattr(
        timer_overflow,
        "RedisClient",
        lambda: _FakeRedisClient(fake_redis),
    )
    monkeypatch.setattr(
        notification_queue,
        "RedisClient",
        lambda: _FakeRedisClient(fake_redis),
    )
    monkeypatch.setattr(
        timer_overflow,
        "enqueue_user_notification",
        lambda user_id, payload, **_kwargs: queued.append((user_id, payload)),
    )
    monkeypatch.setattr(
        timer_overflow,
        "notify_operator",
        lambda message, **kwargs: operator_alerts.append((message, kwargs)) or True,
    )

    set_current_user_id(user.user_id)
    try:
        timer_overflow._run_for_one_user(db, user)
    finally:
        set_current_user_id(None)

    assert len(queued) == 1
    user_id, payload = queued[0]
    assert user_id == user.user_id
    assert payload["type"] == "timer_overflow"
    assert payload["task_id"] == task.task_id
    assert payload["session_id"] == session.session_id
    assert "Open the task to stop or correct the timer." in payload["message"]
    assert "Reply with" not in payload["message"]
    assert "completion percentage" not in payload["message"]

    assert len(operator_alerts) == 1
    message, kwargs = operator_alerts[0]
    assert "Reply with 'done'" in message
    assert kwargs["source"] == "scheduler.timer-overflow"
    assert fake_redis.set_keys


def test_five_minute_timer_overflow_enqueues_when_still_running_after_grace(db, monkeypatch):
    _clean(db)
    now = now_utc()
    user = User(
        user_id=8804,
        email="timer-overflow-five-minute@example.test",
        is_operator=False,
        created_at=now,
    )
    task = Task(
        task_id=str(uuid4()),
        user_id=user.user_id,
        title="Five minute task",
        category="study",
        planned_start_utc=now - timedelta(minutes=11),
        planned_end_utc=now - timedelta(minutes=6),
        planned_duration_minutes=5,
        state=TaskState.EXECUTING,
        source="manual",
        created_at=now - timedelta(minutes=11),
        last_modified_at=now - timedelta(minutes=11),
    )
    session = StopwatchSession(
        session_id=str(uuid4()),
        user_id=user.user_id,
        task_id=task.task_id,
        start_time_utc=now - timedelta(minutes=11),
        total_paused_minutes=0,
        auto_closed=False,
    )
    db.add_all([user, task, session])
    db.commit()

    fake_redis = _FakeRedis()
    queued = []

    monkeypatch.setattr(
        timer_overflow,
        "RedisClient",
        lambda: _FakeRedisClient(fake_redis),
    )
    monkeypatch.setattr(
        notification_queue,
        "RedisClient",
        lambda: _FakeRedisClient(fake_redis),
    )
    monkeypatch.setattr(
        timer_overflow,
        "enqueue_user_notification",
        lambda user_id, payload, **_kwargs: queued.append((user_id, payload)),
    )

    set_current_user_id(user.user_id)
    try:
        timer_overflow._run_for_one_user(db, user)
    finally:
        set_current_user_id(None)

    assert len(queued) == 1
    user_id, payload = queued[0]
    assert user_id == user.user_id
    assert payload["type"] == "timer_overflow"
    assert payload["task_id"] == task.task_id
    assert payload["session_id"] == session.session_id
    assert payload["planned_minutes"] == 5
    assert payload["elapsed_minutes"] == 11
    assert fake_redis.set_keys


class _QueueRedis:
    def __init__(self):
        self.items = []
        self.set_keys = []
        self.exists_keys = set()

    def exists(self, key):
        return key in self.exists_keys

    def setex(self, key, ttl, value):
        self.set_keys.append((key, ttl, value))
        self.exists_keys.add(key)

    def rpush(self, _key, value):
        self.items.append(value)

    def lrange(self, _key, _start, _end):
        return list(self.items)

    def lrem(self, _key, count, value):
        removed = 0
        kept = []
        for item in self.items:
            if item == value and (count == 0 or removed < count):
                removed += 1
            else:
                kept.append(item)
        self.items = kept
        return removed

    def delete(self, _key):
        self.items = []


def test_timer_overflow_records_lifecycle_and_render_ack(db, monkeypatch):
    _clean(db)
    now = now_utc()
    user = User(
        user_id=8802,
        email="timer-overflow-lifecycle@example.test",
        is_operator=False,
        created_at=now,
    )
    task = Task(
        task_id=str(uuid4()),
        user_id=user.user_id,
        title="Lifecycle task",
        category="study",
        planned_start_utc=now - timedelta(minutes=50),
        planned_end_utc=now - timedelta(minutes=20),
        planned_duration_minutes=30,
        state=TaskState.EXECUTING,
        source="manual",
        created_at=now - timedelta(minutes=50),
        last_modified_at=now - timedelta(minutes=50),
    )
    session = StopwatchSession(
        session_id=str(uuid4()),
        user_id=user.user_id,
        task_id=task.task_id,
        start_time_utc=now - timedelta(minutes=50),
        total_paused_minutes=0,
        auto_closed=False,
    )
    db.add_all([user, task, session])
    db.commit()

    fake_redis = _QueueRedis()
    monkeypatch.setattr(
        timer_overflow,
        "RedisClient",
        lambda: _FakeRedisClient(fake_redis),
    )
    monkeypatch.setattr(
        notification_queue,
        "RedisClient",
        lambda: _FakeRedisClient(fake_redis),
    )

    set_current_user_id(user.user_id)
    try:
        timer_overflow._run_for_one_user(db, user)
    finally:
        set_current_user_id(None)

    lifecycle = (
        db.query(NotificationLifecycleEvent)
        .filter(NotificationLifecycleEvent.user_id == user.user_id)
        .one()
    )
    assert lifecycle.notification_type == "timer_overflow"
    assert lifecycle.status == "queued"
    assert lifecycle.surface_id == "worker.timer_overflow"
    assert lifecycle.exposure_id

    decision = (
        db.query(ExposureDecisionEvent)
        .filter(ExposureDecisionEvent.exposure_id == lifecycle.exposure_id)
        .one()
    )
    assert decision.decision_status == "queued"
    assert decision.trigger_source == "worker.timer_overflow"
    assert db.query(ExposureRenderEvent).count() == 0

    from app.services.notification_queue import ack_user_notifications

    ack_user_notifications(
        user.user_id,
        [lifecycle.notification_id],
        db=db,
        event_type="rendered",
    )
    db.commit()

    db.refresh(lifecycle)
    db.refresh(decision)
    assert lifecycle.status == "rendered"
    assert lifecycle.rendered_at is not None
    assert decision.decision_status == "rendered"
    assert db.query(ExposureRenderEvent).count() == 1
    assert db.query(ExposureAckEvent).count() == 1


def test_timer_overflow_db_lifecycle_prevents_redis_restart_duplicate(db, monkeypatch):
    _clean(db)
    now = now_utc()
    user = User(
        user_id=8803,
        email="timer-overflow-durable@example.test",
        is_operator=False,
        created_at=now,
    )
    task = Task(
        task_id=str(uuid4()),
        user_id=user.user_id,
        title="Durable dedupe task",
        category="study",
        planned_start_utc=now - timedelta(minutes=50),
        planned_end_utc=now - timedelta(minutes=20),
        planned_duration_minutes=30,
        state=TaskState.EXECUTING,
        source="manual",
        created_at=now - timedelta(minutes=50),
        last_modified_at=now - timedelta(minutes=50),
    )
    session = StopwatchSession(
        session_id=str(uuid4()),
        user_id=user.user_id,
        task_id=task.task_id,
        start_time_utc=now - timedelta(minutes=50),
        total_paused_minutes=0,
        auto_closed=False,
    )
    db.add_all([user, task, session])
    db.commit()

    first_redis = _QueueRedis()
    monkeypatch.setattr(
        timer_overflow,
        "RedisClient",
        lambda: _FakeRedisClient(first_redis),
    )
    monkeypatch.setattr(
        notification_queue,
        "RedisClient",
        lambda: _FakeRedisClient(first_redis),
    )

    set_current_user_id(user.user_id)
    try:
        timer_overflow._run_for_one_user(db, user)
    finally:
        set_current_user_id(None)
    assert len(first_redis.items) == 1

    restarted_redis = _QueueRedis()
    monkeypatch.setattr(
        timer_overflow,
        "RedisClient",
        lambda: _FakeRedisClient(restarted_redis),
    )
    monkeypatch.setattr(
        notification_queue,
        "RedisClient",
        lambda: _FakeRedisClient(restarted_redis),
    )

    set_current_user_id(user.user_id)
    try:
        timer_overflow._run_for_one_user(db, user)
    finally:
        set_current_user_id(None)

    assert restarted_redis.items == []
    assert (
        db.query(NotificationLifecycleEvent)
        .filter(NotificationLifecycleEvent.notification_type == "timer_overflow")
        .count()
    ) == 1
