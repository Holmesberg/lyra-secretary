"""Stopwatch start: friendly 400 on invalid state transitions.

Previously, starting a timer on a SKIPPED or EXECUTED task returned a
raw 500 with "Cannot transition from SKIPPED to EXECUTING". Now it
returns a structured 400 with a user-friendly message.
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
def start_err_user(db):
    try:
        from app.utils.redis_client import RedisClient
        rc = RedisClient()
        for uid in ("1", "88", "user_primary"):
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
            user_id=88, email="start-err@x",
            is_operator=False, notion_enabled=False, created_at=now,
        ))
        seed.commit()
    finally:
        seed.close()

    yield db
    set_current_user_id(None)


def _h(uid: int = 88) -> dict:
    return {"X-User-Id": str(uid)}


@needs_redis
def test_start_skipped_task_returns_friendly_400(start_err_user, client):
    """Starting a SKIPPED task must return 400 with structured error, not 500."""
    start = datetime.utcnow() + timedelta(minutes=10)
    end = start + timedelta(minutes=30)
    s = start.replace(microsecond=0).isoformat() + "Z"
    e = end.replace(microsecond=0).isoformat() + "Z"

    # Create a task
    r = client.post(
        "/v1/create",
        json={"title": "skip-then-start", "start": s, "end": e},
        headers=_h(),
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["task_id"]

    # Skip the task
    r = client.post(
        f"/v1/tasks/{task_id}/mark-abandoned",
        json={"reason": "test skip"},
        headers=_h(),
    )
    assert r.status_code == 200, r.text

    # Try to start the skipped task
    r = client.post(
        "/v1/stopwatch/start",
        json={"task_id": task_id, "pre_task_readiness": 3},
        headers=_h(),
    )
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    body = r.json()
    detail = body.get("detail", {})
    assert isinstance(detail, dict), f"Expected structured detail, got: {detail}"
    assert detail.get("error") == "invalid_state_transition"
    assert "no longer startable" in detail.get("message", "")
