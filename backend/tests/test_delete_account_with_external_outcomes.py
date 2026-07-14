"""Delete-account regression — external_event_outcome rows don't block user deletion.

Protects against the 2026-04-22 LYR-103 bug where migration 027 added
external_event_outcome.user_id as a bare FK (ON DELETE NO ACTION),
causing DELETE /v1/users/me to 500 with ForeignKeyViolation when the
user had any marked attendance outcomes. Migration 028 added CASCADE;
this test pins that behavior so a future FK edit can't silently
regress it.

Covers both retention and hard-delete branches so the CASCADE works
regardless of which path the user picks.
"""
from datetime import datetime

from fastapi.testclient import TestClient

from app.db.models import ExternalEventOutcome, User
from app.main import app
from tests.conftest import TestingSession

client = TestClient(app, raise_server_exceptions=False)


def _make_user_with_outcome(email: str) -> int:
    """Create a user + one external_event_outcome row. Returns user_id."""
    db = TestingSession()
    try:
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
        outcome = ExternalEventOutcome(
            user_id=u.user_id,
            external_source="google_calendar",
            external_id="test_event_abc",
            outcome="attended",
            event_title="Test event",
            marked_at=datetime.utcnow(),
        )
        db.add(outcome)
        db.commit()
        return u.user_id
    finally:
        db.close()


def _outcome_count(user_id: int) -> int:
    db = TestingSession()
    try:
        return (
            db.query(ExternalEventOutcome)
            .filter(ExternalEventOutcome.user_id == user_id)
            .count()
        )
    finally:
        db.close()


def _user_exists(user_id: int) -> bool:
    db = TestingSession()
    try:
        return db.query(User).filter(User.user_id == user_id).first() is not None
    finally:
        db.close()


def test_delete_retention_mode_with_outcome_row(account_delete_runtime_purge_ok):
    email = "delete-retain-with-outcome@example.com"
    user_id = _make_user_with_outcome(email)
    assert _outcome_count(user_id) == 1

    resp = client.request(
        "DELETE",
        "/v1/users/me",
        json={"confirm_email": email, "retain_for_research": True},
        headers={"X-User-Id": str(user_id)},
    )
    assert resp.status_code == 200, resp.text
    assert account_delete_runtime_purge_ok == [user_id]
    assert not _user_exists(user_id)
    # CASCADE purges outcomes — LYR-103 follow-up would anonymize for
    # VT-23 aggregate retention when n is large enough to matter.
    assert _outcome_count(user_id) == 0


def test_delete_hard_delete_with_outcome_row(account_delete_runtime_purge_ok):
    email = "delete-hard-with-outcome@example.com"
    user_id = _make_user_with_outcome(email)
    assert _outcome_count(user_id) == 1

    resp = client.request(
        "DELETE",
        "/v1/users/me",
        json={"confirm_email": email, "retain_for_research": False},
        headers={"X-User-Id": str(user_id)},
    )
    assert resp.status_code == 200, resp.text
    assert account_delete_runtime_purge_ok == [user_id]
    assert not _user_exists(user_id)
    assert _outcome_count(user_id) == 0
