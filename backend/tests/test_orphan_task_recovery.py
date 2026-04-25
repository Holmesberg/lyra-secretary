"""Tests for orphan task recovery job.

Validates that tasks stuck in EXECUTING with no open StopwatchSession
are transitioned to SKIPPED with initiation_status='orphaned_recovery'.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.db.models import StopwatchSession, Task, TaskState, User
from app.db.scoping import set_current_user_id
from app.utils.time_utils import now_utc
from app.workers.jobs.orphan_task_recovery import _run_for_one_user
from tests.conftest import TestingSession


USER_ID = 950


@pytest.fixture(autouse=True)
def _clean_env(db):
    set_current_user_id(None)
    wipe = TestingSession()
    try:
        wipe.execute(text("DELETE FROM stopwatch_session"))
        wipe.execute(text("DELETE FROM task"))
        wipe.execute(text("DELETE FROM \"user\""))
        wipe.commit()
    finally:
        wipe.close()
    db.rollback()
    db.expire_all()
    seed = TestingSession()
    try:
        seed.add(User(
            user_id=USER_ID, email="orphan-test@test",
            is_operator=False, notion_enabled=False,
            created_at=datetime.utcnow(),
        ))
        seed.commit()
    finally:
        seed.close()
    yield
    set_current_user_id(None)


def _seed_task(db, *, title="t", state=TaskState.PLANNED, start_offset_min=60) -> Task:
    start = now_utc() + timedelta(minutes=start_offset_min)
    end = start + timedelta(minutes=30)
    t = Task(
        title=title,
        planned_start_utc=start,
        planned_end_utc=end,
        planned_duration_minutes=30,
        state=state,
        category="dev",
        user_id=USER_ID,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _seed_session(db, task, *, closed=False) -> StopwatchSession:
    import uuid
    s = StopwatchSession(
        session_id=str(uuid.uuid4()),
        task_id=task.task_id,
        user_id=USER_ID,
        start_time_utc=now_utc(),
        end_time_utc=now_utc() if closed else None,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def test_orphan_executing_no_session_transitions_to_skipped(db):
    """EXECUTING task with no open session → SKIPPED."""
    task = _seed_task(db, title="orphan", state=TaskState.EXECUTING)
    user = db.query(User).filter(User.user_id == USER_ID).first()
    set_current_user_id(USER_ID)
    _run_for_one_user(db, user)
    db.refresh(task)
    assert task.state == TaskState.SKIPPED
    assert task.initiation_status == "orphaned_recovery"


def test_executing_with_open_session_not_touched(db):
    """EXECUTING task WITH an open session is left alone (active timer)."""
    task = _seed_task(db, title="active", state=TaskState.EXECUTING)
    _seed_session(db, task, closed=False)
    user = db.query(User).filter(User.user_id == USER_ID).first()
    set_current_user_id(USER_ID)
    _run_for_one_user(db, user)
    db.refresh(task)
    assert task.state == TaskState.EXECUTING


def test_executing_with_closed_session_only_transitions(db):
    """EXECUTING task with only CLOSED sessions (no open) → SKIPPED."""
    task = _seed_task(db, title="closed-session-orphan", state=TaskState.EXECUTING)
    _seed_session(db, task, closed=True)
    user = db.query(User).filter(User.user_id == USER_ID).first()
    set_current_user_id(USER_ID)
    _run_for_one_user(db, user)
    db.refresh(task)
    assert task.state == TaskState.SKIPPED
    assert task.initiation_status == "orphaned_recovery"


def test_voided_executing_task_not_touched(db):
    """Voided EXECUTING task is skipped by the sweep."""
    task = _seed_task(db, title="voided", state=TaskState.EXECUTING)
    task.voided_at = now_utc()
    db.commit()
    user = db.query(User).filter(User.user_id == USER_ID).first()
    set_current_user_id(USER_ID)
    _run_for_one_user(db, user)
    db.refresh(task)
    assert task.state == TaskState.EXECUTING


def test_planned_task_not_touched(db):
    """PLANNED tasks are left alone (not in ABANDONED_STATES)."""
    task = _seed_task(db, title="planned", state=TaskState.PLANNED)
    user = db.query(User).filter(User.user_id == USER_ID).first()
    set_current_user_id(USER_ID)
    _run_for_one_user(db, user)
    db.refresh(task)
    assert task.state == TaskState.PLANNED


# ---------------------------------------------------------------------------
# Apr 25 2026: PAUSED-with-no-open-session ghost-paused recovery
# ---------------------------------------------------------------------------


def test_orphan_paused_no_session_transitions_to_skipped(db):
    """Bug 1 (LYR-NNN): PAUSED task with no open session → SKIPPED.

    Reproduces the u5 Altium / u6 Compilers Lecs class: stale_session_recovery
    auto-closed the session at 12h+ but Task.state was never transitioned.
    The orphan_task_recovery extension catches it.
    """
    task = _seed_task(db, title="ghost-paused", state=TaskState.PAUSED)
    user = db.query(User).filter(User.user_id == USER_ID).first()
    set_current_user_id(USER_ID)
    _run_for_one_user(db, user)
    db.refresh(task)
    assert task.state == TaskState.SKIPPED
    assert task.initiation_status == "orphaned_recovery"


def test_paused_with_open_session_not_touched(db):
    """A PAUSED task that still has an open session (interruption parent) is left alone."""
    task = _seed_task(db, title="paused-parent", state=TaskState.PAUSED)
    _seed_session(db, task, closed=False)
    user = db.query(User).filter(User.user_id == USER_ID).first()
    set_current_user_id(USER_ID)
    _run_for_one_user(db, user)
    db.refresh(task)
    assert task.state == TaskState.PAUSED


def test_paused_with_only_closed_sessions_recovered(db):
    """PAUSED task whose only sessions are closed (auto_closed=True) → SKIPPED."""
    task = _seed_task(db, title="paused-closed-only", state=TaskState.PAUSED)
    _seed_session(db, task, closed=True)
    user = db.query(User).filter(User.user_id == USER_ID).first()
    set_current_user_id(USER_ID)
    _run_for_one_user(db, user)
    db.refresh(task)
    assert task.state == TaskState.SKIPPED
    assert task.initiation_status == "orphaned_recovery"


def test_voided_paused_task_not_touched(db):
    """Voided PAUSED task is filtered out by voided_at IS NULL check."""
    task = _seed_task(db, title="voided-paused", state=TaskState.PAUSED)
    task.voided_at = now_utc()
    db.commit()
    user = db.query(User).filter(User.user_id == USER_ID).first()
    set_current_user_id(USER_ID)
    _run_for_one_user(db, user)
    db.refresh(task)
    assert task.state == TaskState.PAUSED  # unchanged — voided guard wins
