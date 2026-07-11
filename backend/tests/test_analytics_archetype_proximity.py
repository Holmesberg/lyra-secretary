"""Tests for GET /v1/analytics/archetype/proximity + /trend.

Covers MANIFESTO Rule 17 (2026-04-27 — VT-25 dynamic-reveal endpoint).
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models import (
    Archetype,
    ExposureAckEvent,
    ExposureDecisionEvent,
    ExposureRenderEvent,
    SuppressionEvent,
    Task,
    TaskSource,
    TaskState,
    User,
)
from app.db.scoping import set_current_user_id
from app.main import app
from tests.conftest import auth_headers


client = TestClient(app, raise_server_exceptions=False)


ARCHETYPE_PRIORS = [
    ("disciplined_lark", "Disciplined Lark", 0.95, 0.15),
    ("disciplined_owl", "Disciplined Owl", 1.05, 0.20),
    ("diffuse_average", "Diffuse Average", 1.30, 0.30),
    ("procrastinator", "Procrastinator", 1.80, 0.40),
    ("lark_low_discipline", "Lark, Low Discipline", 1.50, 0.35),
]


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM suppression_event"))
    db.execute(text("DELETE FROM exposure_ack_event"))
    db.execute(text("DELETE FROM exposure_render_event"))
    db.execute(text("DELETE FROM exposure_decision_event"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM \"user\""))
    db.execute(text("DELETE FROM archetype"))
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM suppression_event"))
    db.execute(text("DELETE FROM exposure_ack_event"))
    db.execute(text("DELETE FROM exposure_render_event"))
    db.execute(text("DELETE FROM exposure_decision_event"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM \"user\""))
    db.execute(text("DELETE FROM archetype"))
    db.commit()


@pytest.fixture
def archetypes_seeded(db):
    for aid, name, bf, sigma in ARCHETYPE_PRIORS:
        db.add(Archetype(
            archetype_id=aid, name=name,
            prior_bias_factor=bf, prior_sigma=sigma,
        ))
    db.commit()


def _make_user(db, user_id: int, email: str) -> User:
    u = User(
        user_id=user_id, email=email,
        is_operator=False, notion_enabled=False,
        timezone="Africa/Cairo", created_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    return u


def _seed_executed_task(db, user_id: int, planned: int, executed: int,
                       category: str = "study", days_ago: int = 1) -> None:
    base = datetime.utcnow() - timedelta(days=days_ago)
    t = Task(
        task_id=str(uuid4()),
        title="t",
        category=category,
        planned_start_utc=base,
        planned_end_utc=base + timedelta(minutes=planned),
        planned_duration_minutes=planned,
        executed_start_utc=base,
        executed_end_utc=base + timedelta(minutes=executed),
        executed_duration_minutes=executed,
        state=TaskState.EXECUTED,
        source=TaskSource.MANUAL,
        user_id=user_id,
        initiation_status="live",
    )
    db.add(t)
    db.commit()


# ── Happy path ───────────────────────────────────────────────────


def test_proximity_returns_expected_shape(db, archetypes_seeded):
    user = _make_user(db, user_id=77, email="px1@example.com")
    set_current_user_id(user.user_id)
    _seed_executed_task(db, user.user_id, planned=30, executed=60, category="work")
    set_current_user_id(None)

    resp = client.get(
        "/v1/analytics/archetype/proximity?days=14",
        headers=auth_headers(77),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "proximity" in body
    assert "lookback_days" in body
    assert "n_tasks" in body
    assert "primary_metric" in body
    assert body["lookback_days"] == 14
    assert body["n_tasks"] == 1
    assert body["surface_id"] == "analytics.archetype_proximity"
    assert body["truth_class"] == "interpretation"
    assert body["clean_profile"] == "planning_calibration"
    assert body["eligible_sample_count"] == 1
    assert body["min_n_required"] == 3
    assert body["ready"] is False
    assert body["display_mode"] == "settling_in"
    assert body["suppressed_reason"] == "insufficient_clean_samples"
    assert len(body["proximity"]) == 5
    # Each row has the expected fields
    for row in body["proximity"]:
        assert set(row.keys()) >= {"archetype_id", "label", "score", "rank", "n_tasks"}

    decision = (
        db.query(ExposureDecisionEvent)
        .filter(
            ExposureDecisionEvent.user_id == user.user_id,
            ExposureDecisionEvent.content_template_id == "analytics_archetype_proximity",
        )
        .one()
    )
    suppression = (
        db.query(SuppressionEvent)
        .filter(SuppressionEvent.exposure_id == decision.exposure_id)
        .one()
    )
    assert decision.decision_status == "suppressed"
    assert decision.exposure_category == "meta_inference"
    assert suppression.suppression_reason == "insufficient_clean_samples"


def test_proximity_no_tasks_returns_uniform(db, archetypes_seeded):
    """Cold start: no qualifying tasks → uniform 1/5 across archetypes."""
    user = _make_user(db, user_id=78, email="px2@example.com")

    resp = client.get(
        "/v1/analytics/archetype/proximity?days=14",
        headers=auth_headers(78),
    )
    body = resp.json()
    assert body["n_tasks"] == 0
    for row in body["proximity"]:
        assert abs(row["score"] - 0.20) < 1e-9
    assert body["ready"] is False
    assert body["display_mode"] == "settling_in"
    assert body["eligible_sample_count"] == 0
    assert body["min_n_required"] == 3


def test_proximity_ready_response_waits_for_browser_render_ack(db, archetypes_seeded):
    user = _make_user(db, user_id=79, email="px-ready@example.com")
    set_current_user_id(user.user_id)
    for i in range(3):
        _seed_executed_task(
            db,
            user.user_id,
            planned=30,
            executed=60,
            category="work",
            days_ago=i + 1,
        )
    set_current_user_id(None)

    resp = client.get(
        "/v1/analytics/archetype/proximity?days=14",
        headers=auth_headers(user.user_id),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ready"] is True
    assert body["display_mode"] == "behavioral_proximity"
    assert body["eligible_sample_count"] == 3
    assert body["suppressed_reason"] is None
    assert body["exposure_id"]
    assert "render_id" not in body

    decision = (
        db.query(ExposureDecisionEvent)
        .filter(
            ExposureDecisionEvent.user_id == user.user_id,
            ExposureDecisionEvent.content_template_id == "analytics_archetype_proximity",
        )
        .one()
    )
    assert decision.decision_status == "delivered"
    assert decision.exposure_category == "meta_inference"
    assert (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.exposure_id == decision.exposure_id)
        .count()
        == 0
    )
    assert (
        db.query(ExposureAckEvent)
        .filter(ExposureAckEvent.exposure_id == decision.exposure_id)
        .count()
        == 0
    )

    ack_payload = {
        "surface_id": "analytics.archetype_proximity",
        "client_event_id": f"analytics.archetype_proximity:{decision.exposure_id}",
        "content_snapshot": {
            "surface_id": "analytics.archetype_proximity",
            "display_mode": body["display_mode"],
            "n_tasks": body["n_tasks"],
            "proximity": body["proximity"],
        },
    }
    first_ack = client.post(
        f"/v1/exposures/{decision.exposure_id}/ack/render",
        headers=auth_headers(user.user_id),
        json=ack_payload,
    )
    assert first_ack.status_code == 200, first_ack.text
    assert first_ack.json()["created"] is True

    second_ack = client.post(
        f"/v1/exposures/{decision.exposure_id}/ack/render",
        headers=auth_headers(user.user_id),
        json=ack_payload,
    )
    assert second_ack.status_code == 200, second_ack.text
    assert second_ack.json()["created"] is False

    db.refresh(decision)
    render = (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.exposure_id == decision.exposure_id)
        .one()
    )
    ack = (
        db.query(ExposureAckEvent)
        .filter(ExposureAckEvent.exposure_id == decision.exposure_id)
        .one()
    )
    assert decision.decision_status == "rendered"
    assert render.surface == "analytics.archetype_proximity"
    assert ack.user_id == user.user_id


def test_proximity_render_ack_rejects_cross_user(db, archetypes_seeded):
    owner = _make_user(db, user_id=80, email="px-owner@example.com")
    other = _make_user(db, user_id=81, email="px-other@example.com")
    set_current_user_id(owner.user_id)
    for i in range(3):
        _seed_executed_task(
            db,
            owner.user_id,
            planned=30,
            executed=60,
            category="work",
            days_ago=i + 1,
        )
    set_current_user_id(None)

    response = client.get(
        "/v1/analytics/archetype/proximity?days=14",
        headers=auth_headers(owner.user_id),
    )
    assert response.status_code == 200, response.text
    exposure_id = response.json()["exposure_id"]

    denied = client.post(
        f"/v1/exposures/{exposure_id}/ack/render",
        headers=auth_headers(other.user_id),
        json={
            "surface_id": "analytics.archetype_proximity",
            "content_snapshot": {"surface_id": "analytics.archetype_proximity"},
        },
    )
    assert denied.status_code == 404
    assert (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.exposure_id == exposure_id)
        .count()
        == 0
    )
    assert (
        db.query(ExposureAckEvent)
        .filter(ExposureAckEvent.exposure_id == exposure_id)
        .count()
        == 0
    )


# ── Authorization ────────────────────────────────────────────────


def test_proximity_no_auth_fails_closed(
    db, archetypes_seeded
):
    """Without identity, product analytics must not fall back to operator."""
    resp = client.get("/v1/analytics/archetype/proximity?days=14")
    assert resp.status_code == 401


# ── Cross-user isolation ─────────────────────────────────────────


def test_proximity_cross_user_isolation(db, archetypes_seeded):
    """User B's tasks don't leak into user A's proximity computation."""
    user_a = _make_user(db, user_id=77, email="a@x")
    user_b = _make_user(db, user_id=88, email="b@x")
    # B has 5 procrastinator-shaped tasks
    set_current_user_id(user_b.user_id)
    for i in range(5):
        _seed_executed_task(db, user_b.user_id, planned=30, executed=60,
                           category="work", days_ago=i + 1)
    set_current_user_id(None)

    # A queries — should see uniform (no own tasks)
    resp_a = client.get(
        "/v1/analytics/archetype/proximity?days=14",
        headers=auth_headers(user_a.user_id),
    )
    body_a = resp_a.json()
    assert body_a["n_tasks"] == 0
    for row in body_a["proximity"]:
        assert abs(row["score"] - 0.20) < 1e-9

    # B queries — sees procrastinator winning
    resp_b = client.get(
        "/v1/analytics/archetype/proximity?days=14",
        headers=auth_headers(user_b.user_id),
    )
    body_b = resp_b.json()
    assert body_b["n_tasks"] == 5
    assert body_b["proximity"][0]["archetype_id"] == "procrastinator"


# ── Validation ───────────────────────────────────────────────────


def test_proximity_days_below_minimum_rejected():
    resp = client.get(
        "/v1/analytics/archetype/proximity?days=0",
        headers=auth_headers(99),
    )
    assert resp.status_code == 422


def test_proximity_days_above_maximum_rejected():
    resp = client.get(
        "/v1/analytics/archetype/proximity?days=91",
        headers=auth_headers(99),
    )
    assert resp.status_code == 422


# ── Trend endpoint ───────────────────────────────────────────────


def test_proximity_trend_returns_current_prior_and_delta(db, archetypes_seeded):
    user = _make_user(db, user_id=77, email="trend@x")
    set_current_user_id(user.user_id)
    # Recent (last 7 days): tasks pulling procrastinator
    for i in range(5):
        _seed_executed_task(db, user.user_id, planned=30, executed=60,
                           category="work", days_ago=i + 1)
    # Prior window (8-21 days ago): tasks at executed=planned (closest to lark)
    for i in range(5):
        _seed_executed_task(db, user.user_id, planned=30, executed=30,
                           category="study", days_ago=i + 8)
    set_current_user_id(None)

    resp = client.get(
        "/v1/analytics/archetype/proximity/trend?current_days=7&prior_days=14",
        headers=auth_headers(77),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "current" in body
    assert "prior" in body
    assert "delta_per_archetype" in body
    # Procrastinator increased in current vs prior
    assert body["delta_per_archetype"]["procrastinator"] > 0


def test_proximity_trend_zero_data_returns_uniform_both_windows(db, archetypes_seeded):
    user = _make_user(db, user_id=78, email="trend-empty@x")

    resp = client.get(
        "/v1/analytics/archetype/proximity/trend",
        headers=auth_headers(user.user_id),
    )
    body = resp.json()
    # Both windows uniform → all deltas are 0
    for delta in body["delta_per_archetype"].values():
        assert abs(delta) < 1e-9
