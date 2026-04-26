"""Phase H — sweep_missed_deadlines job tests.

Calls _run_for_one_user(db, user) directly. Verifies:
- Active deadlines past due_at_utc transition to 'missed'
- Active deadlines NOT yet past due stay active
- Planned deadlines past due_at stay planned (intentional — see job docstring)
- Voided deadlines skipped (per voided_at_guard)
- Already-missed deadlines stay missed (idempotent)
- Per-user scoping
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import Deadline, User
from app.workers.jobs.sweep_missed_deadlines import _run_for_one_user


@pytest.fixture(autouse=True)
def _clean_slate(db):
    db.rollback()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    db.rollback()
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


def _make_deadline(db, user_id: int, due_at: datetime, **overrides) -> Deadline:
    d = Deadline(
        deadline_id=str(uuid4()),
        user_id=user_id,
        title=overrides.get("title", "Test"),
        due_at_utc=due_at,
        state=overrides.get("state", "active"),
        voided_at=overrides.get("voided_at"),
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def test_active_past_due_transitions_to_missed(db):
    user = _make_user(db, "s1@example.com")
    past = datetime.utcnow() - timedelta(hours=2)
    deadline = _make_deadline(db, user.user_id, due_at=past, state="active")

    _run_for_one_user(db, user)

    db.refresh(deadline)
    assert deadline.state == "missed"


def test_active_not_yet_due_stays_active(db):
    user = _make_user(db, "s2@example.com")
    future = datetime.utcnow() + timedelta(hours=2)
    deadline = _make_deadline(db, user.user_id, due_at=future, state="active")

    _run_for_one_user(db, user)

    db.refresh(deadline)
    assert deadline.state == "active"


def test_planned_past_due_stays_planned(db):
    """Planned = user never bound a task. Don't transition to missed."""
    user = _make_user(db, "s3@example.com")
    past = datetime.utcnow() - timedelta(hours=2)
    deadline = _make_deadline(db, user.user_id, due_at=past, state="planned")

    _run_for_one_user(db, user)

    db.refresh(deadline)
    assert deadline.state == "planned"


def test_voided_deadlines_skipped(db):
    user = _make_user(db, "s4@example.com")
    past = datetime.utcnow() - timedelta(hours=2)
    deadline = _make_deadline(
        db, user.user_id, due_at=past,
        state="active", voided_at=datetime.utcnow(),
    )

    _run_for_one_user(db, user)

    db.refresh(deadline)
    # Voided deadlines aren't transitioned (still 'active' field but voided_at set)
    assert deadline.state == "active"


def test_already_missed_stays_missed(db):
    user = _make_user(db, "s5@example.com")
    past = datetime.utcnow() - timedelta(hours=2)
    deadline = _make_deadline(db, user.user_id, due_at=past, state="missed")

    _run_for_one_user(db, user)

    db.refresh(deadline)
    assert deadline.state == "missed"


def test_per_user_scoping(db):
    user_a = _make_user(db, "sa@example.com")
    user_b = _make_user(db, "sb@example.com")
    past = datetime.utcnow() - timedelta(hours=2)

    deadline_b = _make_deadline(db, user_b.user_id, due_at=past, state="active")

    # Sweep for user_a — should NOT touch user_b's deadline
    _run_for_one_user(db, user_a)
    db.refresh(deadline_b)
    assert deadline_b.state == "active"

    # Sweep for user_b — now transitions
    _run_for_one_user(db, user_b)
    db.refresh(deadline_b)
    assert deadline_b.state == "missed"


def test_completed_deadline_not_swept(db):
    """Completed deadlines past due_at should NOT transition to missed."""
    user = _make_user(db, "s6@example.com")
    past = datetime.utcnow() - timedelta(hours=2)
    deadline = _make_deadline(db, user.user_id, due_at=past, state="completed")

    _run_for_one_user(db, user)

    db.refresh(deadline)
    assert deadline.state == "completed"
