from datetime import timedelta
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db.models import Task, TaskState, User
from app.db.scoping import set_current_user_id
from app.utils.time_utils import now_utc
from app.workers.jobs import reminders
from tests.conftest import TestingSession


def _clean_tables(db):
    set_current_user_id(None)
    db.rollback()
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

    assert reminders._load_candidate_user_ids() == []
    assert dispose_count == reminders.REMINDER_BOOTSTRAP_MAX_ATTEMPTS
    assert notifications
    assert notifications[0][1]["source"] == "scheduler.reminders"
    assert "No reminder notification" in notifications[0][0]
