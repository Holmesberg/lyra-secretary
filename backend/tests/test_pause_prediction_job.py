"""Pins the Commit 5a contract for the pause_prediction scheduler job.

  * When PausePredictor returns a PausePrediction, the job writes exactly
    one pause_prediction_log row with all fields mapped from the dataclass
    and enqueues one notification via /v1/notifications/push.
  * When the predictor returns None, no row and no notification.
  * FIRING_COOLDOWN_MINUTES: if a row already exists within the cooldown,
    the job does not re-fire — even if the predictor would have returned
    a valid prediction.
  * Active-task resolution prefers the Redis active_stopwatch; falls back
    to a Task.state==EXECUTING query when Redis is empty.
  * A predictor exception for one user does not leave partial writes.
"""
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.models import (
    PausePredictionLog,
    StopwatchSession,
    Task,
    TaskState,
    User,
)
from app.db.scoping import set_current_user_id
from app.services.pause_predictor import PausePrediction
from app.utils.time_utils import now_utc
from app.workers.jobs.pause_prediction import _run_for_one_user

USER_ID = 910


@pytest.fixture(autouse=True)
def _clean_slate(db):
    """Wipe relevant tables and scoping before and after each test."""
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
        email="pause-pred-job@test",
        is_operator=False,
        notion_enabled=False,
        created_at=now_utc(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_executing_task(db, user_id: int = USER_ID) -> Task:
    now = now_utc()
    t = Task(
        task_id=str(uuid4()),
        user_id=user_id,
        title="active work",
        category="dev",
        state=TaskState.EXECUTING,
        planned_start_utc=now - timedelta(minutes=25),
        planned_end_utc=now + timedelta(minutes=35),
        planned_duration_minutes=60,
        executed_start_utc=now - timedelta(minutes=25),
        source="manual",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _canned_prediction(user_id: int = USER_ID, mechanism: str = "clock_anchor") -> PausePrediction:
    now = now_utc()
    return PausePrediction(
        user_id=user_id,
        mechanism=mechanism,
        fired_at=now,
        predicted_at=now + timedelta(minutes=3),
        confidence=0.72,
        lead_minutes=3,
        sample_size=7,
        active_task_id=None,
    )


def test_firing_writes_log_row_and_queues_notification(db, user):
    """Happy path: predictor returns → one row + one httpx.post."""
    canned = _canned_prediction()

    with patch("app.workers.jobs.pause_prediction.PausePredictor") as mock_cls, \
         patch("app.workers.jobs.pause_prediction.httpx") as mock_httpx, \
         patch("app.workers.jobs.pause_prediction.send_telegram_message_sync"):
        mock_cls.return_value.predict.return_value = canned
        _run_for_one_user(db, user)

    rows = db.query(PausePredictionLog).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.user_id == USER_ID
    assert row.mechanism == "clock_anchor"
    assert row.lead_minutes == 3
    assert row.sample_size == 7
    assert row.confidence == 0.72
    assert row.user_response is None
    assert row.response_at is None

    assert mock_httpx.post.call_count == 1
    call = mock_httpx.post.call_args
    assert call.args[0].endswith("/v1/notifications/push")
    assert call.kwargs["json"]["type"] == "pause_prediction"
    assert call.kwargs["json"]["firing_id"] == row.firing_id
    assert call.kwargs["headers"] == {"X-User-Id": str(USER_ID)}


def test_no_prediction_no_row_no_queue(db, user):
    """Predictor returns None → no row, no notification."""
    with patch("app.workers.jobs.pause_prediction.PausePredictor") as mock_cls, \
         patch("app.workers.jobs.pause_prediction.httpx") as mock_httpx, \
         patch("app.workers.jobs.pause_prediction.send_telegram_message_sync"):
        mock_cls.return_value.predict.return_value = None
        _run_for_one_user(db, user)

    assert db.query(PausePredictionLog).count() == 0
    assert mock_httpx.post.call_count == 0


def test_cooldown_blocks_refire(db, user):
    """A firing within FIRING_COOLDOWN_MINUTES suppresses the next tick."""
    now = now_utc()
    recent = PausePredictionLog(
        user_id=USER_ID,
        fired_at=now - timedelta(minutes=3),
        predicted_at=now - timedelta(minutes=1),
        mechanism="clock_anchor",
        confidence=0.55,
        lead_minutes=2,
        sample_size=5,
    )
    db.add(recent)
    db.commit()

    with patch("app.workers.jobs.pause_prediction.PausePredictor") as mock_cls, \
         patch("app.workers.jobs.pause_prediction.httpx") as mock_httpx, \
         patch("app.workers.jobs.pause_prediction.send_telegram_message_sync"):
        mock_cls.return_value.predict.return_value = _canned_prediction()
        _run_for_one_user(db, user)

    # Only the seeded row remains; the predictor was not called,
    # and no notification was enqueued.
    assert db.query(PausePredictionLog).count() == 1
    assert mock_cls.return_value.predict.call_count == 0
    assert mock_httpx.post.call_count == 0


def test_cooldown_expired_allows_fire(db, user):
    """A firing older than FIRING_COOLDOWN_MINUTES does not block a new fire."""
    now = now_utc()
    old = PausePredictionLog(
        user_id=USER_ID,
        fired_at=now - timedelta(minutes=30),
        predicted_at=now - timedelta(minutes=28),
        mechanism="clock_anchor",
        confidence=0.55,
        lead_minutes=2,
        sample_size=5,
        user_response="no_response",
        response_at=now - timedelta(minutes=23),
    )
    db.add(old)
    db.commit()

    with patch("app.workers.jobs.pause_prediction.PausePredictor") as mock_cls, \
         patch("app.workers.jobs.pause_prediction.httpx"), \
         patch("app.workers.jobs.pause_prediction.send_telegram_message_sync"):
        mock_cls.return_value.predict.return_value = _canned_prediction()
        _run_for_one_user(db, user)

    assert db.query(PausePredictionLog).count() == 2


def test_active_task_resolved_via_executing_query(db, user):
    """With no Redis active_stopwatch, the EXECUTING task is passed to predict()."""
    task = _make_executing_task(db)

    with patch("app.workers.jobs.pause_prediction.PausePredictor") as mock_cls, \
         patch("app.workers.jobs.pause_prediction.RedisClient") as mock_redis_cls, \
         patch("app.workers.jobs.pause_prediction.httpx"), \
         patch("app.workers.jobs.pause_prediction.send_telegram_message_sync"):
        mock_redis_cls.return_value.get_active_stopwatch.return_value = None
        mock_cls.return_value.predict.return_value = None
        _run_for_one_user(db, user)

    predict_call = mock_cls.return_value.predict.call_args
    assert predict_call.kwargs["active_task"] is not None
    assert predict_call.kwargs["active_task"].task_id == task.task_id


def test_predictor_exception_does_not_leak_row(db, user):
    """A predictor exception must not leave a half-written pause_prediction_log row."""
    with patch("app.workers.jobs.pause_prediction.PausePredictor") as mock_cls, \
         patch("app.workers.jobs.pause_prediction.httpx") as mock_httpx, \
         patch("app.workers.jobs.pause_prediction.send_telegram_message_sync"):
        mock_cls.return_value.predict.side_effect = RuntimeError("boom")
        _run_for_one_user(db, user)

    assert db.query(PausePredictionLog).count() == 0
    assert mock_httpx.post.call_count == 0


def test_notification_push_failure_keeps_row(db, user):
    """If the /push call fails, the log row must still be committed."""
    canned = _canned_prediction()

    with patch("app.workers.jobs.pause_prediction.PausePredictor") as mock_cls, \
         patch("app.workers.jobs.pause_prediction.httpx") as mock_httpx, \
         patch("app.workers.jobs.pause_prediction.send_telegram_message_sync"):
        mock_cls.return_value.predict.return_value = canned
        mock_httpx.post.side_effect = RuntimeError("network")
        _run_for_one_user(db, user)

    # Research artifact is durable regardless of notification delivery.
    assert db.query(PausePredictionLog).count() == 1


def test_firing_delivers_telegram_message_with_firing_metadata(db, user):
    """5b: Telegram outbound fires with lead_minutes + mechanism in the text."""
    canned = _canned_prediction()

    with patch("app.workers.jobs.pause_prediction.PausePredictor") as mock_cls, \
         patch("app.workers.jobs.pause_prediction.httpx"), \
         patch(
             "app.workers.jobs.pause_prediction.send_telegram_message_sync"
         ) as mock_telegram:
        mock_cls.return_value.predict.return_value = canned
        mock_telegram.return_value = True
        _run_for_one_user(db, user)

    assert mock_telegram.call_count == 1
    text = mock_telegram.call_args.args[0]
    # Template must include the things the user needs to act:
    #   * lead time ("~3 min")
    #   * mechanism label (humanised)
    #   * the three valid reply keywords so the recipient sees the menu.
    assert "3 min" in text
    assert "clock anchor" in text
    assert "pause" in text and "dismiss" in text and "snooze" in text


def test_telegram_failure_does_not_rollback_row(db, user):
    """A Telegram delivery failure must NOT undo the research row."""
    canned = _canned_prediction()

    with patch("app.workers.jobs.pause_prediction.PausePredictor") as mock_cls, \
         patch("app.workers.jobs.pause_prediction.httpx"), \
         patch(
             "app.workers.jobs.pause_prediction.send_telegram_message_sync"
         ) as mock_telegram:
        mock_cls.return_value.predict.return_value = canned
        mock_telegram.side_effect = RuntimeError("bot token revoked")
        _run_for_one_user(db, user)

    assert db.query(PausePredictionLog).count() == 1
