"""Schema tests for PauseEvent, PausePredictionLog, and data_quality_flag.

Migration 020 introduces two new tables and one retrofit column. These tests
pin the model contract that the services/pause_predictor.py layer will depend
on, particularly:
  - pause_reason and pause_initiator are NOT NULL on pause_event (silent
    defaults at stopwatch_manager.py:330-331 were removed in the same commit)
  - resumed_at_utc and duration_minutes are NULL while pause is ongoing
  - pause_prediction_log.user_response is NULL at fire time (reconciliation
    fills it later — no silent default)
  - snooze chains via self-referential parent_firing_id
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models import (
    PauseEvent,
    PausePredictionLog,
    StopwatchSession,
    Task,
    TaskState,
)


def _make_session(db, user_id=1, task_state=TaskState.EXECUTING):
    task = Task(
        task_id=str(uuid4()),
        user_id=user_id,
        title="test task",
        category="dev",
        state=task_state,
        planned_start_utc=datetime.now(timezone.utc),
        planned_end_utc=datetime.now(timezone.utc) + timedelta(minutes=30),
        planned_duration_minutes=30,
        source="manual",
    )
    session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=user_id,
        start_time_utc=datetime.now(timezone.utc),
        total_paused_minutes=0.0,
    )
    db.add(task)
    db.add(session)
    db.commit()
    return task, session


# ---------- PauseEvent ----------

def test_pause_event_open_and_close(db):
    _, session = _make_session(db)
    now = datetime.now(timezone.utc)

    event = PauseEvent(
        session_id=session.session_id,
        user_id=session.user_id,
        paused_at_utc=now,
        pause_reason="mental_fatigue",
        pause_initiator="self",
    )
    db.add(event)
    db.commit()

    fetched = db.query(PauseEvent).filter_by(pause_event_id=event.pause_event_id).one()
    assert fetched.resumed_at_utc is None
    assert fetched.duration_minutes is None
    assert fetched.pause_reason == "mental_fatigue"
    assert fetched.pause_initiator == "self"

    # Close on resume
    fetched.resumed_at_utc = now + timedelta(minutes=3)
    fetched.duration_minutes = 3.0
    db.commit()

    reread = db.query(PauseEvent).filter_by(pause_event_id=event.pause_event_id).one()
    assert reread.duration_minutes == pytest.approx(3.0)


def test_pause_event_reason_is_not_nullable(db):
    _, session = _make_session(db)
    event = PauseEvent(
        session_id=session.session_id,
        user_id=session.user_id,
        paused_at_utc=datetime.now(timezone.utc),
        pause_reason=None,  # explicit NULL — must fail
        pause_initiator="self",
    )
    db.add(event)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_pause_event_initiator_is_not_nullable(db):
    _, session = _make_session(db)
    event = PauseEvent(
        session_id=session.session_id,
        user_id=session.user_id,
        paused_at_utc=datetime.now(timezone.utc),
        pause_reason="mental_fatigue",
        pause_initiator=None,  # explicit NULL — must fail
    )
    db.add(event)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_pause_event_cascades_on_session_delete():
    """The FK to stopwatch_session declares ondelete=CASCADE.

    We verify the declaration (migration contract) rather than runtime behavior
    because SQLite only enforces FKs when PRAGMA foreign_keys=ON, which the test
    harness does not set. Production (SQLite via alembic + PRAGMA on) and Postgres
    both honor the CASCADE.
    """
    fk = next(
        fk for fk in PauseEvent.__table__.foreign_keys
        if fk.column.table.name == "stopwatch_session"
    )
    assert fk.ondelete == "CASCADE"


# ---------- PausePredictionLog ----------

def test_prediction_log_fires_with_response_null(db):
    """At fire time, user_response + response_at are NULL (no silent default)."""
    fired = datetime.now(timezone.utc)
    log = PausePredictionLog(
        user_id=1,
        fired_at=fired,
        predicted_at=fired + timedelta(minutes=3),
        mechanism="clock_anchor",
        confidence=0.7,
        lead_minutes=3,
        sample_size=8,
        active_task_id=None,
    )
    db.add(log)
    db.commit()

    reread = db.query(PausePredictionLog).filter_by(firing_id=log.firing_id).one()
    assert reread.user_response is None
    assert reread.response_at is None
    assert reread.parent_firing_id is None


def test_prediction_log_reconciliation_fills_response(db):
    fired = datetime.now(timezone.utc)
    log = PausePredictionLog(
        user_id=1,
        fired_at=fired,
        predicted_at=fired + timedelta(minutes=3),
        mechanism="work_rhythm",
        confidence=0.55,
        lead_minutes=3,
        sample_size=6,
    )
    db.add(log)
    db.commit()

    # Reconciliation job fills these later
    log.user_response = "pause_now"
    log.response_at = fired + timedelta(minutes=4, seconds=30)
    db.commit()

    reread = db.query(PausePredictionLog).filter_by(firing_id=log.firing_id).one()
    assert reread.user_response == "pause_now"
    assert reread.response_at is not None


def test_prediction_log_snooze_chain(db):
    """Re-fire after snooze links to parent via parent_firing_id."""
    t0 = datetime.now(timezone.utc)
    parent = PausePredictionLog(
        user_id=1,
        fired_at=t0,
        predicted_at=t0 + timedelta(minutes=3),
        mechanism="clock_anchor",
        confidence=0.6,
        lead_minutes=3,
        sample_size=5,
    )
    db.add(parent)
    db.commit()
    parent.user_response = "snooze"
    parent.response_at = t0 + timedelta(seconds=20)
    db.commit()

    child = PausePredictionLog(
        user_id=1,
        fired_at=t0 + timedelta(minutes=5),
        predicted_at=t0 + timedelta(minutes=8),
        mechanism="clock_anchor",
        confidence=0.6,
        lead_minutes=3,
        sample_size=5,
        parent_firing_id=parent.firing_id,
    )
    db.add(child)
    db.commit()

    assert child.parent_firing_id == parent.firing_id
    # Acceptance-rate denominator excludes rows where parent_firing_id IS NOT NULL
    # (MANIFESTO.md §VT-17 formula). Verify we can express that query.
    denominator_rows = (
        db.query(PausePredictionLog)
        .filter(PausePredictionLog.parent_firing_id.is_(None))
        .all()
    )
    assert parent in denominator_rows
    assert child not in denominator_rows


# ---------- data_quality_flag retrofit column ----------

def test_data_quality_flag_defaults_null(db):
    _, session = _make_session(db)
    # Model default — brand new rows are clean
    assert session.data_quality_flag is None


def test_data_quality_flag_accepts_retrofit_values(db):
    _, session = _make_session(db)
    session.data_quality_flag = "possibly_default_pause_metadata"
    db.commit()

    reread = db.query(StopwatchSession).filter_by(session_id=session.session_id).one()
    assert reread.data_quality_flag == "possibly_default_pause_metadata"

    # The second (more severe) flag can override the first
    reread.data_quality_flag = "pause_reason_lost_to_overwrite"
    db.commit()
    reread2 = db.query(StopwatchSession).filter_by(session_id=session.session_id).one()
    assert reread2.data_quality_flag == "pause_reason_lost_to_overwrite"


def test_data_quality_flag_excluded_by_analytics_filter(db):
    """The loader pattern `WHERE data_quality_flag IS NULL` must exclude flagged rows."""
    _, clean = _make_session(db, user_id=1)
    _, flagged = _make_session(db, user_id=1)
    flagged.data_quality_flag = "possibly_default_pause_metadata"
    db.commit()

    clean_rows = (
        db.query(StopwatchSession)
        .filter(StopwatchSession.data_quality_flag.is_(None))
        .all()
    )
    assert clean in clean_rows
    assert flagged not in clean_rows
