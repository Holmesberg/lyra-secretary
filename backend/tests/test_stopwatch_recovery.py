"""LYR-095 regression: get_status must recover from Redis loss.

StopwatchManager.get_status() previously called
redis.get_active_stopwatch() directly, skipping the
_recover_from_db() fallback. If Redis lost the key (restart,
eviction), the endpoint returned active=false even though an
unclosed session existed in SQLite — the active-timer banner
disappeared.

The fix: get_status() now calls _get_active(), which falls
through to _recover_from_db() when Redis returns None.
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
def stopwatch_user(db):
    """Seed a single user and wipe state for stopwatch tests."""
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
            user_id=77, email="sw-test@x",
            is_operator=False, notion_enabled=False, created_at=now,
        ))
        seed.commit()
    finally:
        seed.close()

    yield db
    set_current_user_id(None)


def _h(uid: int = 77) -> dict:
    return {"X-User-Id": str(uid)}


def _future(minutes: int = 10, duration: int = 60):
    start = datetime.utcnow() + timedelta(minutes=minutes)
    end = start + timedelta(minutes=duration)
    s = start.replace(microsecond=0).isoformat() + "Z"
    e = end.replace(microsecond=0).isoformat() + "Z"
    return s, e


@needs_redis
def test_get_status_recovers_after_redis_key_loss(stopwatch_user, client):
    """Start a timer, delete the Redis key, call status → must recover."""
    # Create and start a task
    start, end = _future(10, 60)
    r = client.post(
        "/v1/create",
        json={"title": "recovery test", "start": start, "end": end},
        headers=_h(),
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["task_id"]

    r = client.post(
        "/v1/stopwatch/start",
        json={"task_id": task_id, "pre_task_readiness": 3},
        headers=_h(),
    )
    assert r.status_code == 200, r.text

    # Verify status is active
    r = client.get("/v1/stopwatch/status", headers=_h())
    assert r.status_code == 200
    assert r.json()["active"] is True

    # Simulate Redis key loss (restart / eviction)
    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    rc.clear_active_stopwatch("77")

    # Status must still recover from SQLite
    r = client.get("/v1/stopwatch/status", headers=_h())
    assert r.status_code == 200
    body = r.json()
    assert body["active"] is True, (
        f"LYR-095 regression: get_status returned active=false after Redis key loss. "
        f"Response: {body}"
    )
    assert body["task_id"] == task_id

    # Cleanup: stop the timer so it doesn't leak into other tests
    r = client.post(
        "/v1/stopwatch/stop?confirmed=true",
        json={"post_task_reflection": 3},
        headers=_h(),
    )
    assert r.status_code == 200, r.text
