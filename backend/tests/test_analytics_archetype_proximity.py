"""Tests for GET /v1/analytics/archetype/proximity + /trend.

Covers MANIFESTO Rule 17 (2026-04-27 — VT-25 dynamic-reveal endpoint).
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models import Archetype, Task, TaskSource, TaskState, User
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
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM \"user\""))
    db.execute(text("DELETE FROM archetype"))
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
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
    assert len(body["proximity"]) == 5
    # Each row has the expected fields
    for row in body["proximity"]:
        assert set(row.keys()) >= {"archetype_id", "label", "score", "rank", "n_tasks"}


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


# ── Authorization ────────────────────────────────────────────────


def test_proximity_no_auth_user_id_falls_back_to_default_per_middleware(
    db, archetypes_seeded
):
    """Without X-User-Id, UserScopeMiddleware defaults to user_id=1.

    This documents the existing middleware behavior (per
    docs/testing_patterns.md). The endpoint itself doesn't 401 — that
    fallback is documented as the SHIM, not a bug.

    To get a real 401, you'd need to send a malformed Bearer token
    (covered in middleware-level tests, not here).
    """
    # Don't seed user_id=1; without ContextVar reset middleware sets it
    resp = client.get("/v1/analytics/archetype/proximity?days=14")
    # Either 200 with cold-start (no archetype rows or no tasks for u1)
    # OR 200 with whatever data user_id=1 has. Both indicate the endpoint
    # is reachable; not a 401. The actual cross-user isolation guarantee
    # is enforced by the proximity service's user_id scoping.
    assert resp.status_code == 200


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
