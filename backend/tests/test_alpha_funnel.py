"""Alpha funnel + North Star endpoint tests (2026-04-28).

The North Star is `task_created + timer_started within first 3 min`. The
endpoint reports per-user funnel rows + aggregate metrics. Operator-only.

These tests verify:
  - operator-only auth gate
  - North Star arithmetic
  - empty-cohort handling
  - per-user row shape (timestamps + computed seconds + met flag)
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import Task, TaskState, User
from app.db.scoping import set_current_user_id
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.query(Task).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.query(Task).delete()
    db.query(User).delete()
    db.commit()


def _make_user(db, *, is_operator: bool = False, **stamps) -> User:
    u = User(
        email=f"u{uuid4().hex[:8]}@test",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=is_operator,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
        created_at=stamps.get("created_at", datetime.utcnow()),
        onboarding_completed_at=stamps.get("onboarding_completed_at"),
        first_task_at=stamps.get("first_task_at"),
        first_timer_started_at=stamps.get("first_timer_started_at"),
        d1_return_at=stamps.get("d1_return_at"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_non_operator_forbidden(client, db):
    user = _make_user(db, is_operator=False)
    response = client.get("/v1/admin/alpha_funnel", headers=auth_headers(user.user_id))
    assert response.status_code == 403


def test_unauthenticated_rejected(client):
    response = client.get("/v1/admin/alpha_funnel")
    assert response.status_code == 401


def test_empty_cohort_returns_zeros(client, db):
    op = _make_user(db, is_operator=True)
    response = client.get("/v1/admin/alpha_funnel", headers=auth_headers(op.user_id))
    assert response.status_code == 200
    body = response.json()
    assert body["funnel"]["signed_up"] == 0
    assert body["north_star"]["n_eligible"] == 0
    assert body["north_star"]["rate"] is None
    assert body["users"] == []


def test_user_who_met_north_star(client, db):
    """User who created a task at +30s and started a timer at +90s — meets
    the 3-min target on both legs.
    """
    op = _make_user(db, is_operator=True)
    base = datetime.utcnow() - timedelta(days=2)
    user = _make_user(
        db,
        created_at=base,
        onboarding_completed_at=base + timedelta(seconds=30),
        first_task_at=base + timedelta(seconds=30),
        first_timer_started_at=base + timedelta(seconds=90),
        d1_return_at=base + timedelta(days=1, seconds=10),
    )

    response = client.get("/v1/admin/alpha_funnel", headers=auth_headers(op.user_id))
    assert response.status_code == 200
    body = response.json()

    assert body["funnel"]["signed_up"] == 1
    assert body["funnel"]["completed_onboarding"] == 1
    assert body["funnel"]["first_task_within_60s"] == 1
    assert body["funnel"]["first_timer_within_180s"] == 1
    assert body["funnel"]["returned_d1"] == 1
    assert body["north_star"]["n_eligible"] == 1
    assert body["north_star"]["n_met"] == 1
    assert body["north_star"]["rate"] == 1.0

    # Per-user row content
    assert len(body["users"]) == 1
    row = body["users"][0]
    assert row["user_id"] == user.user_id
    assert row["seconds_to_first_task"] == 30
    assert row["seconds_to_first_timer"] == 90
    assert row["met_north_star"] is True


def test_user_who_missed_north_star_due_to_timer(client, db):
    """User who created a task fast but took 5 min to start the timer."""
    op = _make_user(db, is_operator=True)
    base = datetime.utcnow() - timedelta(hours=1)
    _make_user(
        db,
        created_at=base,
        first_task_at=base + timedelta(seconds=30),
        first_timer_started_at=base + timedelta(minutes=5),
    )

    response = client.get("/v1/admin/alpha_funnel", headers=auth_headers(op.user_id))
    body = response.json()

    assert body["funnel"]["first_task_within_60s"] == 1
    assert body["funnel"]["first_timer_within_180s"] == 0
    assert body["north_star"]["n_eligible"] == 1
    assert body["north_star"]["n_met"] == 0
    assert body["north_star"]["rate"] == 0.0
    assert body["users"][0]["met_north_star"] is False


def test_operator_excluded_from_cohort(client, db):
    """Operator must not appear in the funnel rows or counts."""
    op = _make_user(
        db,
        is_operator=True,
        first_task_at=datetime.utcnow(),
        first_timer_started_at=datetime.utcnow() + timedelta(seconds=60),
    )
    _make_user(db, is_operator=False)  # one alpha user

    response = client.get("/v1/admin/alpha_funnel", headers=auth_headers(op.user_id))
    body = response.json()

    assert body["funnel"]["signed_up"] == 1  # only the non-operator
    assert all(row["user_id"] != op.user_id for row in body["users"])


def test_research_integrity_note_present(client, db):
    op = _make_user(db, is_operator=True)
    response = client.get("/v1/admin/alpha_funnel", headers=auth_headers(op.user_id))
    body = response.json()
    note = body.get("research_integrity_note", "")
    assert "VT-15" in note or "VT-16" in note
    assert "H1" in note
