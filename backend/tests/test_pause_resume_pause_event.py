"""Regression tests for pause/resume dual-write to pause_event + silent-default removal.

These tests pin the commit-4 contract:

  * The pause API rejects requests missing pause_reason or pause_initiator
    (silent defaults at stopwatch_manager.py:330-331 were removed).
  * Every pause() call inserts one pause_event row, closed on resume().
  * Multiple pauses in the same session produce multiple pause_event rows —
    historical fidelity, no overwrite data loss (the original motivating
    incident for migration 020).
  * Orphan-session cleanup and stale-session recovery both close any open
    pause_events for the closed session.
  * The service layer ValueErrors on falsy pause_reason/pause_initiator —
    defense in depth past the API boundary.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.models import PauseEvent, StopwatchSession, Task, TaskState, User
from app.db.scoping import set_current_user_id
from app.services.stopwatch_manager import StopwatchManager
from app.workers.jobs.stale_session_recovery import _run_for_one_user
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


def _h(uid: int = 1) -> dict:
    return {"X-User-Id": str(uid)}


@pytest.fixture
def clean_state(db):
    """Per-test DB + Redis wipe so stopwatch state doesn't leak across tests.

    Each test starts a stopwatch; without this the next test's /start hits
    "already running". Also clears the paused-session key. Pattern matches
    test_interruption_conflict.py's interrupt_user fixture — wipe via a
    separate TestingSession so any in-flight transaction on `db` is rolled
    back cleanly before the wipe.
    """
    try:
        from app.utils.redis_client import RedisClient
        rc = RedisClient()
        for uid in ("1", "66", "user_primary"):
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

    # Ensure user_id=1 exists so /v1/create (FK to user) doesn't fail.
    # Idempotent — wipe above may not actually take effect across sessions
    # with StaticPool, so we re-check rather than blindly insert.
    if db.query(User).filter(User.user_id == 1).first() is None:
        db.add(User(
            user_id=1, email="pause-event@test",
            is_operator=False, notion_enabled=False,
            created_at=datetime.utcnow(),
        ))
        db.commit()

    yield db
    set_current_user_id(None)


def _start_and_get_session(client, task_id: str, uid: int = 1) -> str:
    r = client.post(
        "/v1/stopwatch/start",
        json={"task_id": task_id, "pre_task_readiness": 3},
        headers=_h(uid),
    )
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def _create_task(client, title: str = "pause event task") -> str:
    # Use a window well into the future so start/pause/resume cycles are safe.
    now = datetime.now(timezone.utc)
    start = (now + timedelta(minutes=5)).isoformat()
    end = (now + timedelta(minutes=35)).isoformat()
    r = client.post(
        "/v1/create",
        json={"title": title, "start": start, "end": end},
        headers=_h(),
    )
    assert r.status_code == 200, r.text
    return r.json()["task_id"]


# ---------- API-layer contract ----------

@needs_redis
def test_pause_rejects_missing_body(clean_state, client):
    tid = _create_task(client, "missing body")
    _start_and_get_session(client, tid)
    r = client.post("/v1/stopwatch/pause", json={}, headers=_h())
    # Pydantic validation — required fields absent.
    assert r.status_code == 422, r.text


@needs_redis
def test_pause_rejects_missing_reason(clean_state, client):
    tid = _create_task(client, "missing reason")
    _start_and_get_session(client, tid)
    r = client.post(
        "/v1/stopwatch/pause",
        json={"pause_initiator": "self"},
        headers=_h(),
    )
    assert r.status_code == 422, r.text


@needs_redis
def test_pause_rejects_missing_initiator(clean_state, client):
    tid = _create_task(client, "missing initiator")
    _start_and_get_session(client, tid)
    r = client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "distraction"},
        headers=_h(),
    )
    assert r.status_code == 422, r.text


@needs_redis
def test_pause_rejects_invalid_enum(clean_state, client):
    tid = _create_task(client, "invalid enum")
    _start_and_get_session(client, tid)
    r = client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "because_i_said_so", "pause_initiator": "self"},
        headers=_h(),
    )
    assert r.status_code == 400, r.text


# ---------- Service-layer defense-in-depth ----------

def test_service_rejects_falsy_reason(db):
    """Even if the API were bypassed, the service layer must refuse empty values."""
    mgr = StopwatchManager(db)
    with pytest.raises(ValueError):
        mgr.pause(pause_reason="", pause_initiator="self")


def test_service_rejects_falsy_initiator(db):
    mgr = StopwatchManager(db)
    with pytest.raises(ValueError):
        mgr.pause(pause_reason="distraction", pause_initiator=None)  # type: ignore[arg-type]


# ---------- Dual-write + close ----------

@needs_redis
def test_pause_creates_pause_event_row(clean_state, client):
    tid = _create_task(client, "dual write 1")
    sid = _start_and_get_session(client, tid)

    r = client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "distraction", "pause_initiator": "self"},
        headers=_h(),
    )
    assert r.status_code == 200, r.text

    read = TestingSession()
    try:
        events = read.query(PauseEvent).filter_by(session_id=sid).all()
        assert len(events) == 1
        assert events[0].pause_reason == "distraction"
        assert events[0].pause_initiator == "self"
        assert events[0].resumed_at_utc is None
        assert events[0].duration_minutes is None
    finally:
        read.close()


@needs_redis
def test_resume_closes_pause_event(clean_state, client):
    tid = _create_task(client, "resume closes")
    sid = _start_and_get_session(client, tid)

    client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "prayer", "pause_initiator": "self"},
        headers=_h(),
    )
    r = client.post("/v1/stopwatch/resume", headers=_h())
    assert r.status_code == 200, r.text

    read = TestingSession()
    try:
        events = read.query(PauseEvent).filter_by(session_id=sid).all()
        assert len(events) == 1
        assert events[0].resumed_at_utc is not None
        assert events[0].duration_minutes is not None
        assert events[0].duration_minutes >= 0
    finally:
        read.close()


@needs_redis
def test_two_pauses_produce_two_events_no_overwrite(clean_state, client):
    """The original motivating incident — second pause must not lose first's metadata."""
    tid = _create_task(client, "two pauses")
    sid = _start_and_get_session(client, tid)

    client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "prayer", "pause_initiator": "self"},
        headers=_h(),
    )
    client.post("/v1/stopwatch/resume", headers=_h())
    client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "distraction", "pause_initiator": "external"},
        headers=_h(),
    )

    read = TestingSession()
    try:
        events = (
            read.query(PauseEvent)
            .filter_by(session_id=sid)
            .order_by(PauseEvent.paused_at_utc)
            .all()
        )
        assert len(events) == 2
        assert events[0].pause_reason == "prayer"
        assert events[0].pause_initiator == "self"
        assert events[0].resumed_at_utc is not None
        assert events[1].pause_reason == "distraction"
        assert events[1].pause_initiator == "external"
        assert events[1].resumed_at_utc is None  # current pause, still open
    finally:
        read.close()


# ---------- Orphan + stale cleanup ----------

def test_close_orphan_session_closes_open_pause_events(clean_state):
    """_close_orphan_session must close any open pause_events for the session."""
    db = clean_state
    task = Task(
        task_id=str(uuid4()),
        user_id=1,
        title="orphan test",
        category="dev",
        state=TaskState.EXECUTING,
        planned_start_utc=datetime.now(timezone.utc),
        planned_end_utc=datetime.now(timezone.utc) + timedelta(minutes=30),
        planned_duration_minutes=30,
        source="manual",
    )
    session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=1,
        start_time_utc=datetime.now(timezone.utc) - timedelta(minutes=10),
        total_paused_minutes=0.0,
    )
    db.add_all([task, session])
    db.commit()

    open_evt = PauseEvent(
        pause_event_id=str(uuid4()),
        session_id=session.session_id,
        user_id=1,
        paused_at_utc=datetime.now(timezone.utc) - timedelta(minutes=3),
        pause_reason="distraction",
        pause_initiator="self",
    )
    db.add(open_evt)
    db.commit()

    mgr = StopwatchManager(db)
    mgr._close_orphan_session(session.session_id)

    db.refresh(open_evt)
    db.refresh(session)
    assert session.end_time_utc is not None
    assert session.auto_closed is True
    assert open_evt.resumed_at_utc is not None
    assert open_evt.duration_minutes is not None
    assert open_evt.duration_minutes >= 0


def test_stale_session_recovery_closes_open_pause_events(clean_state):
    """The background sweep must also close dangling pause_events."""
    db = clean_state
    db.expire_all()
    # clean_state seeds user_id=1 via a separate session; expire_all is
    # required to see it on the test's session.
    user = db.query(User).filter(User.user_id == 1).first()
    assert user is not None, "fixture must seed user_id=1"

    started = datetime.now(timezone.utc) - timedelta(hours=49)
    task = Task(
        task_id=str(uuid4()),
        user_id=1,
        title="stale test",
        category="dev",
        state=TaskState.EXECUTING,
        planned_start_utc=started,
        planned_end_utc=started + timedelta(minutes=30),
        planned_duration_minutes=30,
        source="manual",
    )
    session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=1,
        start_time_utc=started,
        total_paused_minutes=0.0,
    )
    db.add_all([task, session])
    db.commit()

    open_evt = PauseEvent(
        pause_event_id=str(uuid4()),
        session_id=session.session_id,
        user_id=1,
        paused_at_utc=started + timedelta(minutes=5),
        pause_reason="prayer",
        pause_initiator="self",
    )
    db.add(open_evt)
    db.commit()

    _run_for_one_user(db, user)

    db.refresh(open_evt)
    db.refresh(session)
    assert session.end_time_utc is not None
    assert session.auto_closed is True
    assert open_evt.resumed_at_utc is not None
    assert open_evt.duration_minutes is not None
