"""Starter task scheduling — window lands on today unless too late.

Covers the 2026-04-22 revision that moved the starter task seed from
"tomorrow 9 am fixed" to "today-aware with morning anchor" so the user
sees something on /today the moment they sign up (rather than an
empty /today that makes the app look dead).

Verifies three tiers + the strict-future + stay-on-today invariants.
"""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.security import _seed_starter_task
from app.db.models import Task, TaskState, User
from tests.conftest import TestingSession


def _make_user(db: Session, email: str = "starter@example.com") -> User:
    u = User(
        email=email,
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _seed_at(now: datetime, email: str) -> Task:
    """Seed a starter task with `now` mocked, return the inserted Task row."""
    db = TestingSession()
    try:
        u = _make_user(db, email=email)
        with patch("app.core.security.datetime") as mock_dt:
            mock_dt.utcnow.return_value = now
            # Allow other datetime methods to pass through
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            _seed_starter_task(db, u)
        task = db.query(Task).filter(Task.user_id == u.user_id).first()
        assert task is not None, "starter task not seeded"
        return task
    finally:
        db.close()


@pytest.mark.parametrize(
    "now, expected_start, expected_duration",
    [
        # Pre-9am local: anchor to today 9 am.
        (datetime(2026, 4, 22, 7, 30), datetime(2026, 4, 22, 9, 0), 30),
        (datetime(2026, 4, 22, 8, 45), datetime(2026, 4, 22, 9, 0), 30),
        # 9:00 exact: advance to next half-hour so start is strictly future.
        (datetime(2026, 4, 22, 9, 0), datetime(2026, 4, 22, 9, 30), 30),
        # Mid-day: next :30 or :00 mark.
        (datetime(2026, 4, 22, 11, 17), datetime(2026, 4, 22, 11, 30), 30),
        (datetime(2026, 4, 22, 11, 30), datetime(2026, 4, 22, 12, 0), 30),
        (datetime(2026, 4, 22, 15, 45), datetime(2026, 4, 22, 16, 0), 30),
        # Late afternoon: still today.
        (datetime(2026, 4, 22, 22, 0), datetime(2026, 4, 22, 22, 30), 30),
        # 23:00 today: starts 23:30, clamps end to 23:59 so duration = 29.
        (datetime(2026, 4, 22, 23, 0), datetime(2026, 4, 22, 23, 30), 29),
        # Cutover: 23:29 is the last-good mid-day slot (next :30 is 23:30).
        # Re-run the test — actually 23:29:00 with bump=0 → next_minute=29, ≤ 30
        # branch, start = 23:30. Works — but placing this in the "late_cutoff"
        # elif branch requires now < late_cutoff (23:29:00) — so 23:29:00 exact
        # falls to the else. Test it explicitly.
        (datetime(2026, 4, 22, 23, 28, 59), datetime(2026, 4, 22, 23, 30), 29),
        # 23:29:00 exact and beyond: tomorrow 9 am.
        (datetime(2026, 4, 22, 23, 29), datetime(2026, 4, 23, 9, 0), 30),
        (datetime(2026, 4, 22, 23, 45), datetime(2026, 4, 23, 9, 0), 30),
        (datetime(2026, 4, 22, 23, 59), datetime(2026, 4, 23, 9, 0), 30),
    ],
)
def test_starter_scheduled_window(now, expected_start, expected_duration):
    task = _seed_at(now, email=f"starter-{now.isoformat()}@example.com")
    assert task.planned_start_utc == expected_start, (
        f"now={now} expected start={expected_start} got {task.planned_start_utc}"
    )
    assert task.planned_duration_minutes == expected_duration, (
        f"now={now} expected duration={expected_duration} "
        f"got {task.planned_duration_minutes}"
    )


def test_starter_is_always_strictly_future():
    """No matter when a user signs up, the starter never opens in the past."""
    samples = [
        datetime(2026, 4, 22, h, m)
        for h in range(24)
        for m in (0, 15, 30, 45, 59)
    ]
    for now in samples:
        task = _seed_at(now, email=f"strict-{now.isoformat()}@example.com")
        assert task.planned_start_utc > now, (
            f"seeded start {task.planned_start_utc} not strictly future of {now}"
        )


def test_starter_stamps_onboarding_completed_at():
    """Stamp fires atomically so the 2026-05-21 kill-criterion query is reliable."""
    now = datetime(2026, 4, 22, 10, 0)
    db = TestingSession()
    try:
        u = _make_user(db, email="stamp@example.com")
        assert u.onboarding_completed_at is None
        with patch("app.core.security.datetime") as mock_dt:
            mock_dt.utcnow.return_value = now
            _seed_starter_task(db, u)
        db.refresh(u)
        assert u.onboarding_completed_at == now
    finally:
        db.close()


def test_starter_is_planned_state_with_planning_category():
    """The surface contract: state=PLANNED, category=planning, single task."""
    now = datetime(2026, 4, 22, 10, 0)
    task = _seed_at(now, email="contract@example.com")
    assert task.state == TaskState.PLANNED
    assert task.category == "planning"
    assert task.title == "Plan your week — brain dump and triage"
