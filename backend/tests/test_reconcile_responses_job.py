"""Pins the Commit 5a contract for the reconcile_responses scheduler job.

  * Rows whose predicted_at + ACCEPTANCE_WINDOW_MINUTES is still in the
    future are NOT touched (window still open).
  * Rows whose window has closed and have a matching PauseEvent in
    [fired_at, predicted_at + ACCEPTANCE_WINDOW_MINUTES] → 'pause_now',
    with response_at set to the matching pause's paused_at_utc.
  * Rows whose window has closed with no matching pause → 'no_response'.
  * Rows already reconciled (user_response IS NOT NULL) are left alone —
    the pre-registration forbids revisiting closed windows.
  * A pause_event for a different user does NOT count as acceptance for
    this user's firing.
"""
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.models import (
    PauseEvent,
    PausePredictionLog,
    StopwatchSession,
    Task,
    TaskState,
    User,
)
from app.db.scoping import set_current_user_id
from app.utils.time_utils import now_utc
from app.workers.jobs.reconcile_responses import (
    ACCEPTANCE_WINDOW_MINUTES,
    _run_for_one_user,
)

USER_ID = 920
OTHER_USER_ID = 921


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM pause_prediction_log"))
    db.execute(text("DELETE FROM pause_event"))
    db.execute(text("DELETE FROM stopwatch_session"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM user"))
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM pause_prediction_log"))
    db.execute(text("DELETE FROM pause_event"))
    db.execute(text("DELETE FROM stopwatch_session"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM user"))
    db.commit()


@pytest.fixture
def user(db):
    set_current_user_id(USER_ID)
    u = User(
        user_id=USER_ID,
        email="reconcile@test",
        is_operator=False,
        notion_enabled=False,
        created_at=now_utc(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _seed_prediction(
    db,
    *,
    user_id: int = USER_ID,
    fired_minutes_ago: int = 15,
    predicted_minutes_ago: int = 12,
    user_response=None,
    response_at=None,
    parent_firing_id=None,
) -> PausePredictionLog:
    now = now_utc()
    row = PausePredictionLog(
        user_id=user_id,
        fired_at=now - timedelta(minutes=fired_minutes_ago),
        predicted_at=now - timedelta(minutes=predicted_minutes_ago),
        mechanism="clock_anchor",
        confidence=0.65,
        lead_minutes=3,
        sample_size=6,
        user_response=user_response,
        response_at=response_at,
        parent_firing_id=parent_firing_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_pause_event(db, *, user_id: int = USER_ID, paused_minutes_ago: int = 10):
    """Seed a minimal (task, session, pause_event) triple for a given user."""
    now = now_utc()
    paused_at = now - timedelta(minutes=paused_minutes_ago)
    task = Task(
        task_id=str(uuid4()),
        user_id=user_id,
        title="reconcile-seed",
        category="dev",
        state=TaskState.EXECUTED,
        planned_start_utc=paused_at - timedelta(minutes=5),
        planned_end_utc=paused_at + timedelta(minutes=25),
        planned_duration_minutes=30,
        source="manual",
    )
    session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=user_id,
        start_time_utc=paused_at - timedelta(minutes=1),
        total_paused_minutes=0.0,
    )
    evt = PauseEvent(
        pause_event_id=str(uuid4()),
        session_id=session.session_id,
        user_id=user_id,
        paused_at_utc=paused_at,
        pause_reason="distraction",
        pause_initiator="self",
    )
    db.add_all([task, session, evt])
    db.commit()
    return evt


def test_window_still_open_row_untouched(db, user):
    """predicted_at + window > now → row remains NULL, job does not reconcile."""
    # Predicted 2 min ago; acceptance_window is 5 → window closes in 3 min
    row = _seed_prediction(db, fired_minutes_ago=5, predicted_minutes_ago=2)

    _run_for_one_user(db, user)

    db.refresh(row)
    assert row.user_response is None
    assert row.response_at is None


def test_closed_window_with_matching_pause_marks_accepted(db, user):
    """A pause_event inside [fired_at, predicted_at+window] → 'pause_now'."""
    row = _seed_prediction(db, fired_minutes_ago=15, predicted_minutes_ago=12)
    evt = _seed_pause_event(db, paused_minutes_ago=10)

    _run_for_one_user(db, user)

    db.refresh(row)
    assert row.user_response == "pause_now"
    assert row.response_at == evt.paused_at_utc


def test_closed_window_without_pause_marks_no_response(db, user):
    """No matching pause_event → 'no_response' with response_at set to now."""
    row = _seed_prediction(db, fired_minutes_ago=15, predicted_minutes_ago=12)

    _run_for_one_user(db, user)

    db.refresh(row)
    assert row.user_response == "no_response"
    assert row.response_at is not None


def test_closed_row_is_not_touched(db, user):
    """A row with user_response already set must not be revisited."""
    now = now_utc()
    row = _seed_prediction(
        db,
        fired_minutes_ago=60,
        predicted_minutes_ago=57,
        user_response="dismiss",
        response_at=now - timedelta(minutes=55),
    )
    # Even if a matching pause exists in the old window, the row stays 'dismiss'.
    _seed_pause_event(db, paused_minutes_ago=56)

    _run_for_one_user(db, user)

    db.refresh(row)
    assert row.user_response == "dismiss"


def test_other_user_pause_does_not_count(db, user):
    """A pause by a different user must not mark THIS user's firing as accepted."""
    # Seed the other user so their pause_event insertion doesn't violate FK.
    other = User(
        user_id=OTHER_USER_ID,
        email="other@test",
        is_operator=False,
        notion_enabled=False,
        created_at=now_utc(),
    )
    db.add(other)
    db.commit()

    row = _seed_prediction(db, user_id=USER_ID, fired_minutes_ago=15, predicted_minutes_ago=12)
    _seed_pause_event(db, user_id=OTHER_USER_ID, paused_minutes_ago=10)

    _run_for_one_user(db, user)

    db.refresh(row)
    assert row.user_response == "no_response"


def test_pause_outside_window_does_not_count(db, user):
    """A pause after predicted_at + ACCEPTANCE_WINDOW_MINUTES is too late."""
    # Window: predicted_at is 20 min ago, window closed 15 min ago.
    row = _seed_prediction(db, fired_minutes_ago=23, predicted_minutes_ago=20)
    # Pause happened 10 min ago — 5 min after window closed.
    _seed_pause_event(db, paused_minutes_ago=10)

    _run_for_one_user(db, user)

    db.refresh(row)
    assert row.user_response == "no_response"
