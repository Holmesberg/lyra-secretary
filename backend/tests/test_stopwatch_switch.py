"""Tests for the multi-tasking swap endpoint (Apr 25 2026).

Pins the StopwatchManager.switch_to_task() contract:
  * Source EXECUTING + valid target → atomic pause source + resume target
  * Source PAUSED (interruption flow) + valid target → swap (no duplicate pause_event)
  * No source active + valid target → just resume target
  * Switch-to-self idempotency (no-op or normal resume)
  * Target validation (not found / voided / wrong state / no open session)
  * pause_event lifecycle: source gets new pause_event with reason='task_switch';
    target's open pause_event closed with resumed_at + duration
  * Redis active_stopwatch swapped to target's session
  * Single-transaction atomicity (commit covers source pause + target resume)
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.models import (
    PauseEvent,
    StopwatchSession,
    Task,
    TaskState,
    User,
)
from app.db.scoping import set_current_user_id
from app.services.stopwatch_manager import StopwatchManager
from app.utils.time_utils import now_utc
from tests.conftest import TestingSession


USER_ID = 920


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


@pytest.fixture(autouse=True)
def _clean_env(db):
    """Wipe DB + Redis before and after each test."""
    set_current_user_id(None)

    if _redis_available():
        from app.utils.redis_client import RedisClient
        rc = RedisClient()
        rc.clear_active_stopwatch(str(USER_ID))
        rc.clear_pause_state(str(USER_ID))

    wipe = TestingSession()
    try:
        wipe.execute(text("DELETE FROM pause_event"))
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
            user_id=USER_ID, email="switch-test@x",
            is_operator=False, notion_enabled=False,
            created_at=datetime.utcnow(),
        ))
        seed.commit()
    finally:
        seed.close()
    set_current_user_id(USER_ID)
    yield
    set_current_user_id(None)
    if _redis_available():
        from app.utils.redis_client import RedisClient
        rc = RedisClient()
        rc.clear_active_stopwatch(str(USER_ID))
        rc.clear_pause_state(str(USER_ID))


def _make_task(db, *, title="task", state=TaskState.PLANNED) -> Task:
    now = now_utc()
    t = Task(
        task_id=str(uuid4()),
        user_id=USER_ID,
        title=title,
        category="dev",
        state=state,
        planned_start_utc=now - timedelta(minutes=10),
        planned_end_utc=now + timedelta(minutes=50),
        planned_duration_minutes=60,
        source="manual",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _make_open_session(db, task, *, paused_at: datetime = None,
                       start_offset_min: int = 30) -> StopwatchSession:
    s = StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=USER_ID,
        start_time_utc=now_utc() - timedelta(minutes=start_offset_min),
        end_time_utc=None,
        auto_closed=False,
        total_paused_minutes=0.0,
        paused_at_utc=paused_at,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _make_pause_event(db, session, paused_at: datetime) -> PauseEvent:
    evt = PauseEvent(
        pause_event_id=str(uuid4()),
        session_id=session.session_id,
        user_id=USER_ID,
        paused_at_utc=paused_at,
        pause_reason="distraction",
        pause_initiator="self",
        active_elapsed_at_pause_seconds=0,
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt


def _set_redis_active(session_id: str, task_id: str, title: str,
                      start_iso: str, paused: bool = False):
    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    rc.set_active_stopwatch(
        user_id=str(USER_ID),
        session_id=session_id,
        task_id=task_id,
        title=title,
        start_time=start_iso,
    )
    if paused:
        rc.set_pause_state(str(USER_ID), session_id, now_utc().isoformat())
    else:
        rc.clear_pause_state(str(USER_ID))


# ---------------------------------------------------------------------------
# Validation rejections
# ---------------------------------------------------------------------------


@needs_redis
def test_switch_target_not_found_rejected(db):
    """Unknown target task_id → ValueError."""
    mgr = StopwatchManager(db)
    with pytest.raises(ValueError, match="Target task not found"):
        mgr.switch_to_task("00000000-0000-0000-0000-000000000000")


@needs_redis
def test_switch_target_voided_rejected(db):
    """Voided target → ValueError."""
    target = _make_task(db, state=TaskState.PAUSED)
    target.voided_at = now_utc()
    db.commit()
    mgr = StopwatchManager(db)
    with pytest.raises(ValueError, match="voided"):
        mgr.switch_to_task(target.task_id)


@needs_redis
def test_switch_target_planned_rejected(db):
    """Target in PLANNED state → ValueError (must be PAUSED)."""
    target = _make_task(db, state=TaskState.PLANNED)
    mgr = StopwatchManager(db)
    with pytest.raises(ValueError, match="must be PAUSED"):
        mgr.switch_to_task(target.task_id)


@needs_redis
def test_switch_target_executed_rejected(db):
    """Target in terminal EXECUTED state → ValueError."""
    target = _make_task(db, state=TaskState.EXECUTED)
    mgr = StopwatchManager(db)
    with pytest.raises(ValueError, match="must be PAUSED"):
        mgr.switch_to_task(target.task_id)


@needs_redis
def test_switch_target_paused_no_open_session_rejected(db):
    """PAUSED target with no open StopwatchSession → ValueError (start instead)."""
    target = _make_task(db, state=TaskState.PAUSED)
    # No session created.
    mgr = StopwatchManager(db)
    with pytest.raises(ValueError, match="no open session"):
        mgr.switch_to_task(target.task_id)


# ---------------------------------------------------------------------------
# Happy paths — three source variants × valid target
# ---------------------------------------------------------------------------


@needs_redis
def test_switch_from_executing_source_to_paused_target(db):
    """Source EXECUTING + target PAUSED-with-open-session → swap."""
    source = _make_task(db, title="source", state=TaskState.EXECUTING)
    source_session = _make_open_session(db, source, start_offset_min=20)

    target = _make_task(db, title="target", state=TaskState.PAUSED)
    target_paused_at = now_utc() - timedelta(minutes=15)
    target_session = _make_open_session(
        db, target, paused_at=target_paused_at, start_offset_min=45
    )
    _make_pause_event(db, target_session, target_paused_at)

    _set_redis_active(
        source_session.session_id, source.task_id,
        source.title, source_session.start_time_utc.isoformat(),
        paused=False,
    )

    mgr = StopwatchManager(db)
    result = mgr.switch_to_task(target.task_id)

    assert result["switched"] is True
    assert result["noop"] is False
    assert result["from_task_id"] == source.task_id
    assert result["to_task_id"] == target.task_id
    assert result["target_pause_duration_minutes"] >= 14.0  # ~15min, allow tolerance

    # Source should now be PAUSED with a new pause_event of reason='task_switch'
    db.refresh(source)
    assert source.state == TaskState.PAUSED
    source_pause_events = (
        db.query(PauseEvent)
        .filter(PauseEvent.session_id == source_session.session_id)
        .all()
    )
    assert len(source_pause_events) == 1
    assert source_pause_events[0].pause_reason == "task_switch"
    assert source_pause_events[0].pause_initiator == "self"
    assert source_pause_events[0].resumed_at_utc is None  # source is now paused

    # Target should be EXECUTING with its pause_event closed
    db.refresh(target)
    assert target.state == TaskState.EXECUTING
    target_pause_events = (
        db.query(PauseEvent)
        .filter(PauseEvent.session_id == target_session.session_id)
        .all()
    )
    assert len(target_pause_events) == 1
    assert target_pause_events[0].resumed_at_utc is not None
    assert target_pause_events[0].duration_minutes is not None

    # Redis active should now point at target's session
    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    new_active = rc.get_active_stopwatch(str(USER_ID))
    assert new_active is not None
    assert new_active["task_id"] == target.task_id
    assert new_active["session_id"] == target_session.session_id
    assert rc.get_pause_state(str(USER_ID)) is None


@needs_redis
def test_switch_from_paused_source_to_paused_target_no_duplicate_event(db):
    """Source PAUSED (interruption-flow source) + target PAUSED → swap with NO new pause_event for source.

    The interruption flow leaves source paused with one open pause_event already.
    A switch back must not create a duplicate pause_event for source.
    """
    source = _make_task(db, title="source-paused", state=TaskState.PAUSED)
    source_paused_at = now_utc() - timedelta(minutes=8)
    source_session = _make_open_session(
        db, source, paused_at=source_paused_at, start_offset_min=30
    )
    _make_pause_event(db, source_session, source_paused_at)

    target = _make_task(db, title="target", state=TaskState.PAUSED)
    target_paused_at = now_utc() - timedelta(minutes=20)
    target_session = _make_open_session(
        db, target, paused_at=target_paused_at, start_offset_min=60
    )
    _make_pause_event(db, target_session, target_paused_at)

    # Redis points at source, with pause_state set (interruption-style)
    _set_redis_active(
        source_session.session_id, source.task_id,
        source.title, source_session.start_time_utc.isoformat(),
        paused=True,
    )

    mgr = StopwatchManager(db)
    result = mgr.switch_to_task(target.task_id)

    assert result["switched"] is True
    assert result["from_task_id"] == source.task_id
    assert result["to_task_id"] == target.task_id

    # Source still PAUSED, NO new pause_event added
    db.refresh(source)
    assert source.state == TaskState.PAUSED
    source_events = (
        db.query(PauseEvent)
        .filter(PauseEvent.session_id == source_session.session_id)
        .all()
    )
    assert len(source_events) == 1  # only the original
    assert source_events[0].pause_reason == "distraction"  # unchanged

    # Target now EXECUTING
    db.refresh(target)
    assert target.state == TaskState.EXECUTING


@needs_redis
def test_switch_no_source_active_just_resumes_target(db):
    """No active stopwatch + target PAUSED-with-open-session → resume target."""
    target = _make_task(db, title="lone-target", state=TaskState.PAUSED)
    target_paused_at = now_utc() - timedelta(minutes=10)
    target_session = _make_open_session(
        db, target, paused_at=target_paused_at, start_offset_min=30
    )
    _make_pause_event(db, target_session, target_paused_at)

    # Redis is empty — no active.
    from app.utils.redis_client import RedisClient
    RedisClient().clear_active_stopwatch(str(USER_ID))

    mgr = StopwatchManager(db)
    result = mgr.switch_to_task(target.task_id)

    assert result["switched"] is True
    assert result["from_task_id"] is None
    assert result["to_task_id"] == target.task_id

    db.refresh(target)
    assert target.state == TaskState.EXECUTING


# ---------------------------------------------------------------------------
# Idempotency: switch-to-self
# ---------------------------------------------------------------------------


@needs_redis
def test_switch_to_self_when_executing_is_noop(db):
    """Target == current EXECUTING active → noop=True, no state change."""
    task = _make_task(db, title="lonely", state=TaskState.EXECUTING)
    session = _make_open_session(db, task, start_offset_min=15)
    _set_redis_active(
        session.session_id, task.task_id, task.title,
        session.start_time_utc.isoformat(), paused=False,
    )

    # State machine doesn't allow EXECUTING for the validation, but the
    # switch endpoint enforces target.state == PAUSED. Pre-condition fails
    # before we get to the noop branch — so for this test, set state PAUSED
    # but Redis active points at target with paused=False (Redis-DB drift
    # case, defensive). The noop branch is reached.
    task.state = TaskState.PAUSED
    db.commit()

    mgr = StopwatchManager(db)
    result = mgr.switch_to_task(task.task_id)

    assert result["switched"] is True
    assert result["noop"] is True
    assert result["from_task_id"] is None
    assert result["to_task_id"] == task.task_id


# ---------------------------------------------------------------------------
# Atomicity / Redis state
# ---------------------------------------------------------------------------


@needs_redis
def test_switch_redis_swapped_atomically(db):
    """Redis active_stopwatch points to target after switch; pause_state cleared."""
    source = _make_task(db, title="src", state=TaskState.EXECUTING)
    source_session = _make_open_session(db, source, start_offset_min=10)
    target = _make_task(db, title="tgt", state=TaskState.PAUSED)
    target_paused_at = now_utc() - timedelta(minutes=5)
    target_session = _make_open_session(db, target, paused_at=target_paused_at)
    _make_pause_event(db, target_session, target_paused_at)

    _set_redis_active(
        source_session.session_id, source.task_id, source.title,
        source_session.start_time_utc.isoformat(), paused=False,
    )

    mgr = StopwatchManager(db)
    mgr.switch_to_task(target.task_id)

    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    new_active = rc.get_active_stopwatch(str(USER_ID))
    assert new_active["task_id"] == target.task_id
    assert new_active["session_id"] == target_session.session_id
    # Pause state must be cleared (target is now executing)
    assert rc.get_pause_state(str(USER_ID)) is None


# ---------------------------------------------------------------------------
# get_paused_others helper
# ---------------------------------------------------------------------------


@needs_redis
def test_recover_from_db_prefers_executing_over_most_recent_start(db):
    """Apr 25 multi-tasking recovery bug: with multiple open sessions
    (one EXECUTING + one PAUSED, where PAUSED has the more recent
    start_time), _recover_from_db must pick the EXECUTING task, not the
    most-recent-by-start.

    Reproduces the screenshot scenario: post-switch state has CO vid 2
    EXECUTING (older session) + feedback calibration PAUSED (newer
    session). If Redis is lost (TTL, eviction), recovery must rehydrate
    to CO vid 2, not feedback calibration. The pre-fix logic ordered by
    start_time DESC and picked feedback calibration — the wrong task.
    """
    # Older-start EXECUTING task (the post-swap "active" one)
    executing = _make_task(db, title="executing-older", state=TaskState.EXECUTING)
    executing_session = _make_open_session(db, executing, start_offset_min=180)

    # Newer-start PAUSED task (the post-swap source)
    paused = _make_task(db, title="paused-newer", state=TaskState.PAUSED)
    paused_at = now_utc() - timedelta(minutes=10)
    paused_session = _make_open_session(db, paused, paused_at=paused_at, start_offset_min=60)
    _make_pause_event(db, paused_session, paused_at)

    # Redis is empty — simulate Redis loss. Recovery should rehydrate
    # to the EXECUTING task's session, NOT the most-recent-by-start.
    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    rc.clear_active_stopwatch(str(USER_ID))
    rc.clear_pause_state(str(USER_ID))

    mgr = StopwatchManager(db)
    recovered = mgr._recover_from_db(str(USER_ID))

    assert recovered is not None
    assert recovered["task_id"] == executing.task_id
    assert recovered["session_id"] == executing_session.session_id

    # Pause state must be cleared on EXECUTING recovery
    assert rc.get_pause_state(str(USER_ID)) is None


@needs_redis
def test_recover_from_db_falls_back_to_most_recently_paused(db):
    """No EXECUTING task → recover the most-recently-paused PAUSED task
    and rehydrate pause_state."""
    older = _make_task(db, title="paused-older", state=TaskState.PAUSED)
    older_paused_at = now_utc() - timedelta(minutes=60)
    _make_open_session(db, older, paused_at=older_paused_at, start_offset_min=120)

    newer = _make_task(db, title="paused-newer", state=TaskState.PAUSED)
    newer_paused_at = now_utc() - timedelta(minutes=5)
    newer_session = _make_open_session(db, newer, paused_at=newer_paused_at, start_offset_min=30)

    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    rc.clear_active_stopwatch(str(USER_ID))
    rc.clear_pause_state(str(USER_ID))

    mgr = StopwatchManager(db)
    recovered = mgr._recover_from_db(str(USER_ID))

    assert recovered is not None
    assert recovered["task_id"] == newer.task_id
    assert recovered["session_id"] == newer_session.session_id

    # Pause state rehydrated for the paused task
    pause_state = rc.get_pause_state(str(USER_ID))
    assert pause_state is not None
    assert pause_state["session_id"] == newer_session.session_id


@needs_redis
def test_recover_from_db_returns_none_when_no_open_sessions(db):
    """No open sessions for the user → return None (nothing to recover)."""
    # Create a task with only a CLOSED session
    task = _make_task(db, title="closed-only", state=TaskState.PAUSED)
    closed_session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=USER_ID,
        start_time_utc=now_utc() - timedelta(hours=2),
        end_time_utc=now_utc() - timedelta(hours=1),
        auto_closed=True,
        total_paused_minutes=0.0,
    )
    db.add(closed_session)
    db.commit()

    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    rc.clear_active_stopwatch(str(USER_ID))
    rc.clear_pause_state(str(USER_ID))

    mgr = StopwatchManager(db)
    recovered = mgr._recover_from_db(str(USER_ID))

    assert recovered is None


@needs_redis
def test_get_paused_others_returns_only_paused_with_open_sessions(db):
    """Helper returns paused-with-open-session tasks excluding the active one."""
    # Active task
    active_task = _make_task(db, title="active", state=TaskState.EXECUTING)
    active_session = _make_open_session(db, active_task, start_offset_min=5)
    _set_redis_active(
        active_session.session_id, active_task.task_id, active_task.title,
        active_session.start_time_utc.isoformat(), paused=False,
    )

    # Paused candidate (legitimate switch target)
    candidate = _make_task(db, title="candidate", state=TaskState.PAUSED)
    candidate_paused_at = now_utc() - timedelta(minutes=12)
    _make_open_session(db, candidate, paused_at=candidate_paused_at, start_offset_min=30)

    # Voided paused — must be filtered out
    voided = _make_task(db, title="voided", state=TaskState.PAUSED)
    voided.voided_at = now_utc()
    db.commit()
    _make_open_session(db, voided, paused_at=now_utc(), start_offset_min=45)

    # PLANNED task (no open session, no pause) — irrelevant
    _make_task(db, title="planned", state=TaskState.PLANNED)

    # Closed-session paused task — has session but it's closed
    closed_paused = _make_task(db, title="closed-paused", state=TaskState.PAUSED)
    closed_session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=closed_paused.task_id,
        user_id=USER_ID,
        start_time_utc=now_utc() - timedelta(hours=2),
        end_time_utc=now_utc() - timedelta(hours=1),
        auto_closed=True,
        total_paused_minutes=0.0,
    )
    db.add(closed_session)
    db.commit()

    mgr = StopwatchManager(db)
    others = mgr.get_paused_others()

    assert len(others) == 1
    assert others[0]["task_id"] == candidate.task_id
    assert others[0]["title"] == "candidate"
    assert others[0]["paused_minutes"] >= 11
    # Apr 25 perf fix: chip carries server-computed elapsed snapshot for
    # instant optimistic anchoring on the frontend.
    assert "elapsed_minutes" in others[0]
    assert isinstance(others[0]["elapsed_minutes"], int)
    assert others[0]["elapsed_minutes"] >= 0
    assert "start_time" in others[0]
    assert "total_paused_minutes" in others[0]
