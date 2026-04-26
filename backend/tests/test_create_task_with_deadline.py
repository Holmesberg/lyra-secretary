"""Integration tests — TaskManager.create_task with explicit deadline binding.

Loop 11 Pass 1: when `deadline_id` is supplied to create_task, TaskManager
calls _validate_bindable_deadline → binds the task → auto-transitions
the deadline state from 'planned' to 'active' (idempotent if already active).

Coverage:
- Happy path: planned → active auto-transition on first bind
- Happy path: already-active stays active (idempotent)
- Wrong-user rejection (cross-tenant safety)
- Voided-deadline rejection
- Terminal-state rejection (completed | missed | skipped)
- Non-existent deadline rejection
- scope_bullet_count_at_plan populated regardless of deadline
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import Deadline, Task, TaskState, User
from app.db.scoping import set_current_user_id
from app.services.task_manager import TaskManager


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
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


def _make_deadline(db, user_id: int, state: str = "planned",
                   voided: bool = False) -> Deadline:
    d = Deadline(
        deadline_id=str(uuid4()),
        user_id=user_id,
        title="Test deadline",
        due_at_utc=datetime.utcnow() + timedelta(days=7),
        state=state,
        voided_at=datetime.utcnow() if voided else None,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def _create_task_args(deadline_id=None, description=None):
    """Standard create_task args with start far enough in future to clear
    the past-time check.

    Note: TaskManager.create_task treats naive datetimes as Cairo local
    (UTC+3), then converts to UTC. A naive `utcnow() + 2h` would land 1h
    in the past after conversion. We use +24h to comfortably clear the
    past-time guard regardless of TZ offset.
    """
    start = datetime.utcnow() + timedelta(hours=24)
    end = start + timedelta(hours=1)
    return dict(
        title="Test task",
        start=start,
        end=end,
        description=description,
        deadline_id=deadline_id,
    )


def test_bind_to_planned_deadline_auto_transitions_to_active(db):
    """Happy path: planned deadline auto-promotes to active on first bind."""
    user = _make_user(db, "test1@example.com")
    set_current_user_id(user.user_id)

    deadline = _make_deadline(db, user.user_id, state="planned")
    assert deadline.state == "planned"

    tm = TaskManager(db)
    task, conflicts, _ = tm.create_task(
        **_create_task_args(deadline_id=deadline.deadline_id)
    )

    assert task is not None
    assert task.deadline_id == deadline.deadline_id
    assert task.deadline_match_source == "user_explicit"
    assert task.deadline_match_confidence == 1.0

    db.refresh(deadline)
    assert deadline.state == "active"  # auto-transitioned


def test_bind_to_active_deadline_is_idempotent(db):
    """Already-active deadline stays active (no-op state-change)."""
    user = _make_user(db, "test2@example.com")
    set_current_user_id(user.user_id)

    deadline = _make_deadline(db, user.user_id, state="active")

    tm = TaskManager(db)
    task, _, _ = tm.create_task(
        **_create_task_args(deadline_id=deadline.deadline_id)
    )

    assert task is not None
    assert task.deadline_id == deadline.deadline_id

    db.refresh(deadline)
    assert deadline.state == "active"  # unchanged


def test_wrong_user_rejection(db):
    """Cross-tenant binding attempt fails with deadline_not_found."""
    user_a = _make_user(db, "alice@example.com")
    user_b = _make_user(db, "bob@example.com")

    # Deadline owned by user A
    deadline = _make_deadline(db, user_a.user_id, state="active")

    # Acting as user B
    set_current_user_id(user_b.user_id)
    tm = TaskManager(db)

    with pytest.raises(ValueError, match="deadline_not_found"):
        tm.create_task(**_create_task_args(deadline_id=deadline.deadline_id))


def test_voided_deadline_rejection(db):
    """Voided deadline rejects new bindings."""
    user = _make_user(db, "test3@example.com")
    set_current_user_id(user.user_id)

    deadline = _make_deadline(db, user.user_id, state="active", voided=True)

    tm = TaskManager(db)
    with pytest.raises(ValueError, match="deadline_voided"):
        tm.create_task(**_create_task_args(deadline_id=deadline.deadline_id))


@pytest.mark.parametrize("terminal_state", ["completed", "missed", "skipped"])
def test_terminal_state_rejection(db, terminal_state):
    """Terminal-state deadlines reject new bindings."""
    user = _make_user(db, f"test_{terminal_state}@example.com")
    set_current_user_id(user.user_id)

    deadline = _make_deadline(db, user.user_id, state=terminal_state)

    tm = TaskManager(db)
    with pytest.raises(ValueError, match="deadline_terminal_state"):
        tm.create_task(**_create_task_args(deadline_id=deadline.deadline_id))


def test_nonexistent_deadline_rejection(db):
    """Random UUID that doesn't exist → deadline_not_found."""
    user = _make_user(db, "test4@example.com")
    set_current_user_id(user.user_id)

    tm = TaskManager(db)
    with pytest.raises(ValueError, match="deadline_not_found"):
        tm.create_task(**_create_task_args(deadline_id=str(uuid4())))


def test_scope_bullet_count_populated_with_deadline(db):
    """scope_bullet_count_at_plan is computed alongside deadline binding."""
    user = _make_user(db, "test5@example.com")
    set_current_user_id(user.user_id)

    deadline = _make_deadline(db, user.user_id, state="planned")

    tm = TaskManager(db)
    task, _, _ = tm.create_task(
        **_create_task_args(
            deadline_id=deadline.deadline_id,
            description="- step 1\n- step 2\n- step 3",
        )
    )
    assert task is not None
    assert task.scope_bullet_count_at_plan == 3
    assert task.deadline_id == deadline.deadline_id


def test_scope_bullet_count_populated_without_deadline(db):
    """scope_bullet_count_at_plan works for plain tasks (no deadline)."""
    user = _make_user(db, "test6@example.com")
    set_current_user_id(user.user_id)

    tm = TaskManager(db)
    task, _, _ = tm.create_task(
        **_create_task_args(description="- one\n* two\n• three")
    )
    assert task is not None
    assert task.scope_bullet_count_at_plan == 3
    assert task.deadline_id is None
    assert task.deadline_match_source is None


def test_no_deadline_no_description_yields_none(db):
    """Plain task with no description has scope_bullet_count_at_plan=None."""
    user = _make_user(db, "test7@example.com")
    set_current_user_id(user.user_id)

    tm = TaskManager(db)
    task, _, _ = tm.create_task(**_create_task_args())
    assert task is not None
    assert task.scope_bullet_count_at_plan is None
    assert task.deadline_id is None


def test_complete_task_resamples_scope_bullets(db):
    """complete_task writes scope_bullet_count_at_execute from current description."""
    user = _make_user(db, "test8@example.com")
    set_current_user_id(user.user_id)

    tm = TaskManager(db)
    task, _, _ = tm.create_task(
        **_create_task_args(description="- only one bullet")
    )
    assert task is not None
    assert task.scope_bullet_count_at_plan == 1

    # Simulate a description edit before execute (scope drift)
    task.description = "- one\n- two\n- three\n- four"
    db.commit()

    # Need EXECUTING state before complete_task. Bypass full state-machine
    # ceremony by transitioning manually for this test.
    task.state = TaskState.EXECUTING
    task.executed_start_utc = datetime.utcnow() - timedelta(minutes=30)
    db.commit()

    completed, _ = tm.complete_task(
        task_id=task.task_id,
        executed_start=task.executed_start_utc,
        executed_end=datetime.utcnow(),
    )
    assert completed.scope_bullet_count_at_plan == 1  # frozen
    assert completed.scope_bullet_count_at_execute == 4  # re-sampled
