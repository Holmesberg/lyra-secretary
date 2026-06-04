from datetime import timedelta
from uuid import uuid4

from sqlalchemy import text

from app.db.models import StopwatchSession, Task, TaskState, User
from app.db.scoping import set_current_user_id
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
        timer_overflow,
        "enqueue_user_notification",
        lambda user_id, payload: queued.append((user_id, payload)),
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
