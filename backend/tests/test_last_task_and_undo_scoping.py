"""Regression tests: /tasks/last filters voided + undo cache per-user scoped.

Covers the fixes from voided_at audit commit 3:
  1. GET /tasks/last returns 404 for voided tasks
  2. Undo Redis keys are namespaced per-user (undo:{user_id}:{entity_id})
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import text

from app.db.models import Task, User
from app.db.scoping import set_current_user_id
from tests.conftest import TestingSession

USER_A = 902
USER_B = 903
_HA = {"X-User-Id": str(USER_A)}
_HB = {"X-User-Id": str(USER_B)}


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
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM stopwatch_session"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM user"))
    db.commit()

    seed = TestingSession()
    try:
        now = datetime.utcnow()
        seed.add_all([
            User(user_id=USER_A, email="user-a@test", is_operator=True, notion_enabled=False, created_at=now),
            User(user_id=USER_B, email="user-b@test", is_operator=False, notion_enabled=False, created_at=now),
        ])
        seed.commit()
    finally:
        seed.close()
    db.rollback()
    db.expire_all()

    try:
        from app.utils.redis_client import RedisClient
        rc = RedisClient()
        for uid in (str(USER_A), str(USER_B)):
            rc.clear_active_stopwatch(uid)
            rc.client.delete(f"stopwatch:paused:{uid}")
            # Clear any stale undo keys
            for k in rc.client.keys(f"undo:{uid}:*"):
                rc.client.delete(k)
            rc.client.delete(f"last_operated_task:{uid}")
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


# ---------------------------------------------------------------------------
# 1. GET /tasks/last returns 404 for voided task
# ---------------------------------------------------------------------------

@needs_redis
def test_last_task_filters_voided(client):
    """Create a task, void it, then GET /tasks/last should return 404."""
    start, end = _future(10)
    r = client.post("/v1/create", json={"title": "will-void", "start": start, "end": end}, headers=_HA)
    assert r.status_code == 200
    tid = r.json()["task_id"]

    # /tasks/last should find it
    r = client.get("/v1/tasks/last", headers=_HA)
    assert r.status_code == 200
    assert r.json()["task_id"] == tid

    # Void it
    r = client.post(f"/v1/tasks/{tid}/void", json={"voided_reason": "test_contamination"}, headers=_HA)
    assert r.status_code == 200

    # Now /tasks/last should 404
    r = client.get("/v1/tasks/last", headers=_HA)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 2. Undo cache is per-user scoped
# ---------------------------------------------------------------------------

@needs_redis
def test_undo_per_user_isolated(client):
    """User A creates a task — user B cannot undo it."""
    start_a, end_a = _future(10)
    r = client.post("/v1/create", json={"title": "A-task", "start": start_a, "end": end_a}, headers=_HA)
    assert r.status_code == 200
    tid_a = r.json()["task_id"]

    # User A can undo (within 30s window)
    r = client.post("/v1/undo", headers=_HA)
    assert r.status_code == 200
    assert r.json()["action_undone"] == "create_task"

    # Create another task as A
    start_a2, end_a2 = _future(80)
    r = client.post("/v1/create", json={"title": "A-task-2", "start": start_a2, "end": end_a2}, headers=_HA)
    assert r.status_code == 200

    # User B should NOT see A's undo
    r = client.post("/v1/undo", headers=_HB)
    assert r.status_code == 400
    assert "nothing to undo" in r.json()["detail"].lower()


@needs_redis
def test_undo_does_not_cross_users(client):
    """Both users create tasks — each can only undo their own."""
    start_a, end_a = _future(10)
    start_b, end_b = _future(80)

    r = client.post("/v1/create", json={"title": "A-owns", "start": start_a, "end": end_a}, headers=_HA)
    assert r.status_code == 200
    tid_a = r.json()["task_id"]

    r = client.post("/v1/create", json={"title": "B-owns", "start": start_b, "end": end_b}, headers=_HB)
    assert r.status_code == 200
    tid_b = r.json()["task_id"]

    # B undoes B's task
    r = client.post("/v1/undo", headers=_HB)
    assert r.status_code == 200
    assert "B-owns" in r.json()["message"]

    # A undoes A's task
    r = client.post("/v1/undo", headers=_HA)
    assert r.status_code == 200
    assert "A-owns" in r.json()["message"]
