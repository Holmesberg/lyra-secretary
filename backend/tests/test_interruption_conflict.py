"""Interruption flow: conflict response includes PAUSED state for frontend detection.

Test case 1: single paused conflict → conflicts array has state="PAUSED"
Test case 2: mixed paused + planned → both appear with correct states

The frontend uses these state values to decide whether to show the
interruption offer (PAUSED) or the generic conflict error (PLANNED/EXECUTING).
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.db.models import Task, TaskState, User
from app.db.scoping import set_current_user_id
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
def interrupt_user(db):
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
        wipe.execute(text("DELETE FROM stopwatch_session"))
        wipe.execute(text("DELETE FROM task"))
        wipe.execute(text("DELETE FROM user"))
        wipe.commit()
    finally:
        wipe.close()

    db.rollback()
    db.expire_all()
    now = datetime.utcnow()
    seed = TestingSession()
    try:
        seed.add(User(
            user_id=66, email="interrupt@x",
            is_operator=False, notion_enabled=False, created_at=now,
        ))
        seed.commit()
    finally:
        seed.close()

    yield db
    set_current_user_id(None)


def _h(uid: int = 66) -> dict:
    return {"X-User-Id": str(uid)}


def _future(minutes: int, duration: int = 30):
    start = datetime.utcnow() + timedelta(minutes=minutes)
    end = start + timedelta(minutes=duration)
    s = start.replace(microsecond=0).isoformat() + "Z"
    e = end.replace(microsecond=0).isoformat() + "Z"
    return s, e


@needs_redis
def test_single_paused_conflict_returns_paused_state(interrupt_user, client):
    """Create overlapping a single PAUSED task → conflict state is 'PAUSED'."""
    # Create and start task A at +10min
    s, e = _future(10, 60)
    r = client.post("/v1/create", json={"title": "deep work A", "start": s, "end": e}, headers=_h())
    assert r.status_code == 200
    tid_a = r.json()["task_id"]

    # Start and pause task A
    r = client.post("/v1/stopwatch/start", json={"task_id": tid_a, "pre_task_readiness": 3}, headers=_h())
    assert r.status_code == 200
    r = client.post("/v1/stopwatch/pause", json={}, headers=_h())
    assert r.status_code == 200

    # Try to create task B overlapping A's time slot
    r = client.post("/v1/create", json={"title": "interrupting B", "start": s, "end": e}, headers=_h())
    assert r.status_code == 200
    body = r.json()
    assert body["created"] is False
    assert len(body["conflicts"]) == 1
    assert body["conflicts"][0]["state"] == "PAUSED"
    assert body["conflicts"][0]["task_id"] == tid_a

    # Cleanup
    r = client.post("/v1/stopwatch/stop?confirmed=true", json={"post_task_reflection": 3}, headers=_h())
    assert r.status_code == 200


@needs_redis
def test_mixed_paused_and_planned_conflicts(interrupt_user, client):
    """Overlap with both a PAUSED and a PLANNED task → both appear in conflicts."""
    # Create task A at +10min (60 min)
    s_a, e_a = _future(10, 60)
    r = client.post("/v1/create", json={"title": "deep work A", "start": s_a, "end": e_a}, headers=_h())
    assert r.status_code == 200
    tid_a = r.json()["task_id"]

    # Create task B at +40min (30 min) — overlaps A's second half
    s_b, e_b = _future(40, 30)
    r = client.post("/v1/create", json={"title": "planned B", "start": s_b, "end": e_b, "force": True}, headers=_h())
    assert r.status_code == 200
    tid_b = r.json()["task_id"]

    # Start and pause task A
    r = client.post("/v1/stopwatch/start", json={"task_id": tid_a, "pre_task_readiness": 3}, headers=_h())
    assert r.status_code == 200
    r = client.post("/v1/stopwatch/pause", json={}, headers=_h())
    assert r.status_code == 200

    # Try to create task C overlapping both A (PAUSED) and B (PLANNED)
    s_c, e_c = _future(20, 40)  # overlaps A from +20 to +60, B from +40 to +60
    r = client.post("/v1/create", json={"title": "mixed conflict C", "start": s_c, "end": e_c}, headers=_h())
    assert r.status_code == 200
    body = r.json()
    assert body["created"] is False
    assert len(body["conflicts"]) == 2

    states = {c["state"] for c in body["conflicts"]}
    assert "PAUSED" in states, f"Expected PAUSED in conflicts, got {states}"
    assert "PLANNED" in states, f"Expected PLANNED in conflicts, got {states}"

    # Cleanup
    r = client.post("/v1/stopwatch/stop?confirmed=true", json={"post_task_reflection": 3}, headers=_h())
    assert r.status_code == 200
