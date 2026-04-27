"""Tests for GET /v1/analytics/calibration_nudge.

Loop 1 endpoint per feedback_loops_closure_plan.md §Loop 1. Mirrors
/v1/analytics/pause_prediction shape; pre-registered primary metric
is delta_difference between accepted-vs-dismissed groups.
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models import (
    CalibrationNudgeEvent,
    Task,
    TaskSource,
    TaskState,
    User,
)
from app.db.scoping import set_current_user_id
from app.main import app
from tests.conftest import auth_headers


client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM calibration_nudge_event"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM \"user\""))
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM calibration_nudge_event"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM \"user\""))
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


def _seed_task_and_event(
    db, user_id: int, *,
    user_planned: int,
    suggested: int,
    decision: str,
    executed: int = None,
    days_ago: int = 1,
    voided: bool = False,
) -> CalibrationNudgeEvent:
    """Seed a Task + matching CalibrationNudgeEvent.

    If executed is set, event is "resolved" with that duration.
    Otherwise event is unresolved (executed_duration_minutes = NULL).
    """
    base = datetime.utcnow() - timedelta(days=days_ago)
    task = Task(
        task_id=str(uuid4()),
        title="t",
        category="study",
        planned_start_utc=base,
        planned_end_utc=base + timedelta(minutes=user_planned),
        planned_duration_minutes=user_planned,
        executed_start_utc=base if executed else None,
        executed_end_utc=(
            base + timedelta(minutes=executed) if executed else None
        ),
        executed_duration_minutes=executed,
        state=TaskState.EXECUTED if executed else TaskState.PLANNED,
        source=TaskSource.MANUAL,
        user_id=user_id,
    )
    db.add(task)
    db.flush()

    event = CalibrationNudgeEvent(
        event_id=str(uuid4()),
        user_id=user_id,
        task_id=task.task_id,
        suggested_duration_minutes=suggested,
        user_planned_duration_minutes=user_planned,
        bias_factor=1.4,
        sample_size=12,
        user_decision=decision,
        decided_at=base,
        executed_duration_minutes=executed,
        resolved_at=datetime.utcnow() if executed else None,
        voided_at=datetime.utcnow() if voided else None,
    )
    db.add(event)
    db.commit()
    return event


# ── Empty-state ────────────────────────────────────────────────────


def test_empty_state_returns_zeros(db):
    user = _make_user(db, user_id=77, email="empty@x")
    resp = client.get(
        "/v1/analytics/calibration_nudge",
        headers=auth_headers(user.user_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total_nudges"] == 0
    assert body["summary"]["acceptance_rate"] == 0.0
    assert body["delta_by_decision"]["accepted_mean_delta_minutes"] is None
    assert body["delta_by_decision"]["dismissed_mean_delta_minutes"] is None


# ── Happy path: accept + outcome ───────────────────────────────────


def test_summary_counts_accepted_dismissed_resolved(db):
    user = _make_user(db, user_id=77, email="happy@x")
    # 3 accepted, 1 resolved
    _seed_task_and_event(db, user.user_id, user_planned=60, suggested=90,
                         decision="accepted", executed=85)
    _seed_task_and_event(db, user.user_id, user_planned=60, suggested=90,
                         decision="accepted", executed=None)
    _seed_task_and_event(db, user.user_id, user_planned=60, suggested=90,
                         decision="accepted", executed=None)
    # 2 dismissed, 1 resolved
    _seed_task_and_event(db, user.user_id, user_planned=30, suggested=60,
                         decision="dismissed", executed=55)
    _seed_task_and_event(db, user.user_id, user_planned=30, suggested=60,
                         decision="dismissed", executed=None)

    resp = client.get(
        "/v1/analytics/calibration_nudge",
        headers=auth_headers(user.user_id),
    )
    body = resp.json()
    assert body["summary"]["total_nudges"] == 5
    assert body["summary"]["accepted"] == 3
    assert body["summary"]["dismissed"] == 2
    assert body["summary"]["resolved"] == 2  # 1 from each group
    assert body["summary"]["unresolved"] == 3
    assert body["summary"]["acceptance_rate"] == 0.6


def test_delta_means_computed_from_resolved_events(db):
    user = _make_user(db, user_id=77, email="delta@x")
    # Accepted: planned=90 (=suggested), executed=85 → delta = 90-85 = +5 (under)
    _seed_task_and_event(db, user.user_id, user_planned=90, suggested=90,
                         decision="accepted", executed=85)
    # Dismissed: planned=30, executed=60 → delta = 30-60 = -30 (over)
    _seed_task_and_event(db, user.user_id, user_planned=30, suggested=60,
                         decision="dismissed", executed=60)

    resp = client.get(
        "/v1/analytics/calibration_nudge",
        headers=auth_headers(user.user_id),
    )
    body = resp.json()
    assert body["delta_by_decision"]["accepted_mean_delta_minutes"] == 5
    assert body["delta_by_decision"]["dismissed_mean_delta_minutes"] == -30
    # Difference: accepted (+5) − dismissed (-30) = +35 ← accepted group ran more on time
    assert body["delta_by_decision"]["delta_difference_accepted_minus_dismissed"] == 35


# ── voided_at filter ──────────────────────────────────────────────


def test_voided_events_excluded(db):
    user = _make_user(db, user_id=77, email="voided@x")
    _seed_task_and_event(db, user.user_id, user_planned=60, suggested=90,
                         decision="accepted", executed=85)
    _seed_task_and_event(db, user.user_id, user_planned=60, suggested=90,
                         decision="accepted", executed=85, voided=True)

    resp = client.get(
        "/v1/analytics/calibration_nudge",
        headers=auth_headers(user.user_id),
    )
    body = resp.json()
    assert body["summary"]["total_nudges"] == 1


# ── Lookback window ────────────────────────────────────────────────


def test_old_events_outside_lookback_excluded(db):
    user = _make_user(db, user_id=77, email="old@x")
    # 5 days ago — within 30-day lookback
    _seed_task_and_event(db, user.user_id, user_planned=60, suggested=90,
                         decision="accepted", days_ago=5, executed=85)
    # 60 days ago — outside default 30-day lookback
    _seed_task_and_event(db, user.user_id, user_planned=60, suggested=90,
                         decision="accepted", days_ago=60, executed=85)

    resp = client.get(
        "/v1/analytics/calibration_nudge",
        headers=auth_headers(user.user_id),
    )
    body = resp.json()
    assert body["summary"]["total_nudges"] == 1

    # Wider window catches both
    resp = client.get(
        "/v1/analytics/calibration_nudge?days=90",
        headers=auth_headers(user.user_id),
    )
    body = resp.json()
    assert body["summary"]["total_nudges"] == 2


# ── Cross-user isolation ──────────────────────────────────────────


def test_cross_user_isolation(db):
    user_a = _make_user(db, user_id=77, email="a@x")
    user_b = _make_user(db, user_id=88, email="b@x")
    _seed_task_and_event(db, user_a.user_id, user_planned=60, suggested=90,
                         decision="accepted", executed=85)
    _seed_task_and_event(db, user_b.user_id, user_planned=60, suggested=90,
                         decision="dismissed", executed=110)

    # A sees only A's events
    resp_a = client.get(
        "/v1/analytics/calibration_nudge",
        headers=auth_headers(user_a.user_id),
    )
    body_a = resp_a.json()
    assert body_a["summary"]["total_nudges"] == 1
    assert body_a["summary"]["accepted"] == 1
    assert body_a["summary"]["dismissed"] == 0

    # B sees only B's events
    resp_b = client.get(
        "/v1/analytics/calibration_nudge",
        headers=auth_headers(user_b.user_id),
    )
    body_b = resp_b.json()
    assert body_b["summary"]["total_nudges"] == 1
    assert body_b["summary"]["accepted"] == 0
    assert body_b["summary"]["dismissed"] == 1


# ── Validation ─────────────────────────────────────────────────────


def test_lookback_below_minimum_rejected():
    resp = client.get(
        "/v1/analytics/calibration_nudge?days=0",
        headers=auth_headers(77),
    )
    assert resp.status_code == 422


def test_lookback_above_maximum_rejected():
    resp = client.get(
        "/v1/analytics/calibration_nudge?days=181",
        headers=auth_headers(77),
    )
    assert resp.status_code == 422
