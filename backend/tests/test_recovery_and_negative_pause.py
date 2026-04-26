"""Regression tests for LYR-080, LYR-088, LYR-106.

LYR-080: Backend rebuild during an active paused session left the user with
  a banner showing zero elapsed and no paused indicator — Redis state was
  lost and _recover_from_db did not rehydrate pause_state for paused tasks.
  Apr 25 fix: priority-ordered recovery rehydrates pause_state from the
  paused_session.paused_at_utc when falling through to PAUSED-task fallback.

LYR-088: After resuming on Stopwatch A while Stopwatch B was paused-mid-work
  (multi-tasking swap), recovery occasionally surfaced B as active because
  start_time_utc.DESC ordering picked the most-recently-started session
  rather than the one currently EXECUTING. Apr 25 fix: priority 1 is the
  unique session whose Task.state == EXECUTING; paused fallback is only
  reached when no executing task exists for the user.

LYR-106: Day-18 sweep found one production row (u=5, pe=a3c8629f, -12.02 min)
  where a resume() computed a negative pause_duration. Either clock skew or
  ContextVar drift between pause and resume. The guard logs and clamps to 0.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.models import PauseEvent, StopwatchSession, Task, TaskState, User
from app.db.scoping import set_current_user_id
from app.services.stopwatch_manager import StopwatchManager
from app.utils.time_utils import now_utc
from tests.conftest import TestingSession


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


@pytest.fixture
def clean_state(db):
    """Per-test DB + Redis wipe. Mirrors test_pause_resume_pause_event.py."""
    try:
        from app.utils.redis_client import RedisClient
        rc = RedisClient()
        for uid in ("1", "77", "user_primary"):
            rc.clear_active_stopwatch(uid)
            rc.client.delete(f"stopwatch:paused:{uid}")
    except Exception:
        pass

    set_current_user_id(None)
    wipe = TestingSession()
    try:
        wipe.execute(text("DELETE FROM pause_event"))
        wipe.execute(text("DELETE FROM stopwatch_session"))
        wipe.execute(text("DELETE FROM task"))
        wipe.execute(text("DELETE FROM user"))
        wipe.commit()
    finally:
        wipe.close()

    db.rollback()
    db.expire_all()

    if db.query(User).filter(User.user_id == 1).first() is None:
        db.add(User(
            user_id=1, email="recovery-test@x",
            is_operator=False, notion_enabled=False,
            created_at=datetime.utcnow(),
        ))
        db.commit()

    yield db
    set_current_user_id(None)


def _seed_task(db, *, state: TaskState, title: str = "t") -> Task:
    now = now_utc()
    task = Task(
        task_id=str(uuid4()),
        user_id=1,
        title=title,
        category="dev",
        state=state,
        planned_start_utc=now,
        planned_end_utc=now + timedelta(minutes=30),
        planned_duration_minutes=30,
        source="manual",
    )
    db.add(task)
    db.commit()
    return task


def _seed_session(db, task: Task, *, paused_at: datetime = None) -> StopwatchSession:
    session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=1,
        start_time_utc=now_utc() - timedelta(minutes=10),
        total_paused_minutes=0.0,
        paused_at_utc=paused_at,
    )
    db.add(session)
    db.commit()
    return session


# ---------- LYR-088: priority-ordered recovery ----------

@needs_redis
def test_recover_picks_executing_task_over_paused(clean_state):
    """An EXECUTING session must win over a more-recently-started PAUSED one."""
    db = clean_state
    set_current_user_id(1)

    paused_task = _seed_task(db, state=TaskState.PAUSED, title="paused other")
    paused_started_later = StopwatchSession(
        session_id=str(uuid4()),
        task_id=paused_task.task_id,
        user_id=1,
        start_time_utc=now_utc() - timedelta(minutes=2),
        total_paused_minutes=0.0,
        paused_at_utc=now_utc() - timedelta(seconds=30),
    )
    db.add(paused_started_later)
    db.commit()

    executing_task = _seed_task(db, state=TaskState.EXECUTING, title="executing now")
    executing_session = _seed_session(db, executing_task)

    mgr = StopwatchManager(db)
    active = mgr._recover_from_db("1")

    assert active is not None
    assert active["task_id"] == executing_task.task_id, (
        f"LYR-088 regression: recovery returned task_id={active['task_id']!r} "
        f"but EXECUTING task is {executing_task.task_id!r}"
    )
    assert active["session_id"] == executing_session.session_id


@needs_redis
def test_recover_falls_back_to_most_recent_paused(clean_state):
    """No EXECUTING task → fall back to the most-recently-paused session."""
    db = clean_state
    set_current_user_id(1)

    older_paused_task = _seed_task(db, state=TaskState.PAUSED, title="older")
    older_session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=older_paused_task.task_id,
        user_id=1,
        start_time_utc=now_utc() - timedelta(minutes=20),
        total_paused_minutes=0.0,
        paused_at_utc=now_utc() - timedelta(minutes=10),
    )
    db.add(older_session)
    db.commit()

    newer_paused_task = _seed_task(db, state=TaskState.PAUSED, title="newer")
    newer_session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=newer_paused_task.task_id,
        user_id=1,
        start_time_utc=now_utc() - timedelta(minutes=5),
        total_paused_minutes=0.0,
        paused_at_utc=now_utc() - timedelta(seconds=30),
    )
    db.add(newer_session)
    db.commit()

    mgr = StopwatchManager(db)
    active = mgr._recover_from_db("1")

    assert active is not None
    assert active["task_id"] == newer_paused_task.task_id
    assert active["session_id"] == newer_session.session_id


# ---------- LYR-080: pause_state rehydration ----------

@needs_redis
def test_recover_rehydrates_pause_state_for_paused_task(clean_state):
    """After Redis loss on a paused session, recovery must rehydrate pause_state."""
    db = clean_state
    set_current_user_id(1)

    paused_at = now_utc() - timedelta(minutes=3)
    paused_task = _seed_task(db, state=TaskState.PAUSED, title="lost-redis")
    session = _seed_session(db, paused_task, paused_at=paused_at)

    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    rc.clear_active_stopwatch("1")
    rc.client.delete("stopwatch:paused:1")

    mgr = StopwatchManager(db)
    active = mgr._recover_from_db("1")

    assert active is not None
    assert active["task_id"] == paused_task.task_id
    assert active["session_id"] == session.session_id

    pause_state = rc.get_pause_state("1")
    assert pause_state is not None, (
        "LYR-080 regression: pause_state must be rehydrated from "
        "session.paused_at_utc when recovery returns a PAUSED-state task"
    )
    assert pause_state["session_id"] == session.session_id


@needs_redis
def test_recover_clears_lingering_pause_state_on_executing_recovery(clean_state):
    """If recovery picks an EXECUTING task, lingering pause_state must be cleared."""
    db = clean_state
    set_current_user_id(1)

    executing_task = _seed_task(db, state=TaskState.EXECUTING)
    _seed_session(db, executing_task)

    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    rc.client.set("stopwatch:paused:1",
                  '{"session_id":"ghost","paused_at":"2026-01-01T00:00:00+00:00"}')

    mgr = StopwatchManager(db)
    active = mgr._recover_from_db("1")

    assert active is not None
    assert rc.get_pause_state("1") is None, (
        "Lingering pause_state on EXECUTING recovery would make the banner "
        "report paused=true for an unpaused task"
    )


# ---------- LYR-106: negative pause duration guard ----------

@needs_redis
def test_resume_clamps_negative_pause_duration_to_zero(clean_state, caplog):
    """A future-dated paused_at must not produce a negative pause_duration."""
    import logging
    caplog.set_level(logging.ERROR)
    db = clean_state
    set_current_user_id(1)

    executing_task = _seed_task(db, state=TaskState.PAUSED, title="negative")
    paused_at_future = now_utc() + timedelta(minutes=15)
    session = _seed_session(db, executing_task, paused_at=paused_at_future)

    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    rc.set_active_stopwatch(
        user_id="1",
        session_id=session.session_id,
        task_id=executing_task.task_id,
        title=executing_task.title,
        start_time=session.start_time_utc.isoformat(),
    )
    rc.set_pause_state("1", session.session_id, paused_at_future.isoformat())

    mgr = StopwatchManager(db)
    mgr.resume()

    db.refresh(session)
    assert session.total_paused_minutes == 0.0, (
        f"LYR-106 regression: total_paused_minutes={session.total_paused_minutes} "
        f"after resume() with future paused_at — must clamp to 0."
    )
    assert any("LYR-106" in rec.message for rec in caplog.records), (
        "LYR-106 guard must log when negative pause_duration is detected"
    )


@needs_redis
def test_resume_tolerates_small_clock_skew_silently(clean_state, caplog):
    """Sub-5-second negative drift must clamp without logging — normal clock skew."""
    import logging
    caplog.set_level(logging.ERROR)
    db = clean_state
    set_current_user_id(1)

    paused_task = _seed_task(db, state=TaskState.PAUSED, title="tiny-skew")
    paused_at_slightly_future = now_utc() + timedelta(seconds=2)
    session = _seed_session(db, paused_task, paused_at=paused_at_slightly_future)

    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    rc.set_active_stopwatch(
        user_id="1",
        session_id=session.session_id,
        task_id=paused_task.task_id,
        title=paused_task.title,
        start_time=session.start_time_utc.isoformat(),
    )
    rc.set_pause_state("1", session.session_id, paused_at_slightly_future.isoformat())

    mgr = StopwatchManager(db)
    mgr.resume()

    db.refresh(session)
    assert session.total_paused_minutes == 0.0
    assert not any("LYR-106" in rec.message for rec in caplog.records), (
        "Tiny clock-skew (<5s) must not log — would flood logs in production"
    )
