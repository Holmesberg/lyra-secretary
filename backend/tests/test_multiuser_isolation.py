"""Multi-user isolation acceptance gate.

Phase 1 of the multi-user pivot. These tests are the structural defense
against cross-user data leaks. If any of them fails, the migration is
not safe to ship.

Strategy: seed two users + tasks, then drive the SQLAlchemy ORM through
the same scoping ContextVar that the FastAPI dependency uses, and assert
that user A cannot see, count, or fetch user B's rows via any normal
ORM query path.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.db.models import Task, User
from app.db.scoping import set_current_user_id


@pytest.fixture
def two_users(db):
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM user"))
    now = datetime.utcnow()
    db.add_all([
        User(user_id=1, email="op@x", is_operator=True, notion_enabled=True, created_at=now),
        User(user_id=2, email="alice@x", is_operator=False, notion_enabled=False, created_at=now),
    ])
    db.flush()
    db.add_all([
        Task(
            task_id="t1-op", title="op task", user_id=1,
            planned_start_utc=now, planned_end_utc=now + timedelta(minutes=30),
            planned_duration_minutes=30, state="PLANNED", source="manual",
            created_at=now, last_modified_at=now,
        ),
        Task(
            task_id="t2-alice", title="alice task", user_id=2,
            planned_start_utc=now, planned_end_utc=now + timedelta(minutes=45),
            planned_duration_minutes=45, state="PLANNED", source="manual",
            created_at=now, last_modified_at=now,
        ),
    ])
    db.commit()
    yield db
    set_current_user_id(None)


def test_unscoped_sees_both(two_users):
    set_current_user_id(None)
    rows = two_users.query(Task).all()
    assert len(rows) == 2


def test_user1_sees_only_own(two_users):
    set_current_user_id(1)
    rows = two_users.query(Task).all()
    assert [r.task_id for r in rows] == ["t1-op"]


def test_user2_sees_only_own(two_users):
    set_current_user_id(2)
    rows = two_users.query(Task).all()
    assert [r.task_id for r in rows] == ["t2-alice"]


def test_user1_cannot_fetch_user2_by_id(two_users):
    set_current_user_id(1)
    row = two_users.query(Task).filter(Task.task_id == "t2-alice").first()
    assert row is None, "scoping hook leaked a cross-user row by primary key"


def test_user2_cannot_fetch_user1_by_id(two_users):
    set_current_user_id(2)
    row = two_users.query(Task).filter(Task.task_id == "t1-op").first()
    assert row is None


def test_count_is_scoped(two_users):
    set_current_user_id(1)
    assert two_users.query(Task).count() == 1
    set_current_user_id(2)
    assert two_users.query(Task).count() == 1


def test_user_table_is_exempt(two_users):
    """User table has no user_id column; queries against it must NOT
    be filtered (otherwise login can't load the requesting user)."""
    set_current_user_id(1)
    assert two_users.query(User).count() == 2
