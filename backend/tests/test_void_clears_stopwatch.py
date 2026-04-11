"""Regression: voiding a task must clear the stopwatch banner.

The CO-block incident (Apr 11, 2026): operator voided a PAUSED task via
OpenClaw. The void succeeded, voided_at was stamped, but the frontend
kept showing 'PAUSED · CO block 65:09:22' indefinitely because:

1. /v1/tasks/{id}/void did not close the unclosed StopwatchSession
2. /v1/tasks/{id}/void did not clear the Redis stopwatch:active key
3. /v1/stopwatch/status returned the orphan session on every poll

Fix: void_task calls StopwatchManager.void_cleanup() which closes the
session and clears Redis. Plus a defensive self-heal in _get_active
that detects task.voided_at and cleans up on the next poll — this
recovers historic stale state that predates void_cleanup.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.db.models import StopwatchSession, User
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
def void_user(db):
    try:
        from app.utils.redis_client import RedisClient
        rc = RedisClient()
        for uid in ("1", "78", "user_primary"):
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
            user_id=78, email="void-test@x",
            is_operator=False, notion_enabled=False, created_at=now,
        ))
        seed.commit()
    finally:
        seed.close()

    yield db
    set_current_user_id(None)


def _h(uid: int = 78) -> dict:
    return {"X-User-Id": str(uid)}


def _future(minutes: int = 10, duration: int = 60):
    start = datetime.utcnow() + timedelta(minutes=minutes)
    end = start + timedelta(minutes=duration)
    s = start.replace(microsecond=0).isoformat() + "Z"
    e = end.replace(microsecond=0).isoformat() + "Z"
    return s, e


@needs_redis
def test_void_paused_task_clears_stopwatch_banner(void_user, client):
    """Void a PAUSED task → /stopwatch/status must return active=false."""
    start, end = _future(10, 60)
    r = client.post(
        "/v1/create",
        json={"title": "CO block regression", "start": start, "end": end},
        headers=_h(),
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["task_id"]

    # Start → pause (mirrors the CO-block sequence).
    r = client.post(
        "/v1/stopwatch/start",
        json={"task_id": task_id, "pre_task_readiness": 3},
        headers=_h(),
    )
    assert r.status_code == 200, r.text

    r = client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "intentional_break", "pause_initiator": "self"},
        headers=_h(),
    )
    assert r.status_code == 200, r.text

    # Sanity: banner is showing PAUSED before the void.
    r = client.get("/v1/stopwatch/status", headers=_h())
    assert r.status_code == 200
    assert r.json()["active"] is True
    assert r.json()["paused"] is True

    # Void.
    r = client.post(
        f"/v1/tasks/{task_id}/void",
        json={"voided_reason": "system_error"},
        headers=_h(),
    )
    assert r.status_code == 200, r.text
    assert r.json()["voided"] is True

    # The banner must clear immediately — the void endpoint itself
    # cleaned up Redis + closed the session (no self-heal needed).
    r = client.get("/v1/stopwatch/status", headers=_h())
    assert r.status_code == 200
    body = r.json()
    # get_status returns either {active: False} or None → FastAPI may
    # serialize both as a JSON object. The invariant: there is no
    # active timer claim.
    assert body.get("active") is not True, (
        f"CO-block regression: /stopwatch/status still reports an active "
        f"timer after voiding the bound task. Response: {body}"
    )

    # Redis keys must be gone.
    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    assert rc.get_active_stopwatch("78") is None
    assert rc.get_pause_state("78") is None

    # The StopwatchSession must have end_time_utc set and paused_at cleared.
    check = TestingSession()
    try:
        sessions = check.query(StopwatchSession).filter(
            StopwatchSession.task_id == task_id
        ).all()
        assert len(sessions) == 1
        assert sessions[0].end_time_utc is not None, (
            "void_cleanup must close the orphan StopwatchSession."
        )
        assert sessions[0].auto_closed is True
        assert sessions[0].paused_at_utc is None
    finally:
        check.close()


@needs_redis
def test_get_active_self_heals_historic_voided_task(void_user, client):
    """Simulate pre-fix stale state: task voided but Redis + session still live.

    Writes voided_at directly (bypassing the cleanup path) to mimic the
    operator's current stuck banner. Next /stopwatch/status poll must
    detect the void via _get_active self-heal and return no active.
    """
    start, end = _future(10, 60)
    r = client.post(
        "/v1/create",
        json={"title": "historic ghost", "start": start, "end": end},
        headers=_h(),
    )
    task_id = r.json()["task_id"]

    client.post(
        "/v1/stopwatch/start",
        json={"task_id": task_id, "pre_task_readiness": 3},
        headers=_h(),
    )
    client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "intentional_break", "pause_initiator": "self"},
        headers=_h(),
    )

    # Stamp voided_at directly — simulates a void that ran before
    # void_cleanup existed, or any code path that forgot to clean up.
    from datetime import datetime as _dt
    write = TestingSession()
    try:
        write.execute(
            text("UPDATE task SET voided_at = :now, voided_reason = 'system_error' WHERE task_id = :tid"),
            {"now": _dt.utcnow(), "tid": task_id},
        )
        write.commit()
    finally:
        write.close()

    # Next status poll must self-heal and report no active timer.
    r = client.get("/v1/stopwatch/status", headers=_h())
    assert r.status_code == 200
    body = r.json()
    assert body.get("active") is not True, (
        f"Self-heal failed: _get_active returned a voided task. "
        f"Response: {body}"
    )

    # And it must have cleaned up Redis + closed the session as a side effect.
    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    assert rc.get_active_stopwatch("78") is None
    assert rc.get_pause_state("78") is None
