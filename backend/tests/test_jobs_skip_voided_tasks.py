"""Regression tests: background jobs must skip voided tasks.

Covers the 5 background job fixes from the voided_at audit (commit 1):
  - reminders.py: check_upcoming_tasks
  - timer_overflow.py: check_timer_overflow
  - overdue_tasks.py: detect_and_skip_overdue_tasks
  - stale_session_recovery.py: run_stale_session_recovery
  - notion_sync.py: retry_failed_syncs

Each test creates a voided task in the job's target state and verifies
the job skips it (no side effects: no notifications, no state changes,
no Notion calls).

These tests call _run_for_one_user directly (not via for_each_user)
to avoid SessionLocal/scoping indirection. The voided_at filter is
the unit under test.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from uuid import uuid4

from sqlalchemy import text

from app.db.models import Task, StopwatchSession, User, TaskState
from app.db.scoping import set_current_user_id
from app.utils.time_utils import now_utc
from tests.conftest import TestingSession


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _redis_available() -> bool:
    try:
        from app.utils.redis_client import RedisClient
        RedisClient().client.ping()
        return True
    except Exception:
        return False


needs_redis = pytest.mark.skipif(
    not _redis_available(), reason="redis not reachable"
)

USER_ID = 900
NOW = now_utc()


@pytest.fixture(autouse=True)
def _clean_slate(db):
    """Wipe task/session/user tables before and after each test."""
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM stopwatch_session"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM user"))
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM stopwatch_session"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM user"))
    db.commit()


@pytest.fixture
def user(db):
    u = User(
        user_id=USER_ID,
        email="voided-test@test",
        is_operator=True,
        notion_enabled=True,
        created_at=NOW,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_task(db, *, state="PLANNED", voided=False, **overrides):
    """Create a task, optionally voided."""
    tid = str(uuid4())
    defaults = dict(
        task_id=tid,
        title=f"voided-test-{tid[:8]}",
        user_id=USER_ID,
        planned_start_utc=NOW - timedelta(hours=2),
        planned_end_utc=NOW - timedelta(hours=1),
        planned_duration_minutes=60,
        state=state,
        source="manual",
        created_at=NOW,
        last_modified_at=NOW,
    )
    defaults.update(overrides)
    if voided:
        defaults["voided_at"] = NOW - timedelta(minutes=30)
        defaults["voided_reason"] = "test_contamination"
    t = Task(**defaults)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _make_session(db, task, *, stale=False, **overrides):
    """Create a StopwatchSession for a task."""
    sid = str(uuid4())
    start = NOW - timedelta(hours=49) if stale else NOW - timedelta(minutes=30)
    defaults = dict(
        session_id=sid,
        task_id=task.task_id,
        start_time_utc=start,
        end_time_utc=None,
        auto_closed=False,
        total_paused_minutes=0.0,
        user_id=USER_ID,
    )
    defaults.update(overrides)
    s = StopwatchSession(**defaults)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ---------------------------------------------------------------------------
# 1. reminders — voided PLANNED task should NOT trigger reminder
# ---------------------------------------------------------------------------

@needs_redis
def test_reminders_skip_voided_task(db, user):
    """A voided PLANNED task within the 15-min window must not get a reminder."""
    from app.workers.jobs.reminders import _run_for_one_user

    set_current_user_id(USER_ID)

    # Non-voided task: upcoming in 10 min
    live_task = _make_task(
        db,
        state="PLANNED",
        voided=False,
        planned_start_utc=NOW + timedelta(minutes=10),
        planned_end_utc=NOW + timedelta(minutes=70),
    )

    # Voided task: also upcoming in 10 min
    voided_task = _make_task(
        db,
        state="PLANNED",
        voided=True,
        planned_start_utc=NOW + timedelta(minutes=10),
        planned_end_utc=NOW + timedelta(minutes=70),
    )

    with patch("app.workers.jobs.reminders.send_telegram_message_sync") as mock_tg, \
         patch("app.workers.jobs.reminders.enqueue_user_notification") as mock_enqueue:
        mock_tg.return_value = True
        _run_for_one_user(db, user)

    # Telegram should be called exactly once (for the live task)
    assert mock_tg.call_count == 1
    assert mock_enqueue.call_count == 1
    msg = mock_tg.call_args[0][0]
    assert live_task.title in msg
    assert voided_task.title not in msg


# ---------------------------------------------------------------------------
# 2. timer_overflow — voided task with open session should NOT trigger alert
# ---------------------------------------------------------------------------

@needs_redis
def test_timer_overflow_skip_voided_task(db, user):
    """An open session on a voided task must not trigger overflow alert."""
    from app.workers.jobs.timer_overflow import _run_for_one_user

    set_current_user_id(USER_ID)

    # Voided task with an open session that's well past planned duration
    voided_task = _make_task(
        db,
        state="EXECUTING",
        voided=True,
        planned_duration_minutes=30,
    )
    _make_session(
        db,
        voided_task,
        start_time_utc=NOW - timedelta(minutes=120),  # 120 min ago, planned 30
    )

    # Live task with an open session also overflowing
    live_task = _make_task(
        db,
        state="EXECUTING",
        voided=False,
        planned_duration_minutes=30,
    )
    _make_session(
        db,
        live_task,
        start_time_utc=NOW - timedelta(minutes=120),
    )

    with patch("app.workers.jobs.timer_overflow.send_telegram_message_sync") as mock_tg, \
         patch("app.workers.jobs.timer_overflow.enqueue_user_notification") as mock_enqueue:
        mock_tg.return_value = True
        _run_for_one_user(db, user)

    # Only the live task should trigger an alert
    assert mock_tg.call_count == 1
    assert mock_enqueue.call_count == 1
    msg = mock_tg.call_args[0][0]
    assert live_task.title in msg
    assert voided_task.title not in msg


# ---------------------------------------------------------------------------
# 3. overdue_tasks — voided PLANNED task past window should NOT be skipped
# ---------------------------------------------------------------------------

def test_overdue_skip_voided_task(db, user):
    """A voided PLANNED task past its window must not transition to SKIPPED."""
    from app.workers.jobs.overdue_tasks import _run_for_one_user

    set_current_user_id(USER_ID)

    # Voided task: window ended 1h ago, never started
    voided_task = _make_task(
        db,
        state="PLANNED",
        voided=True,
        planned_start_utc=NOW - timedelta(hours=3),
        planned_end_utc=NOW - timedelta(hours=1),
        initiation_status="not_started",
    )

    # Live task: also overdue
    live_task = _make_task(
        db,
        state="PLANNED",
        voided=False,
        planned_start_utc=NOW - timedelta(hours=3),
        planned_end_utc=NOW - timedelta(hours=1),
        initiation_status="not_started",
    )

    _run_for_one_user(db, user)

    db.refresh(voided_task)
    db.refresh(live_task)

    # Voided task state must be untouched
    assert voided_task.state == TaskState.PLANNED
    # Live task should have been transitioned
    assert live_task.state == TaskState.SKIPPED


# ---------------------------------------------------------------------------
# 4. stale_session_recovery — session on voided task should NOT be auto-closed
# ---------------------------------------------------------------------------

def test_stale_recovery_skip_voided_task(db, user):
    """A stale session on a voided task must not be auto-closed."""
    from app.workers.jobs.stale_session_recovery import _run_for_one_user

    set_current_user_id(USER_ID)

    # Voided task with a 24h-old open session
    voided_task = _make_task(db, state="EXECUTING", voided=True)
    voided_session = _make_session(db, voided_task, stale=True)

    # Live task with a 24h-old open session
    live_task = _make_task(db, state="EXECUTING", voided=False)
    live_session = _make_session(db, live_task, stale=True)

    with patch("app.workers.jobs.stale_session_recovery.RedisClient") as MockRedis:
        mock_rc = MagicMock()
        mock_rc.get_active_stopwatch.return_value = None
        MockRedis.return_value = mock_rc

        _run_for_one_user(db, user)

    db.refresh(voided_session)
    db.refresh(live_session)

    # Voided session must remain open
    assert voided_session.end_time_utc is None
    assert voided_session.auto_closed is False

    # Live session should have been auto-closed
    assert live_session.end_time_utc is not None
    assert live_session.auto_closed is True


# ---------------------------------------------------------------------------
# 5. notion_sync — voided task should be dropped from queue, not synced
# ---------------------------------------------------------------------------

def test_notion_sync_skip_voided_task(db, user):
    """A voided task in the Notion retry queue must be dropped (not synced)."""
    from app.workers.jobs.notion_sync import _run_for_one_user

    set_current_user_id(USER_ID)

    voided_task = _make_task(db, state="PLANNED", voided=True)
    live_task = _make_task(db, state="PLANNED", voided=False)

    fake_queue = [
        {"task_id": voided_task.task_id},
        {"task_id": live_task.task_id},
    ]

    with patch("app.workers.jobs.notion_sync.RedisClient") as MockRedis, \
         patch("app.workers.jobs.notion_sync.NotionClient") as MockNotion:
        mock_rc = MagicMock()
        mock_rc.get_notion_sync_queue.return_value = fake_queue
        MockRedis.return_value = mock_rc

        mock_notion = MagicMock()
        MockNotion.return_value = mock_notion

        _run_for_one_user(db, user)

        # Notion sync should only be called for the live task
        assert mock_notion.sync_task.call_count == 1
        synced_task = mock_notion.sync_task.call_args[0][0]
        assert synced_task.task_id == live_task.task_id

        # Both items consumed from queue (voided = dropped, live = synced)
        mock_rc.remove_from_notion_queue.assert_called_once_with(
            user_id=str(USER_ID), count=2
        )
