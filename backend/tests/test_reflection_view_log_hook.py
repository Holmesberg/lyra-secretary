"""LYR-098 Commit 2b: reflection_view_log write-on-fire + callback tests.

Covers:
- `POST /v1/stopwatch/stop` writes a reflection_view_log row for each
  non-None signal (micro_mirror / calibration_nudge) and returns the
  row ids on the response (`micro_mirror_view_id` /
  `calibration_nudge_view_id`).
- `POST /v1/reflection_view/{view_id}/viewed` stamps `viewed_at`
  (first-wins / idempotent).
- `POST /v1/reflection_view/{view_id}/dismissed` stamps `dismissed_at`
  and computes `dwell_seconds` when a prior `viewed_at` exists.
- Unknown `view_id` → 404 on both callbacks.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.db.models import (
    ExposureAckEvent,
    ExposureDecisionEvent,
    ExposureRenderEvent,
    ReflectionViewLog,
    Task,
    TaskState,
    User,
)
from app.db.scoping import set_current_user_id
from app.utils.time_utils import now_utc
from tests.conftest import TestingSession


USER_ID = 902


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
def refl_env(db):
    """Fresh env: wipe Redis + DB tables, seed one user."""
    try:
        from app.utils.redis_client import RedisClient
        rc = RedisClient()
        for uid in ("1", str(USER_ID), "user_primary"):
            rc.clear_active_stopwatch(uid)
            rc.client.delete(f"stopwatch:paused:{uid}")
    except Exception:
        pass

    set_current_user_id(None)
    wipe = TestingSession()
    try:
        wipe.execute(text("DELETE FROM reflection_view_log"))
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
            user_id=USER_ID, email="refl-log-hook@test",
            is_operator=False, notion_enabled=False,
            created_at=datetime.utcnow(),
        ))
        seed.commit()
    finally:
        seed.close()

    yield db
    set_current_user_id(None)


def _h():
    return {"X-User-Id": str(USER_ID)}


def _iso_future(minutes: int, duration: int = 30):
    start = datetime.utcnow() + timedelta(minutes=minutes)
    end = start + timedelta(minutes=duration)
    return (
        start.replace(microsecond=0).isoformat() + "Z",
        end.replace(microsecond=0).isoformat() + "Z",
    )


def _ack_stop_surface(client, body: dict, key: str, surface_id: str) -> None:
    exposure_id = body[f"{key}_exposure_id"]
    response = client.post(
        f"/v1/exposures/{exposure_id}/ack/render",
        headers=_h(),
        json={
            "surface_id": surface_id,
            "client_event_id": f"{surface_id}:{exposure_id}",
            "content_snapshot": {"message": body[key]},
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["created"] is True
    viewed = client.post(
        f"/v1/reflection_view/{body[f'{key}_view_id']}/viewed",
        headers=_h(),
    )
    assert viewed.status_code == 200, viewed.text


def _seed_dev_history(n: int = 3, delta: int = -15) -> None:
    """Seed n EXECUTED 'dev' tasks so calibration_nudge fires on next stop."""
    s = TestingSession()
    try:
        planned = 60
        executed = planned - delta
        for i in range(n):
            start = datetime.utcnow() - timedelta(days=1, minutes=i * 5)
            t = Task(
                title=f"history-{i}",
                planned_start_utc=start,
                planned_end_utc=start + timedelta(minutes=planned),
                planned_duration_minutes=planned,
                executed_start_utc=start,
                executed_end_utc=start + timedelta(minutes=executed),
                executed_duration_minutes=executed,
                state=TaskState.EXECUTED,
                category="dev",
                initiation_status="initiated",
                user_id=USER_ID,
            )
            s.add(t)
        s.commit()
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Write-on-fire hook (through the real /stopwatch/stop endpoint)
# ---------------------------------------------------------------------------

@needs_redis
def test_hook_writes_micro_mirror_row_on_stop(refl_env, client):
    """A future-planned task started now → delay < 0 → micro_mirror
    "Started on time." fires → 1 reflection_view_log row."""
    start, end = _iso_future(10, 30)
    r = client.post("/v1/create", json={"title": "t", "start": start, "end": end}, headers=_h())
    assert r.status_code == 200, r.text
    task_id = r.json()["task_id"]

    r = client.post(
        "/v1/stopwatch/start",
        json={"task_id": task_id, "pre_task_readiness": 3},
        headers=_h(),
    )
    assert r.status_code == 200, r.text

    r = client.post(
        "/v1/stopwatch/stop?confirmed=true",
        json={"post_task_reflection": 3, "task_completion_percentage": 90},
        headers=_h(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["micro_mirror"] == "Started on time."
    assert body["micro_mirror_view_id"] is not None
    assert body["micro_mirror_exposure_id"] is not None
    assert body["calibration_nudge_view_id"] is None  # no history seeded

    check = TestingSession()
    try:
        rows = check.query(ReflectionViewLog).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.view_id == body["micro_mirror_view_id"]
        assert row.user_id == USER_ID
        assert row.reflection_type == "micro_mirror"
        assert row.task_id == task_id
        assert row.payload == "Started on time."
        assert row.viewed_at is None
        assert row.dismissed_at is None
        assert row.dwell_seconds is None
        decision = (
            check.query(ExposureDecisionEvent)
            .filter(
                ExposureDecisionEvent.exposure_id
                == body["micro_mirror_exposure_id"]
            )
            .one()
        )
        assert decision.decision_status == "reserved"
        assert decision.delivered_at is None
        assert check.query(ExposureRenderEvent).count() == 0
        assert check.query(ExposureAckEvent).count() == 0
    finally:
        check.close()

    _ack_stop_surface(
        client,
        body,
        "micro_mirror",
        "stopwatch.micro_mirror",
    )
    verify = TestingSession()
    try:
        decision = (
            verify.query(ExposureDecisionEvent)
            .filter(
                ExposureDecisionEvent.exposure_id
                == body["micro_mirror_exposure_id"]
            )
            .one()
        )
        row = verify.query(ReflectionViewLog).one()
        assert decision.decision_status == "rendered"
        assert decision.delivered_at is not None
        assert verify.query(ExposureRenderEvent).count() == 1
        assert verify.query(ExposureAckEvent).count() == 1
        assert row.viewed_at is not None
    finally:
        verify.close()


@needs_redis
def test_hook_writes_both_rows_when_both_signals_fire(refl_env, client):
    """Seed dev history + stop a new dev task → micro_mirror AND
    calibration_nudge both fire → 2 rows written; both view_ids returned."""
    _seed_dev_history(n=3, delta=-15)

    start, end = _iso_future(10, 30)
    r = client.post(
        "/v1/create",
        json={"title": "t", "start": start, "end": end, "category": "dev"},
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
        "/v1/stopwatch/stop?confirmed=true",
        json={"post_task_reflection": 3, "task_completion_percentage": 90},
        headers=_h(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["micro_mirror"] is not None
    assert body["calibration_nudge"] is not None
    assert body["micro_mirror_view_id"] is not None
    assert body["calibration_nudge_view_id"] is not None
    assert body["micro_mirror_exposure_id"] is not None
    assert body["calibration_nudge_exposure_id"] is not None
    assert body["micro_mirror_view_id"] != body["calibration_nudge_view_id"]

    check = TestingSession()
    try:
        rows = {
            r.reflection_type: r
            for r in check.query(ReflectionViewLog).all()
        }
        assert set(rows.keys()) == {"micro_mirror", "calibration_nudge"}
        assert rows["micro_mirror"].view_id == body["micro_mirror_view_id"]
        assert rows["calibration_nudge"].view_id == body["calibration_nudge_view_id"]
        assert rows["micro_mirror"].payload == body["micro_mirror"]
        assert rows["calibration_nudge"].payload == body["calibration_nudge"]
        for row in rows.values():
            assert row.user_id == USER_ID
            assert row.task_id == task_id
            assert row.viewed_at is None
        exposure_ids = {
            body["micro_mirror_exposure_id"],
            body["calibration_nudge_exposure_id"],
        }
        decisions = (
            check.query(ExposureDecisionEvent)
            .filter(ExposureDecisionEvent.exposure_id.in_(exposure_ids))
            .all()
        )
        assert len(decisions) == 2
        assert {row.decision_status for row in decisions} == {"reserved"}
        assert (
            check.query(ExposureRenderEvent)
            .filter(ExposureRenderEvent.exposure_id.in_(exposure_ids))
            .count()
            == 0
        )
        assert (
            check.query(ExposureAckEvent)
            .filter(ExposureAckEvent.exposure_id.in_(exposure_ids))
            .count()
            == 0
        )
    finally:
        check.close()

    _ack_stop_surface(
        client,
        body,
        "micro_mirror",
        "stopwatch.micro_mirror",
    )
    _ack_stop_surface(
        client,
        body,
        "calibration_nudge",
        "stopwatch.calibration_nudge",
    )
    verify = TestingSession()
    try:
        exposure_ids = {
            body["micro_mirror_exposure_id"],
            body["calibration_nudge_exposure_id"],
        }
        decisions = (
            verify.query(ExposureDecisionEvent)
            .filter(ExposureDecisionEvent.exposure_id.in_(exposure_ids))
            .all()
        )
        assert len(decisions) == 2
        assert {row.decision_status for row in decisions} == {"rendered"}
        assert (
            verify.query(ExposureRenderEvent)
            .filter(ExposureRenderEvent.exposure_id.in_(exposure_ids))
            .count()
            == 2
        )
        assert (
            verify.query(ExposureAckEvent)
            .filter(ExposureAckEvent.exposure_id.in_(exposure_ids))
            .count()
            == 2
        )
        assert all(
            row.viewed_at is not None
            for row in verify.query(ReflectionViewLog).all()
        )
    finally:
        verify.close()


# ---------------------------------------------------------------------------
# Callback endpoints — viewed / dismissed
# ---------------------------------------------------------------------------

def _direct_seed_row(view_id: str, reflection_type: str = "micro_mirror",
                     viewed_at=None, fired_offset_seconds: int = 0) -> None:
    """Insert a reflection_view_log row directly (bypass stop endpoint)."""
    s = TestingSession()
    try:
        row = ReflectionViewLog(
            view_id=view_id,
            user_id=USER_ID,
            reflection_type=reflection_type,
            task_id=None,
            payload="test payload",
            fired_at=now_utc() - timedelta(seconds=fired_offset_seconds),
            viewed_at=viewed_at,
        )
        s.add(row)
        s.commit()
    finally:
        s.close()


def test_viewed_endpoint_stamps_viewed_at(refl_env, client):
    _direct_seed_row("view-001")
    r = client.post("/v1/reflection_view/view-001/viewed", headers=_h())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["viewed"] is True
    assert body["viewed_at"] is not None


def test_viewed_endpoint_idempotent(refl_env, client):
    _direct_seed_row("view-002")
    r1 = client.post("/v1/reflection_view/view-002/viewed", headers=_h())
    assert r1.status_code == 200
    first = r1.json()["viewed_at"]
    r2 = client.post("/v1/reflection_view/view-002/viewed", headers=_h())
    assert r2.status_code == 200
    assert r2.json()["viewed_at"] == first


def test_dismissed_endpoint_computes_dwell_when_viewed_at_set(refl_env, client):
    """Row already has viewed_at from 3 seconds ago → dismiss now → dwell ≈ 3."""
    viewed = now_utc() - timedelta(seconds=3)
    _direct_seed_row("view-003", viewed_at=viewed, fired_offset_seconds=5)

    r = client.post("/v1/reflection_view/view-003/dismissed", headers=_h())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dismissed"] is True
    assert body["dismissed_at"] is not None
    assert body["dwell_seconds"] is not None
    # Timing tolerance — between 2 and 5 seconds.
    assert 2 <= body["dwell_seconds"] <= 5


def test_dismissed_endpoint_no_dwell_without_prior_viewed(refl_env, client):
    _direct_seed_row("view-004")
    r = client.post("/v1/reflection_view/view-004/dismissed", headers=_h())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dismissed_at"] is not None
    assert body["dwell_seconds"] is None


def test_dismissed_endpoint_idempotent(refl_env, client):
    _direct_seed_row("view-005")
    r1 = client.post("/v1/reflection_view/view-005/dismissed", headers=_h())
    assert r1.status_code == 200
    first = r1.json()["dismissed_at"]
    r2 = client.post("/v1/reflection_view/view-005/dismissed", headers=_h())
    assert r2.status_code == 200
    assert r2.json()["dismissed_at"] == first


def test_viewed_404_on_unknown_view_id(refl_env, client):
    r = client.post("/v1/reflection_view/nonexistent/viewed", headers=_h())
    assert r.status_code == 404


def test_dismissed_404_on_unknown_view_id(refl_env, client):
    r = client.post("/v1/reflection_view/nonexistent/dismissed", headers=_h())
    assert r.status_code == 404
