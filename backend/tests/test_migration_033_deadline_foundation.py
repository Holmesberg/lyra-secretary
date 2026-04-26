"""Migration 033 schema-shape tests — deadline mechanism foundation.

The conftest creates tables via `Base.metadata.create_all`, which uses the
ORM model definitions (not the raw alembic migration). These tests verify
the ORM model side of migration 033 — the migration file's upgrade()
correctness against a real DB engine is verified separately by the gates
section of Phase F (`alembic upgrade head` against a fresh sqlite db).

What this test asserts:
- New tables (`deadline`, `task_deadline_outcome`) are queryable.
- New task columns are accessible and accept None.
- Default state for new Deadline rows is 'planned' (NOT 'active').
- Deadline.is_bindable property correctly gates planned/active vs terminal.
- TaskDeadlineOutcome stores +/− delay_minutes correctly.
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from app.db.models import (
    Deadline,
    Task,
    TaskDeadlineOutcome,
    TaskState,
    TaskSource,
    User,
)


@pytest.fixture(autouse=True)
def _clean_slate(db):
    db.rollback()
    db.query(TaskDeadlineOutcome).delete()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    db.rollback()
    db.query(TaskDeadlineOutcome).delete()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()


@pytest.fixture
def user(db):
    u = User(
        email="test@example.com",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_deadline_table_columns_exist(db):
    """Deadline table has every column declared in the migration."""
    inspector = inspect(db.bind)
    cols = {c["name"] for c in inspector.get_columns("deadline")}
    expected = {
        "deadline_id", "user_id", "title", "description",
        "due_at_utc", "category_hint", "state",
        "completed_at", "voided_at", "created_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_task_deadline_outcome_table_columns_exist(db):
    inspector = inspect(db.bind)
    cols = {c["name"] for c in inspector.get_columns("task_deadline_outcome")}
    expected = {
        "task_id", "user_id", "computed_at",
        "deadline_utc_at_compute", "executed_end_utc_at_compute",
        "deadline_met", "delay_minutes", "voided_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_task_has_loop11_columns(db):
    """Task table has the 5 new Loop 11 columns."""
    inspector = inspect(db.bind)
    cols = {c["name"] for c in inspector.get_columns("task")}
    expected = {
        "deadline_id", "deadline_match_confidence", "deadline_match_source",
        "scope_bullet_count_at_plan", "scope_bullet_count_at_execute",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_deadline_default_state_is_planned(db, user):
    """Per operator decision 2026-04-26: new deadlines start in 'planned'."""
    d = Deadline(
        deadline_id=str(uuid4()),
        user_id=user.user_id,
        title="Test deadline",
        due_at_utc=datetime.utcnow() + timedelta(days=7),
        # Intentionally NOT setting state — let the default fire.
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    assert d.state == "planned"


def test_deadline_is_bindable_by_state(db, user):
    """is_bindable property gates planned/active vs terminal/voided."""
    base = dict(
        user_id=user.user_id,
        title="t",
        due_at_utc=datetime.utcnow() + timedelta(days=1),
    )

    planned = Deadline(deadline_id=str(uuid4()), state="planned", **base)
    active = Deadline(deadline_id=str(uuid4()), state="active", **base)
    completed = Deadline(deadline_id=str(uuid4()), state="completed", **base)
    missed = Deadline(deadline_id=str(uuid4()), state="missed", **base)
    skipped = Deadline(deadline_id=str(uuid4()), state="skipped", **base)
    voided = Deadline(
        deadline_id=str(uuid4()),
        state="active",
        voided_at=datetime.utcnow(),
        **base,
    )

    assert planned.is_bindable is True
    assert active.is_bindable is True
    assert completed.is_bindable is False
    assert missed.is_bindable is False
    assert skipped.is_bindable is False
    # Voided supersedes state — even if state='active', voided is not bindable.
    assert voided.is_bindable is False


def test_task_deadline_outcome_signed_delay(db, user):
    """delay_minutes is signed: + over (missed), − under (met early)."""
    # Seed a task we can reference.
    task_id = str(uuid4())
    t = Task(
        task_id=task_id,
        title="t",
        planned_start_utc=datetime.utcnow(),
        planned_end_utc=datetime.utcnow() + timedelta(hours=1),
        planned_duration_minutes=60,
        state=TaskState.EXECUTED,
        source=TaskSource.MANUAL,
        user_id=user.user_id,
    )
    db.add(t)
    db.commit()

    deadline_t = datetime(2026, 5, 1, 17, 0, 0)
    executed_t = datetime(2026, 5, 1, 17, 30, 0)  # 30 min late

    outcome = TaskDeadlineOutcome(
        task_id=task_id,
        user_id=user.user_id,
        computed_at=datetime.utcnow(),
        deadline_utc_at_compute=deadline_t,
        executed_end_utc_at_compute=executed_t,
        deadline_met=False,
        delay_minutes=30,
    )
    db.add(outcome)
    db.commit()
    db.refresh(outcome)

    assert outcome.delay_minutes == 30
    assert outcome.deadline_met is False

    # Negative case (met early)
    task_id_2 = str(uuid4())
    t2 = Task(
        task_id=task_id_2,
        title="t2",
        planned_start_utc=datetime.utcnow(),
        planned_end_utc=datetime.utcnow() + timedelta(hours=1),
        planned_duration_minutes=60,
        state=TaskState.EXECUTED,
        source=TaskSource.MANUAL,
        user_id=user.user_id,
    )
    db.add(t2)
    db.commit()

    outcome2 = TaskDeadlineOutcome(
        task_id=task_id_2,
        user_id=user.user_id,
        computed_at=datetime.utcnow(),
        deadline_utc_at_compute=deadline_t,
        executed_end_utc_at_compute=deadline_t - timedelta(minutes=15),
        deadline_met=True,
        delay_minutes=-15,
    )
    db.add(outcome2)
    db.commit()
    db.refresh(outcome2)

    assert outcome2.delay_minutes == -15
    assert outcome2.deadline_met is True


def test_task_loop11_columns_default_none(db, user):
    """All 5 new task columns default to None (backward-compat for existing rows)."""
    t = Task(
        task_id=str(uuid4()),
        title="t",
        planned_start_utc=datetime.utcnow(),
        planned_end_utc=datetime.utcnow() + timedelta(hours=1),
        planned_duration_minutes=60,
        state=TaskState.PLANNED,
        source=TaskSource.MANUAL,
        user_id=user.user_id,
        # Intentionally NOT setting the 5 Loop 11 columns.
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    assert t.deadline_id is None
    assert t.deadline_match_confidence is None
    assert t.deadline_match_source is None
    assert t.scope_bullet_count_at_plan is None
    assert t.scope_bullet_count_at_execute is None
