"""Phase H — reconcile_deadline_outcomes job tests.

Calls _run_for_one_user(db, user) directly (no API client). Verifies:
- Writes outcome row for EXECUTED deadline-bound tasks
- deadline_met true if executed_end_utc <= due_at_utc
- delay_minutes signed (positive=overran, negative=met early)
- Skips voided tasks
- Skips voided deadlines
- Skips tasks without deadline_id
- Skips PLANNED/EXECUTING tasks (only EXECUTED)
- Idempotent: re-running doesn't create duplicate rows (PK constraint)
- Per-user scoping: doesn't leak across users
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import (
    Deadline,
    DeadlineCompletionEvent,
    Task,
    TaskDeadlineOutcome,
    TaskSource,
    TaskState,
    User,
)
from app.workers.jobs.reconcile_deadline_outcomes import _run_for_one_user


@pytest.fixture(autouse=True)
def _clean_slate(db):
    db.rollback()
    db.query(TaskDeadlineOutcome).delete()
    db.query(DeadlineCompletionEvent).delete()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    db.rollback()
    db.query(TaskDeadlineOutcome).delete()
    db.query(DeadlineCompletionEvent).delete()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()


def _make_user(db, email: str) -> User:
    u = User(
        email=email,
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


def _make_deadline(db, user_id: int, due_at: datetime, **overrides) -> Deadline:
    d = Deadline(
        deadline_id=str(uuid4()),
        user_id=user_id,
        title=overrides.get("title", "Test deadline"),
        due_at_utc=due_at,
        state=overrides.get("state", "active"),
        voided_at=overrides.get("voided_at"),
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def _make_task(db, user_id: int, deadline_id=None, **overrides) -> Task:
    base = datetime(2026, 5, 1, 9, 0, 0)
    t = Task(
        task_id=str(uuid4()),
        title=overrides.get("title", "Task"),
        planned_start_utc=base,
        planned_end_utc=base + timedelta(hours=1),
        planned_duration_minutes=60,
        executed_start_utc=overrides.get("executed_start_utc", base),
        executed_end_utc=overrides.get("executed_end_utc", base + timedelta(hours=1)),
        executed_duration_minutes=overrides.get("executed_duration_minutes", 60),
        state=overrides.get("state", TaskState.EXECUTED),
        source=TaskSource.MANUAL,
        user_id=user_id,
        deadline_id=deadline_id,
        voided_at=overrides.get("voided_at"),
        initiation_status=overrides.get("initiation_status"),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def test_writes_outcome_for_executed_deadline_bound_task(db):
    user = _make_user(db, "h1@example.com")
    due = datetime(2026, 5, 1, 17, 0, 0)
    deadline = _make_deadline(db, user.user_id, due_at=due)
    task = _make_task(
        db, user.user_id,
        deadline_id=deadline.deadline_id,
        executed_end_utc=datetime(2026, 5, 1, 16, 30, 0),  # 30 min early
    )

    _run_for_one_user(db, user)

    outcome = db.query(TaskDeadlineOutcome).filter(
        TaskDeadlineOutcome.task_id == task.task_id
    ).first()
    assert outcome is not None
    assert outcome.deadline_met is True
    assert outcome.delay_minutes == -30  # 30 min early → negative


def test_writes_outcome_for_overrun(db):
    user = _make_user(db, "h2@example.com")
    due = datetime(2026, 5, 1, 17, 0, 0)
    deadline = _make_deadline(db, user.user_id, due_at=due)
    task = _make_task(
        db, user.user_id,
        deadline_id=deadline.deadline_id,
        executed_end_utc=datetime(2026, 5, 1, 18, 15, 0),  # 75 min late
    )

    _run_for_one_user(db, user)

    outcome = db.query(TaskDeadlineOutcome).filter(
        TaskDeadlineOutcome.task_id == task.task_id
    ).first()
    assert outcome is not None
    assert outcome.deadline_met is False
    assert outcome.delay_minutes == 75


def test_boundary_executed_at_deadline_counts_as_met(db):
    """delay_minutes == 0 → deadline_met=True (boundary semantics)."""
    user = _make_user(db, "h3@example.com")
    due = datetime(2026, 5, 1, 17, 0, 0)
    deadline = _make_deadline(db, user.user_id, due_at=due)
    task = _make_task(
        db, user.user_id,
        deadline_id=deadline.deadline_id,
        executed_end_utc=due,  # exactly at deadline
    )

    _run_for_one_user(db, user)

    outcome = db.query(TaskDeadlineOutcome).filter(
        TaskDeadlineOutcome.task_id == task.task_id
    ).first()
    assert outcome.deadline_met is True
    assert outcome.delay_minutes == 0


def test_skips_voided_tasks(db):
    user = _make_user(db, "h4@example.com")
    deadline = _make_deadline(db, user.user_id, due_at=datetime(2026, 5, 1, 17, 0, 0))
    _make_task(
        db, user.user_id,
        deadline_id=deadline.deadline_id,
        voided_at=datetime.utcnow(),
    )

    _run_for_one_user(db, user)
    assert db.query(TaskDeadlineOutcome).count() == 0


def test_skips_voided_deadlines(db):
    user = _make_user(db, "h5@example.com")
    deadline = _make_deadline(
        db, user.user_id,
        due_at=datetime(2026, 5, 1, 17, 0, 0),
        voided_at=datetime.utcnow(),
    )
    _make_task(db, user.user_id, deadline_id=deadline.deadline_id)

    _run_for_one_user(db, user)
    assert db.query(TaskDeadlineOutcome).count() == 0


def test_skips_unbound_tasks(db):
    user = _make_user(db, "h6@example.com")
    _make_task(db, user.user_id, deadline_id=None)

    _run_for_one_user(db, user)
    assert db.query(TaskDeadlineOutcome).count() == 0


def test_skips_retroactive_done_tasks(db):
    """Retroactive done fabricates planned timestamps; keep it out of TDO."""
    user = _make_user(db, "retroactive@example.com")
    deadline = _make_deadline(db, user.user_id, due_at=datetime(2026, 5, 1, 17, 0, 0))
    _make_task(
        db,
        user.user_id,
        deadline_id=deadline.deadline_id,
        initiation_status="retroactive",
    )

    _run_for_one_user(db, user)

    assert db.query(TaskDeadlineOutcome).count() == 0


@pytest.mark.parametrize("state", [
    TaskState.PLANNED, TaskState.EXECUTING, TaskState.PAUSED, TaskState.SKIPPED,
])
def test_skips_non_executed_tasks(db, state):
    user = _make_user(db, f"h7-{state.value}@example.com")
    deadline = _make_deadline(db, user.user_id, due_at=datetime(2026, 5, 1, 17, 0, 0))
    _make_task(
        db, user.user_id,
        deadline_id=deadline.deadline_id,
        state=state,
        executed_end_utc=None,  # non-EXECUTED tasks have no end
    )

    _run_for_one_user(db, user)
    assert db.query(TaskDeadlineOutcome).count() == 0


def test_idempotent_no_duplicate_rows(db):
    user = _make_user(db, "h8@example.com")
    deadline = _make_deadline(db, user.user_id, due_at=datetime(2026, 5, 1, 17, 0, 0))
    _make_task(db, user.user_id, deadline_id=deadline.deadline_id)

    _run_for_one_user(db, user)
    assert db.query(TaskDeadlineOutcome).count() == 1

    # Second run: still 1 (LEFT JOIN filter excludes already-reconciled rows)
    _run_for_one_user(db, user)
    assert db.query(TaskDeadlineOutcome).count() == 1


def test_per_user_scoping(db):
    user_a = _make_user(db, "ha@example.com")
    user_b = _make_user(db, "hb@example.com")
    deadline_b = _make_deadline(db, user_b.user_id, due_at=datetime(2026, 5, 1, 17, 0, 0))
    _make_task(db, user_b.user_id, deadline_id=deadline_b.deadline_id)

    # Run for user_a only — no rows should be written (B's deadline is invisible)
    _run_for_one_user(db, user_a)
    assert db.query(TaskDeadlineOutcome).count() == 0

    # Now run for user_b — exactly 1 row
    _run_for_one_user(db, user_b)
    assert db.query(TaskDeadlineOutcome).count() == 1
