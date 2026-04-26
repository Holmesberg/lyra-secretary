"""Phase I — /v1/analytics/deadline-shape endpoint tests.

Verifies:
- Empty case: zero outcomes returns the placeholder shape
- Happy path: outcomes are summarized, stratified, per-deadline
- voided_at_guard discipline: voided outcomes/tasks/deadlines excluded
- Per-user scoping: cross-user data not visible
- Stratification by deadline_match_source + scope_bullet_count band
- Per-deadline bias_factor_observed (Rule 15 input)
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models import (
    Deadline,
    Task,
    TaskDeadlineOutcome,
    TaskSource,
    TaskState,
    User,
)
from app.main import app


client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clean_slate(db):
    db.rollback()
    db.query(TaskDeadlineOutcome).delete()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    db.rollback()
    db.query(TaskDeadlineOutcome).delete()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()


def _make_user(db, email: str) -> User:
    u = User(
        email=email,
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _hdr(uid: int) -> dict:
    return {"X-User-Id": str(uid)}


def _seed_outcome(
    db, user_id: int,
    deadline_match_source: str = "user_explicit",
    scope_bullets: int = 2,
    delay_minutes: int = -10,  # met by 10
    deadline_voided: bool = False,
    task_voided: bool = False,
    outcome_voided: bool = False,
    deadline_state: str = "active",
    planned_duration: int = 60,
    executed_duration: int = 70,
    deadline_title: str = "Test Deadline",
):
    """Seed one (deadline, task, outcome) trio."""
    base = datetime(2026, 5, 1, 9, 0, 0)
    deadline = Deadline(
        deadline_id=str(uuid4()),
        user_id=user_id,
        title=deadline_title,
        due_at_utc=base + timedelta(hours=1),
        state=deadline_state,
        voided_at=datetime.utcnow() if deadline_voided else None,
    )
    db.add(deadline)
    db.flush()

    task = Task(
        task_id=str(uuid4()),
        title="Bound task",
        planned_start_utc=base,
        planned_end_utc=base + timedelta(minutes=planned_duration),
        planned_duration_minutes=planned_duration,
        executed_start_utc=base,
        executed_end_utc=base + timedelta(minutes=executed_duration),
        executed_duration_minutes=executed_duration,
        state=TaskState.EXECUTED,
        source=TaskSource.MANUAL,
        user_id=user_id,
        deadline_id=deadline.deadline_id,
        deadline_match_source=deadline_match_source,
        deadline_match_confidence=1.0 if deadline_match_source == "user_explicit" else 0.7,
        scope_bullet_count_at_plan=scope_bullets,
        voided_at=datetime.utcnow() if task_voided else None,
    )
    db.add(task)
    db.flush()

    outcome = TaskDeadlineOutcome(
        task_id=task.task_id,
        user_id=user_id,
        computed_at=datetime.utcnow(),
        deadline_utc_at_compute=deadline.due_at_utc,
        executed_end_utc_at_compute=task.executed_end_utc,
        deadline_met=delay_minutes <= 0,
        delay_minutes=delay_minutes,
        voided_at=datetime.utcnow() if outcome_voided else None,
    )
    db.add(outcome)
    db.commit()
    return deadline, task, outcome


# ── Empty case ───────────────────────────────────────────────────


def test_empty_returns_placeholder_shape(db):
    user = _make_user(db, "empty@example.com")
    resp = client.get("/v1/analytics/deadline-shape", headers=_hdr(user.user_id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total_outcomes"] == 0
    assert data["summary"]["mean_delay_minutes"] is None
    assert data["per_deadline"] == []
    assert "no deadline-bound" in data["note"]


# ── Happy path ───────────────────────────────────────────────────


def test_happy_path_summarizes(db):
    user = _make_user(db, "happy@example.com")
    # 3 met, 2 missed
    for delay in [-5, -10, -15]:
        _seed_outcome(db, user.user_id, delay_minutes=delay)
    for delay in [10, 30]:
        _seed_outcome(db, user.user_id, delay_minutes=delay)

    resp = client.get("/v1/analytics/deadline-shape", headers=_hdr(user.user_id))
    assert resp.status_code == 200
    s = resp.json()["summary"]
    assert s["total_outcomes"] == 5
    assert s["deadline_met_count"] == 3
    assert s["deadline_missed_count"] == 2
    assert s["deadline_met_rate"] == 0.6
    # Mean delay = (-5 + -10 + -15 + 10 + 30) / 5 = 2.0
    assert s["mean_delay_minutes"] == 2.0
    assert s["median_delay_minutes"] == -5  # sorted middle


# ── voided_at discipline ─────────────────────────────────────────


def test_voided_outcome_excluded(db):
    user = _make_user(db, "voided1@example.com")
    _seed_outcome(db, user.user_id, delay_minutes=-5)
    _seed_outcome(db, user.user_id, delay_minutes=10, outcome_voided=True)

    resp = client.get("/v1/analytics/deadline-shape", headers=_hdr(user.user_id))
    assert resp.json()["summary"]["total_outcomes"] == 1


def test_voided_task_excluded(db):
    user = _make_user(db, "voided2@example.com")
    _seed_outcome(db, user.user_id, delay_minutes=-5)
    _seed_outcome(db, user.user_id, delay_minutes=10, task_voided=True)

    resp = client.get("/v1/analytics/deadline-shape", headers=_hdr(user.user_id))
    assert resp.json()["summary"]["total_outcomes"] == 1


def test_voided_deadline_excluded(db):
    user = _make_user(db, "voided3@example.com")
    _seed_outcome(db, user.user_id, delay_minutes=-5)
    _seed_outcome(db, user.user_id, delay_minutes=10, deadline_voided=True)

    resp = client.get("/v1/analytics/deadline-shape", headers=_hdr(user.user_id))
    assert resp.json()["summary"]["total_outcomes"] == 1


# ── Cross-user scoping ───────────────────────────────────────────


def test_cross_user_scoping(db):
    alice = _make_user(db, "i-alice@example.com")
    bob = _make_user(db, "i-bob@example.com")

    _seed_outcome(db, alice.user_id, delay_minutes=-5)
    _seed_outcome(db, bob.user_id, delay_minutes=20)

    alice_resp = client.get("/v1/analytics/deadline-shape", headers=_hdr(alice.user_id))
    bob_resp = client.get("/v1/analytics/deadline-shape", headers=_hdr(bob.user_id))

    assert alice_resp.json()["summary"]["total_outcomes"] == 1
    assert alice_resp.json()["summary"]["deadline_met_count"] == 1
    assert bob_resp.json()["summary"]["total_outcomes"] == 1
    assert bob_resp.json()["summary"]["deadline_missed_count"] == 1


# ── Stratification ───────────────────────────────────────────────


def test_stratification_by_match_source(db):
    user = _make_user(db, "strat1@example.com")
    _seed_outcome(db, user.user_id, deadline_match_source="user_explicit", delay_minutes=-5)
    _seed_outcome(db, user.user_id, deadline_match_source="user_explicit", delay_minutes=-10)
    _seed_outcome(db, user.user_id, deadline_match_source="parser_auto", delay_minutes=20)

    resp = client.get("/v1/analytics/deadline-shape", headers=_hdr(user.user_id))
    by_source = {b["source"]: b for b in resp.json()["by_match_source"]}
    assert by_source["user_explicit"]["n"] == 2
    assert by_source["user_explicit"]["met_rate"] == 1.0
    assert by_source["parser_auto"]["n"] == 1
    assert by_source["parser_auto"]["met_rate"] == 0.0


def test_stratification_by_scope_bullet_band(db):
    user = _make_user(db, "strat2@example.com")
    # Two in band 0
    _seed_outcome(db, user.user_id, scope_bullets=0, delay_minutes=-5)
    _seed_outcome(db, user.user_id, scope_bullets=0, delay_minutes=-10)
    # One in band 1-3
    _seed_outcome(db, user.user_id, scope_bullets=2, delay_minutes=10)
    # One in band 4-6
    _seed_outcome(db, user.user_id, scope_bullets=5, delay_minutes=20)
    # One in band 7+
    _seed_outcome(db, user.user_id, scope_bullets=10, delay_minutes=60)

    resp = client.get("/v1/analytics/deadline-shape", headers=_hdr(user.user_id))
    bands = {b["band"]: b for b in resp.json()["by_scope_bullet_count_band"]}
    assert bands["0"]["n"] == 2
    assert bands["1-3"]["n"] == 1
    assert bands["4-6"]["n"] == 1
    assert bands["7+"]["n"] == 1
    assert bands["7+"]["mean_delay_minutes"] == 60.0


# ── Per-deadline aggregation (Rule 15 input) ─────────────────────


def test_per_deadline_aggregates(db):
    user = _make_user(db, "perdl@example.com")
    base = datetime(2026, 5, 1, 9, 0, 0)

    # Two deadlines, two tasks each
    deadline_a = Deadline(
        deadline_id=str(uuid4()),
        user_id=user.user_id,
        title="DL-A",
        due_at_utc=base + timedelta(hours=2),
        state="active",
    )
    deadline_b = Deadline(
        deadline_id=str(uuid4()),
        user_id=user.user_id,
        title="DL-B",
        due_at_utc=base + timedelta(hours=2),
        state="active",
    )
    db.add_all([deadline_a, deadline_b])
    db.flush()

    for d, delays in [(deadline_a, [-5, -10]), (deadline_b, [20, 40])]:
        for delay in delays:
            t = Task(
                task_id=str(uuid4()),
                title="t",
                planned_start_utc=base,
                planned_end_utc=base + timedelta(hours=1),
                planned_duration_minutes=60,
                executed_start_utc=base,
                executed_end_utc=base + timedelta(minutes=60 + delay // 5),
                executed_duration_minutes=60 + delay // 5,
                state=TaskState.EXECUTED,
                source=TaskSource.MANUAL,
                user_id=user.user_id,
                deadline_id=d.deadline_id,
                deadline_match_source="user_explicit",
                deadline_match_confidence=1.0,
            )
            db.add(t)
            db.flush()

            o = TaskDeadlineOutcome(
                task_id=t.task_id,
                user_id=user.user_id,
                computed_at=datetime.utcnow(),
                deadline_utc_at_compute=d.due_at_utc,
                executed_end_utc_at_compute=t.executed_end_utc,
                deadline_met=delay <= 0,
                delay_minutes=delay,
            )
            db.add(o)
    db.commit()

    resp = client.get("/v1/analytics/deadline-shape", headers=_hdr(user.user_id))
    per_dl = {d["title"]: d for d in resp.json()["per_deadline"]}

    assert per_dl["DL-A"]["n"] == 2
    assert per_dl["DL-A"]["met_rate"] == 1.0
    assert per_dl["DL-B"]["n"] == 2
    assert per_dl["DL-B"]["met_rate"] == 0.0
    # bias_factor_observed exposed (Rule 15)
    assert per_dl["DL-A"]["bias_factor_observed"] is not None
    assert per_dl["DL-B"]["bias_factor_observed"] is not None
