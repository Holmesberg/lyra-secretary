"""Regression: get_status must expose the current pause start time.

Operator report 2026-04-26: "electronics paused early but counting from
00:00 when I stopped the parallel task." Root cause: get_status returned
`paused: true` and `total_paused_minutes: 0` (correct — current pause
hasn't ended yet) but did NOT expose when the current pause began. The
frontend banner therefore initialized its pause counter to Date.now()
on every remount / multi-task swap, displaying "paused · 00:00" instead
of the actual pause duration. Active-work elapsed was always correct;
only the paused-duration display was broken.

Fix: get_status now returns:
  - current_pause_seconds (server-computed delta from paused_at to now)
  - current_pause_started_at (ISO timestamp; mirror of pause_state.paused_at)

Both are 0 / None when not paused.
"""
from datetime import datetime, timedelta
import time

import pytest
from sqlalchemy import text

from app.db.models import User
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
    try:
        from app.utils.redis_client import RedisClient
        rc = RedisClient()
        for uid in ("1", "77"):
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

    seed = TestingSession()
    try:
        seed.add(User(
            user_id=77, email="pause-anchor@x",
            is_operator=False, notion_enabled=False,
            created_at=datetime.utcnow(),
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
    return start.replace(microsecond=0).isoformat() + "Z", end.replace(microsecond=0).isoformat() + "Z"


@needs_redis
def test_status_exposes_current_pause_anchor_when_paused(stopwatch_user, client):
    """When paused, get_status returns current_pause_seconds + current_pause_started_at."""
    start, end = _future(10, 60)
    r = client.post(
        "/v1/create",
        json={"title": "pause anchor test", "start": start, "end": end},
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

    r = client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "intentional_break", "pause_initiator": "self"},
        headers=_h(),
    )
    assert r.status_code == 200, r.text

    # Wait so current_pause_seconds has a non-zero value to assert against
    # 2.5s instead of 2.1 — under suite load the wall-clock can compress
    # below 2s and the >=2 assertion below would flake.
    time.sleep(2.5)

    r = client.get("/v1/stopwatch/status", headers=_h())
    assert r.status_code == 200
    body = r.json()
    assert body["paused"] is True
    assert body["current_pause_seconds"] >= 2, (
        f"Expected current_pause_seconds ≥ 2 after sleeping 2.1s, "
        f"got {body.get('current_pause_seconds')}. Full response: {body}"
    )
    assert body["current_pause_started_at"] is not None
    # ISO format parseable
    parsed = datetime.fromisoformat(body["current_pause_started_at"])
    delta = (datetime.utcnow() - parsed).total_seconds()
    assert 1 <= delta <= 30, f"current_pause_started_at delta out of range: {delta}s"

    # Cleanup
    client.post(
        "/v1/stopwatch/stop?confirmed=true",
        json={"post_task_reflection": 3},
        headers=_h(),
    )


@needs_redis
def test_status_pause_anchor_zero_when_not_paused(stopwatch_user, client):
    """Active but unpaused → current_pause_seconds=0, current_pause_started_at=None."""
    start, end = _future(10, 60)
    r = client.post(
        "/v1/create",
        json={"title": "unpaused test", "start": start, "end": end},
        headers=_h(),
    )
    task_id = r.json()["task_id"]

    client.post(
        "/v1/stopwatch/start",
        json={"task_id": task_id, "pre_task_readiness": 3},
        headers=_h(),
    )

    r = client.get("/v1/stopwatch/status", headers=_h())
    body = r.json()
    assert body["paused"] is False
    assert body["current_pause_seconds"] == 0
    assert body["current_pause_started_at"] is None

    # Cleanup
    client.post(
        "/v1/stopwatch/stop?confirmed=true",
        json={"post_task_reflection": 3},
        headers=_h(),
    )


@needs_redis
def test_status_pause_anchor_survives_recovery(stopwatch_user, client):
    """Even after Redis key loss + recovery from DB, current_pause_seconds is correct.

    Mirrors the LYR-095 recovery scenario: pause_state regenerated from
    session.paused_at_utc, so current_pause_seconds should reflect the
    ORIGINAL pause start, not the recovery moment.
    """
    start, end = _future(10, 60)
    r = client.post(
        "/v1/create",
        json={"title": "recovery anchor test", "start": start, "end": end},
        headers=_h(),
    )
    task_id = r.json()["task_id"]
    client.post(
        "/v1/stopwatch/start",
        json={"task_id": task_id, "pre_task_readiness": 3},
        headers=_h(),
    )
    pr = client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "intentional_break", "pause_initiator": "self"},
        headers=_h(),
    )
    assert pr.status_code == 200, pr.text

    # 2.5s instead of 2.1 — under suite load the wall-clock can compress
    # below 2s and the >=2 assertion below would flake.
    time.sleep(2.5)

    # Simulate Redis loss
    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    rc.clear_active_stopwatch("77")
    rc.client.delete("stopwatch:paused:77")

    # Recovery should re-populate Redis from session.paused_at_utc
    r = client.get("/v1/stopwatch/status", headers=_h())
    body = r.json()
    assert body["active"] is True, f"Recovery failed: {body}"
    assert body["paused"] is True, f"pause_state not rehydrated by recovery: {body}"
    # Counter should reflect the ORIGINAL pause time, not "0 seconds since recovery"
    assert body["current_pause_seconds"] >= 2, (
        f"After recovery, pause counter must reflect original pause start. "
        f"Got current_pause_seconds={body.get('current_pause_seconds')}. "
        f"Full response: {body}"
    )

    client.post(
        "/v1/stopwatch/stop?confirmed=true",
        json={"post_task_reflection": 3},
        headers=_h(),
    )
