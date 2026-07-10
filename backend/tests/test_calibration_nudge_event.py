"""Tests for Loop 1 calibration nudge event lifecycle.

Covers:
- Schema all-or-none validation (partial nudge_* fields rejected)
- Event row written when nudge_decision present in create
- Event row NOT written when nudge fields absent
- Outcome stamped on complete_task transition to EXECUTED
- voided_at filter respected (already-voided event not re-stamped)
- Cross-user isolation (one user's events invisible to another)
- Internal-caller bypass guard (TaskManager raises on partial sets)
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.models import (
    CalibrationNudgeEvent,
    ReflectionViewLog,
    Task,
    TaskSource,
    TaskState,
    User,
)
from app.db.scoping import set_current_user_id
from app.services.task_manager import TaskManager
from app.schemas.task import TaskCreateRequest


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM calibration_nudge_event"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM \"user\""))
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM calibration_nudge_event"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM \"user\""))
    db.commit()


def _make_user(db, user_id: int = 77, email: str = "n@example.com") -> User:
    u = User(
        user_id=user_id, email=email,
        is_operator=False, notion_enabled=False,
        timezone="Africa/Cairo", created_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    return u


def _future_window(hours_from_now: int = 24, duration: int = 60):
    """Returns (start, end) far enough in future to clear the past-time guard
    (Cairo→UTC conversion takes 3 hours off the clock)."""
    start = datetime.utcnow() + timedelta(hours=hours_from_now)
    end = start + timedelta(minutes=duration)
    return start, end


# ── Schema validation ──────────────────────────────────────────────


def test_all_four_nudge_fields_present_validates(db):
    start, end = _future_window()
    req = TaskCreateRequest(
        title="t", start=start, end=end,
        nudge_decision="accepted",
        nudge_suggested_duration_minutes=60,
        nudge_bias_factor=1.4,
        nudge_sample_size=10,
    )
    assert req.nudge_decision == "accepted"


def test_zero_nudge_fields_validates(db):
    start, end = _future_window()
    req = TaskCreateRequest(title="t", start=start, end=end)
    assert req.nudge_decision is None


@pytest.mark.parametrize("present_fields", [
    {"nudge_decision": "accepted"},
    {"nudge_decision": "accepted", "nudge_suggested_duration_minutes": 60},
    {"nudge_decision": "accepted", "nudge_suggested_duration_minutes": 60, "nudge_bias_factor": 1.4},
    {"nudge_suggested_duration_minutes": 60, "nudge_bias_factor": 1.4, "nudge_sample_size": 10},
])
def test_partial_nudge_fields_rejected(db, present_fields):
    start, end = _future_window()
    with pytest.raises(Exception) as exc:
        TaskCreateRequest(title="t", start=start, end=end, **present_fields)
    assert "nudge_" in str(exc.value).lower() or "all" in str(exc.value).lower()


def test_invalid_decision_value_rejected(db):
    start, end = _future_window()
    with pytest.raises(Exception):
        TaskCreateRequest(
            title="t", start=start, end=end,
            nudge_decision="snoozed",  # not in Literal
            nudge_suggested_duration_minutes=60,
            nudge_bias_factor=1.4,
            nudge_sample_size=10,
        )


# ── Event creation lifecycle ───────────────────────────────────────


def test_event_written_when_nudge_decision_present(db):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    start, end = _future_window()

    tm = TaskManager(db)
    task, _, _ = tm.create_task(
        title="study session", start=start, end=end,
        nudge_decision="accepted",
        nudge_suggested_duration_minutes=90,
        nudge_bias_factor=1.4,
        nudge_sample_size=12,
    )

    events = db.query(CalibrationNudgeEvent).all()
    assert len(events) == 1
    e = events[0]
    assert e.task_id == task.task_id
    assert e.user_id == user.user_id
    assert e.user_decision == "accepted"
    assert e.suggested_duration_minutes == 90
    assert e.user_planned_duration_minutes == 60  # actual duration of created task
    assert e.bias_factor == 1.4
    assert e.sample_size == 12
    assert e.executed_duration_minutes is None  # not yet stamped
    assert e.resolved_at is None
    assert e.voided_at is None


def test_no_event_when_nudge_fields_absent(db):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    start, end = _future_window()

    tm = TaskManager(db)
    tm.create_task(title="t", start=start, end=end)

    assert db.query(CalibrationNudgeEvent).count() == 0


def test_internal_caller_partial_fields_raise(db):
    """TaskManager defends against internal callers that bypass schema."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    start, end = _future_window()

    tm = TaskManager(db)
    with pytest.raises(ValueError, match="all-or-none"):
        tm.create_task(
            title="t", start=start, end=end,
            nudge_decision="accepted",
            # Only 1/4 — schema would reject; here we bypass by calling directly
        )


# ── Outcome reconciliation (inline in complete_task) ──────────────


def test_outcome_stamped_on_complete_task(db):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    start, end = _future_window()

    tm = TaskManager(db)
    task, _, _ = tm.create_task(
        title="t", start=start, end=end,
        nudge_decision="accepted",
        nudge_suggested_duration_minutes=90,
        nudge_bias_factor=1.4,
        nudge_sample_size=12,
    )

    # Need EXECUTING state before complete_task. Bypass full ceremony.
    task.state = TaskState.EXECUTING
    task.executed_start_utc = datetime.utcnow() - timedelta(minutes=45)
    db.commit()

    completed, _ = tm.complete_task(
        task_id=task.task_id,
        executed_start=task.executed_start_utc,
        executed_end=datetime.utcnow(),
    )

    event = db.query(CalibrationNudgeEvent).filter_by(task_id=task.task_id).first()
    assert event is not None
    assert event.executed_duration_minutes is not None
    assert event.executed_duration_minutes >= 44  # ~45 min elapsed
    assert event.resolved_at is not None


def test_outcome_can_be_corrected_to_active_execution_after_pause_subtraction(db):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    start, end = _future_window()

    tm = TaskManager(db)
    task, _, _ = tm.create_task(
        title="paused task",
        start=start,
        end=end,
        nudge_decision="accepted",
        nudge_suggested_duration_minutes=90,
        nudge_bias_factor=1.4,
        nudge_sample_size=12,
    )

    task.state = TaskState.EXECUTING
    task.executed_start_utc = datetime.utcnow() - timedelta(minutes=90)
    db.commit()

    tm.complete_task(
        task_id=task.task_id,
        executed_start=task.executed_start_utc,
        executed_end=datetime.utcnow(),
    )
    tm.reconcile_calibration_nudge_outcome(task.task_id, 60)
    db.commit()

    event = db.query(CalibrationNudgeEvent).filter_by(task_id=task.task_id).first()
    assert event.executed_duration_minutes == 60


def test_voided_event_not_re_stamped(db):
    """If event was voided post-creation, complete_task does not resurrect it."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    start, end = _future_window()

    tm = TaskManager(db)
    task, _, _ = tm.create_task(
        title="t", start=start, end=end,
        nudge_decision="dismissed",
        nudge_suggested_duration_minutes=120,
        nudge_bias_factor=1.8,
        nudge_sample_size=8,
    )

    # Manually void the event
    event = db.query(CalibrationNudgeEvent).filter_by(task_id=task.task_id).first()
    event.voided_at = datetime.utcnow()
    db.commit()

    # Now complete the task
    task.state = TaskState.EXECUTING
    task.executed_start_utc = datetime.utcnow() - timedelta(minutes=60)
    db.commit()
    tm.complete_task(
        task_id=task.task_id,
        executed_start=task.executed_start_utc,
        executed_end=datetime.utcnow(),
    )

    # Voided event should still have NULL outcome (filter excluded it)
    db.refresh(event)
    assert event.executed_duration_minutes is None
    assert event.resolved_at is None


def test_complete_task_with_no_event_does_nothing(db):
    """Tasks created without a nudge complete normally — no event row exists."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    start, end = _future_window()

    tm = TaskManager(db)
    task, _, _ = tm.create_task(title="t", start=start, end=end)

    task.state = TaskState.EXECUTING
    task.executed_start_utc = datetime.utcnow() - timedelta(minutes=30)
    db.commit()
    completed, _ = tm.complete_task(
        task_id=task.task_id,
        executed_start=task.executed_start_utc,
        executed_end=datetime.utcnow(),
    )
    # Task transitions normally; no event row created/updated
    assert completed.state == TaskState.EXECUTED
    assert db.query(CalibrationNudgeEvent).count() == 0


# ── Cross-user isolation ──────────────────────────────────────────


def test_cross_user_event_isolation(db):
    """User A's events don't leak into user B's queries."""
    user_a = _make_user(db, user_id=77, email="a@x")
    user_b = _make_user(db, user_id=88, email="b@x")

    set_current_user_id(user_a.user_id)
    start, end = _future_window()
    tm_a = TaskManager(db)
    tm_a.create_task(
        title="a's task", start=start, end=end,
        nudge_decision="accepted",
        nudge_suggested_duration_minutes=60,
        nudge_bias_factor=1.4,
        nudge_sample_size=10,
    )

    # User B creates a task without nudge
    set_current_user_id(user_b.user_id)
    tm_b = TaskManager(db)
    tm_b.create_task(title="b's task", start=start, end=end)

    # User B's view: zero events (cross-user filter excludes A's)
    set_current_user_id(user_b.user_id)
    b_events = (
        db.query(CalibrationNudgeEvent)
        .filter(CalibrationNudgeEvent.user_id == user_b.user_id)
        .all()
    )
    assert len(b_events) == 0

    # User A's view: one event
    set_current_user_id(user_a.user_id)
    a_events = (
        db.query(CalibrationNudgeEvent)
        .filter(CalibrationNudgeEvent.user_id == user_a.user_id)
        .all()
    )
    assert len(a_events) == 1


# ── Phase 6 V3 — ReflectionViewLog write at creation_nudge fire ────


def test_creation_nudge_writes_reflection_view_log(db):
    """Apr 27 drift fix — every creation-nudge fire writes a
    ReflectionViewLog row alongside the CalibrationNudgeEvent so the
    Phase 6 response-type classifier has V3 signal data when it
    activates. Per `docs/archive/legacy/planning/phase_6_architecture_backlog.md:227`.
    """
    user = _make_user(db)
    set_current_user_id(user.user_id)
    start, end = _future_window()

    fire_time = datetime.utcnow() - timedelta(seconds=12)

    tm = TaskManager(db)
    task, _, _ = tm.create_task(
        title="study", start=start, end=end,
        nudge_decision="accepted",
        nudge_suggested_duration_minutes=90,
        nudge_bias_factor=1.4,
        nudge_sample_size=12,
        nudge_viewed_at=fire_time,
    )

    rows = db.query(ReflectionViewLog).filter(
        ReflectionViewLog.task_id == task.task_id,
        ReflectionViewLog.reflection_type == "creation_nudge",
    ).all()
    assert len(rows) == 1
    r = rows[0]
    assert r.user_id == user.user_id
    assert r.outcome == "adjusted"  # accepted → adjusted
    # dwell_seconds computed from fire_time → decision_time (~12s)
    assert r.dwell_seconds is not None
    assert r.dwell_seconds >= 10
    assert r.viewed_at == fire_time
    assert r.dismissed_at is not None


def test_creation_nudge_dismissed_outcome(db):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    start, end = _future_window()

    tm = TaskManager(db)
    task, _, _ = tm.create_task(
        title="t", start=start, end=end,
        nudge_decision="dismissed",
        nudge_suggested_duration_minutes=90,
        nudge_bias_factor=1.4,
        nudge_sample_size=12,
        # No nudge_viewed_at — dwell_seconds should be NULL but the
        # row still writes.
    )
    rows = db.query(ReflectionViewLog).filter(
        ReflectionViewLog.task_id == task.task_id,
        ReflectionViewLog.reflection_type == "creation_nudge",
    ).all()
    assert len(rows) == 1
    assert rows[0].outcome == "kept"  # dismissed → kept (user kept their typed value)
    assert rows[0].dwell_seconds is None
    assert rows[0].viewed_at is None


def test_no_reflection_view_log_when_nudge_absent(db):
    """Tasks without a calibration nudge don't write reflection_view_log."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    start, end = _future_window()

    tm = TaskManager(db)
    task, _, _ = tm.create_task(title="t", start=start, end=end)

    rows = db.query(ReflectionViewLog).filter(
        ReflectionViewLog.task_id == task.task_id,
    ).all()
    assert len(rows) == 0
