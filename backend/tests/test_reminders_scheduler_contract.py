from datetime import timedelta
import json
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db.models import NotificationLifecycleEvent, Task, TaskState, User
from app.db.scoping import set_current_user_id
from app.services import notification_queue
from app.utils.time_utils import now_utc
from app.workers.jobs import reminders
from app.workers.jobs._scheduler_contract import (
    JobResult,
    NO_MUTATION_ATTEMPTED,
    SchedulerJobDegraded,
    reset_degradation_backoff,
)
from tests.conftest import TestingSession


def _clean_tables(db):
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM exposure_ack_event"))
    db.execute(text("DELETE FROM exposure_render_event"))
    db.execute(text("DELETE FROM notification_lifecycle_event"))
    db.execute(text("DELETE FROM exposure_decision_event"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM user"))
    db.commit()


def _make_user(db, user_id: int) -> User:
    user = User(
        user_id=user_id,
        email=f"reminder-contract-{user_id}@example.test",
        created_at=now_utc(),
    )
    db.add(user)
    db.commit()
    return user


def _make_task(db, *, user_id: int, state: TaskState, starts_in_minutes: int, voided=False):
    start = now_utc() + timedelta(minutes=starts_in_minutes)
    task = Task(
        task_id=str(uuid4()),
        title=f"reminder-contract-{user_id}-{starts_in_minutes}",
        user_id=user_id,
        planned_start_utc=start,
        planned_end_utc=start + timedelta(minutes=30),
        planned_duration_minutes=30,
        state=state,
        source="manual",
        created_at=now_utc(),
        last_modified_at=now_utc(),
        voided_at=now_utc() if voided else None,
    )
    db.add(task)
    db.commit()
    return task


def test_reminder_candidate_bootstrap_only_returns_due_planned_users(db, monkeypatch):
    _clean_tables(db)
    monkeypatch.setattr(reminders, "SessionLocal", TestingSession)

    _make_user(db, 7101)
    _make_user(db, 7102)
    _make_user(db, 7103)
    _make_user(db, 7104)

    _make_task(db, user_id=7101, state=TaskState.PLANNED, starts_in_minutes=10)
    _make_task(db, user_id=7101, state=TaskState.PLANNED, starts_in_minutes=12)
    _make_task(db, user_id=7102, state=TaskState.EXECUTING, starts_in_minutes=10)
    _make_task(db, user_id=7103, state=TaskState.PLANNED, starts_in_minutes=30)
    _make_task(
        db,
        user_id=7104,
        state=TaskState.PLANNED,
        starts_in_minutes=10,
        voided=True,
    )

    assert reminders._load_candidate_user_ids() == [7101]


def test_reminder_bootstrap_db_failure_degrades_without_raise(monkeypatch):
    class FailingSession:
        def query(self, *args, **kwargs):
            raise OperationalError("select", {}, Exception("db down"))

        def rollback(self):
            pass

        def close(self):
            pass

    notifications = []
    dispose_count = 0

    def fake_dispose():
        nonlocal dispose_count
        dispose_count += 1

    monkeypatch.setattr(reminders, "SessionLocal", FailingSession)
    monkeypatch.setattr(reminders, "_dispose_engine_pool", fake_dispose)
    monkeypatch.setattr(reminders.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        reminders,
        "notify_operator",
        lambda message, **kwargs: notifications.append((message, kwargs)) or True,
    )
    reset_degradation_backoff()

    with pytest.raises(SchedulerJobDegraded):
        reminders._load_candidate_user_ids()
    assert dispose_count == reminders.REMINDER_BOOTSTRAP_MAX_ATTEMPTS
    assert notifications
    assert notifications[0][1]["source"] == "scheduler.reminders"
    assert f"Data integrity risk: {NO_MUTATION_ATTEMPTED}" in notifications[0][0]


def test_reminder_entrypoint_returns_degraded_handled_on_bootstrap_failure(monkeypatch):
    class FailingSession:
        def query(self, *args, **kwargs):
            raise OperationalError("select", {}, Exception("db down"))

        def rollback(self):
            pass

        def close(self):
            pass

    notifications = []

    monkeypatch.setattr(reminders, "SessionLocal", FailingSession)
    monkeypatch.setattr(reminders, "_dispose_engine_pool", lambda: None)
    monkeypatch.setattr(reminders.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        reminders,
        "notify_operator",
        lambda message, **kwargs: notifications.append((message, kwargs)) or True,
    )
    reset_degradation_backoff()

    assert reminders.check_upcoming_tasks() == JobResult.DEGRADED_HANDLED
    assert len(notifications) == 1


def test_reminder_notification_payload_carries_task_dedupe_metadata(db, monkeypatch):
    _clean_tables(db)
    user = _make_user(db, 7105)
    task = _make_task(db, user_id=7105, state=TaskState.PLANNED, starts_in_minutes=10)
    queued = []
    decisions = []

    class Decision:
        exposure_id = "exp-reminder-1"

    class FakeRedis:
        def exists(self, _key):
            return False

        def setex(self, *_args):
            return True

    class FakeRedisClient:
        client = FakeRedis()

    monkeypatch.setattr(reminders, "RedisClient", lambda: FakeRedisClient())
    monkeypatch.setattr(
        reminders,
        "enqueue_user_notification",
        lambda *args, **kwargs: queued.append((args, kwargs)),
    )
    monkeypatch.setattr(
        reminders,
        "create_output_surface_decision",
        lambda *args, **kwargs: decisions.append((args, kwargs)) or Decision(),
    )

    reminders._run_for_one_user(db, user)

    assert len(queued) == 1
    args, kwargs = queued[0]
    assert args[0] == user.user_id
    payload = args[1]
    assert payload["type"] == "reminder"
    assert payload["task_id"] == task.task_id
    assert payload["dedupe_key"] == f"reminder:{user.user_id}:{task.task_id}"
    assert payload["surface_id"] == "worker.reminder"
    assert payload["exposure_id"] == "exp-reminder-1"
    assert kwargs["db"] is db
    assert kwargs["surface_id"] == "worker.reminder"
    assert kwargs["exposure_id"] == "exp-reminder-1"
    assert kwargs["dedupe_key"] == f"reminder:{user.user_id}:{task.task_id}"
    assert kwargs["content_snapshot"] == payload["message"]
    assert len(decisions) == 1
    decision_kwargs = decisions[0][1]
    assert decision_kwargs["decision_status"] == "queued"
    assert decision_kwargs["delivered_at"] is None


def test_reminder_user_queue_survives_openclaw_mirror_failure(db, monkeypatch):
    _clean_tables(db)
    user = _make_user(db, 7106)
    task = _make_task(db, user_id=7106, state=TaskState.PLANNED, starts_in_minutes=10)
    pushes = []
    store = {}

    class FakeRedis:
        def exists(self, key):
            return key in store

        def setex(self, key, _seconds, value):
            store[key] = value
            return True

        def rpush(self, key, value):
            pushes.append((key, value))
            return 1

    class FakeRedisClient:
        client = FakeRedis()

    def fail_notify(*_args, **_kwargs):
        raise RuntimeError("openclaw active session busy")

    monkeypatch.setattr(reminders, "RedisClient", lambda: FakeRedisClient())
    monkeypatch.setattr(notification_queue, "RedisClient", lambda: FakeRedisClient())
    monkeypatch.setattr(
        notification_queue.settings,
        "OPENCLAW_MIRROR_USER_NOTIFICATIONS",
        True,
    )
    monkeypatch.setattr(notification_queue.settings, "OPENCLAW_OPERATOR_USER_ID", 1)
    monkeypatch.setattr(notification_queue, "notify_operator", fail_notify)

    reminders._run_for_one_user(db, user)

    assert len(pushes) == 1
    key, raw_payload = pushes[0]
    payload = json.loads(raw_payload)
    assert key == f"notifications:pending:{user.user_id}"
    assert payload["type"] == "reminder"
    assert payload["task_id"] == task.task_id
    assert payload["surface_id"] == "worker.reminder"
    assert payload["exposure_id"]
    assert store[f"reminder_sent:{user.user_id}:{task.task_id}"] == "1"

    lifecycle = (
        db.query(NotificationLifecycleEvent)
        .filter(NotificationLifecycleEvent.user_id == user.user_id)
        .filter(NotificationLifecycleEvent.notification_type == "reminder")
        .one()
    )
    assert lifecycle.status == "queued"
    assert lifecycle.exposure_id == payload["exposure_id"]
