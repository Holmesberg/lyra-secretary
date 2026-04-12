"""Regression tests: mutation endpoints reject voided tasks.

Covers the 7 mutation endpoint fixes from the voided_at audit (commit 2):
  1. mark-abandoned (skip_task)
  2. swap (swap_tasks)
  3. reschedule (reschedule_task)
  4. complete_task
  5. stopwatch start
  6. stopwatch stop
  7. update-completion

Each test creates a task via the API, voids it, then verifies the mutation
is rejected with a 400 error.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import text

from app.db.models import Task, StopwatchSession, User, TaskState
from app.db.scoping import set_current_user_id, get_current_user_id
from app.utils.time_utils import now_utc
from tests.conftest import TestingSession

USER_ID = 901
_H = {"X-User-Id": str(USER_ID)}


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


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat() + "Z"


def _future(minutes: int, duration: int = 60):
    start = datetime.utcnow() + timedelta(minutes=minutes)
    end = start + timedelta(minutes=duration)
    return _iso(start), _iso(end)


@pytest.fixture(autouse=True)
def _clean_slate(db):
    """Wipe tables and Redis stopwatch state before/after each test."""
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM stopwatch_session"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM user"))
    db.commit()

    # Seed user
    seed = TestingSession()
    try:
        seed.add(User(
            user_id=USER_ID,
            email="mutation-test@test",
            is_operator=True,
            notion_enabled=False,
            created_at=datetime.utcnow(),
        ))
        seed.commit()
    finally:
        seed.close()
    db.rollback()
    db.expire_all()

    # Clear Redis stopwatch state
    try:
        from app.utils.redis_client import RedisClient
        rc = RedisClient()
        rc.clear_active_stopwatch(str(USER_ID))
        rc.client.delete(f"stopwatch:paused:{USER_ID}")
    except Exception:
        pass

    yield

    set_current_user_id(None)
    wipe = TestingSession()
    try:
        wipe.execute(text("DELETE FROM stopwatch_session"))
        wipe.execute(text("DELETE FROM task"))
        wipe.execute(text("DELETE FROM user"))
        wipe.commit()
    finally:
        wipe.close()

    try:
        from app.utils.redis_client import RedisClient
        rc = RedisClient()
        rc.clear_active_stopwatch(str(USER_ID))
        rc.client.delete(f"stopwatch:paused:{USER_ID}")
    except Exception:
        pass


def _create_task(client, offset_min=10, duration=60, force=False):
    """Create a PLANNED task via the API and return its task_id."""
    start, end = _future(offset_min, duration)
    r = client.post(
        "/v1/create",
        json={"title": f"mut-test-{uuid4().hex[:8]}", "start": start, "end": end, "force": force},
        headers=_H,
    )
    assert r.status_code == 200, f"create failed: {r.json()}"
    return r.json()["task_id"]


def _void_task(client, task_id):
    """Void a task via the API."""
    r = client.post(
        f"/v1/tasks/{task_id}/void",
        json={"voided_reason": "test_contamination"},
        headers=_H,
    )
    assert r.status_code == 200, f"void failed: {r.json()}"


# ---------------------------------------------------------------------------
# 1. mark-abandoned rejects voided task
# ---------------------------------------------------------------------------

@needs_redis
def test_mark_abandoned_rejects_voided(client):
    tid = _create_task(client)
    _void_task(client, tid)
    r = client.post(f"/v1/tasks/{tid}/mark-abandoned", headers=_H)
    assert r.status_code == 400
    assert "voided" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 2. swap rejects when one task is voided
# ---------------------------------------------------------------------------

@needs_redis
def test_swap_rejects_voided(client):
    # Need a SKIPPED task + a PLANNED task. Create two, skip one, void it.
    tid_a = _create_task(client, offset_min=10)
    tid_b = _create_task(client, offset_min=80)

    # Skip task A
    r = client.post(f"/v1/tasks/{tid_a}/mark-abandoned", headers=_H)
    assert r.status_code == 200

    # Void the now-SKIPPED task A
    _void_task(client, tid_a)

    # Attempt swap: voided SKIPPED + live PLANNED
    r = client.post(
        "/v1/tasks/swap",
        json={"task_a_id": tid_a, "task_b_id": tid_b},
        headers=_H,
    )
    assert r.status_code == 400
    assert "voided" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 3. reschedule rejects voided task
# ---------------------------------------------------------------------------

@needs_redis
def test_reschedule_rejects_voided(client):
    tid = _create_task(client)
    _void_task(client, tid)
    new_start, new_end = _future(120, 60)
    r = client.post(
        "/v1/reschedule",
        json={"task_id": tid, "new_start": new_start, "new_end": new_end},
        headers=_H,
    )
    assert r.status_code == 400
    assert "voided" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 4. complete_task rejects voided task (service layer)
# ---------------------------------------------------------------------------

def test_complete_task_rejects_voided(db):
    from app.services.task_manager import TaskManager

    set_current_user_id(USER_ID)
    now = now_utc()
    tid = str(uuid4())
    task = Task(
        task_id=tid,
        title="complete-test",
        user_id=USER_ID,
        planned_start_utc=now - timedelta(hours=2),
        planned_end_utc=now - timedelta(hours=1),
        planned_duration_minutes=60,
        state="EXECUTING",
        source="manual",
        created_at=now,
        last_modified_at=now,
        voided_at=now - timedelta(minutes=5),
        voided_reason="test_contamination",
    )
    db.add(task)
    db.commit()

    manager = TaskManager(db)
    with pytest.raises(ValueError, match="voided"):
        manager.complete_task(tid, now - timedelta(minutes=30), now)


# ---------------------------------------------------------------------------
# 5. stopwatch start rejects voided task
# ---------------------------------------------------------------------------

@needs_redis
def test_stopwatch_start_rejects_voided(client):
    tid = _create_task(client)
    _void_task(client, tid)
    r = client.post(
        "/v1/stopwatch/start",
        json={"task_id": tid},
        headers=_H,
    )
    assert r.status_code == 400
    assert "voided" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 6. stopwatch stop auto-closes when task voided mid-session
# ---------------------------------------------------------------------------

@needs_redis
def test_stopwatch_stop_voided_mid_session(client, db):
    """Start timer, void task in DB, then stop — self-heal cleans up + returns 400."""
    from app.utils.redis_client import RedisClient

    tid = _create_task(client)

    # Start timer
    r = client.post("/v1/stopwatch/start", json={"task_id": tid}, headers=_H)
    assert r.status_code == 200
    session_id = r.json()["session_id"]

    # Void the task directly in DB (bypass API so Redis isn't cleaned up yet)
    set_current_user_id(USER_ID)
    s = TestingSession()
    try:
        s.execute(
            text("UPDATE task SET voided_at = :now, voided_reason = 'test_contamination' WHERE task_id = :tid"),
            {"now": datetime.utcnow(), "tid": tid},
        )
        s.commit()
    finally:
        s.close()

    # Attempt to stop — _get_active self-heal detects voided task,
    # closes orphan session, clears Redis, then returns 400.
    r = client.post("/v1/stopwatch/stop", json={}, headers=_H)
    assert r.status_code == 400

    # Redis cleaned up by self-heal
    rc = RedisClient()
    assert rc.get_active_stopwatch(str(USER_ID)) is None

    # Session auto-closed by self-heal
    s2 = TestingSession()
    try:
        set_current_user_id(USER_ID)
        sess = s2.query(StopwatchSession).filter(
            StopwatchSession.session_id == session_id
        ).first()
        assert sess is not None
        assert sess.end_time_utc is not None
        assert sess.auto_closed is True
    finally:
        s2.close()


# ---------------------------------------------------------------------------
# 7. update-completion rejects voided task
# ---------------------------------------------------------------------------

@needs_redis
def test_update_completion_rejects_voided(client, db):
    """Start timer, void task in DB, then update-completion — self-heal blocks it."""
    tid = _create_task(client)

    r = client.post("/v1/stopwatch/start", json={"task_id": tid}, headers=_H)
    assert r.status_code == 200

    # Void the task directly in DB (bypass API so Redis isn't cleaned up yet)
    set_current_user_id(USER_ID)
    s = TestingSession()
    try:
        s.execute(
            text("UPDATE task SET voided_at = :now, voided_reason = 'test_contamination' WHERE task_id = :tid"),
            {"now": datetime.utcnow(), "tid": tid},
        )
        s.commit()
    finally:
        s.close()

    # update-completion calls _get_active which self-heals voided tasks → 400
    r = client.post(
        "/v1/stopwatch/update-completion",
        json={"task_completion_percentage": 75},
        headers=_H,
    )
    assert r.status_code == 400
