"""Feedback widget endpoint smoke tests (2026-04-28).

Covers:
  - POST /v1/feedback as authenticated user → row written + 200
  - POST /v1/feedback rejects empty/oversized body
  - GET /v1/admin/feedback as operator returns ordered list
  - GET /v1/admin/feedback as non-operator → 403
  - POST /v1/admin/feedback/{id}/resolve flips status

Notifier (email/Telegram) is mocked — we only verify the endpoint
contract, not actual delivery.
"""
from datetime import datetime
from uuid import uuid4

import pytest

from app.db.models import Feedback, User
from app.db.scoping import set_current_user_id
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def _clean_slate(db, monkeypatch):
    set_current_user_id(None)
    db.rollback()
    db.query(Feedback).delete()
    db.query(User).delete()
    db.commit()
    # Mock the notifier so tests don't hit Resend/Telegram
    monkeypatch.setattr(
        "app.api.v1.endpoints.feedback.notify_operator",
        lambda **kw: {"email": True, "telegram": True},
    )
    yield
    set_current_user_id(None)
    db.rollback()
    db.query(Feedback).delete()
    db.query(User).delete()
    db.commit()


def _make_user(db, *, is_operator: bool = False) -> User:
    u = User(
        email=f"u{uuid4().hex[:8]}@test",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=is_operator,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_submit_feedback_writes_row(client, db):
    u = _make_user(db)
    r = client.post(
        "/v1/feedback",
        json={"kind": "bug", "body": "the thing exploded"},
        headers=auth_headers(u.user_id),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "feedback_id" in body
    rows = db.query(Feedback).all()
    assert len(rows) == 1
    assert rows[0].kind == "bug"
    assert rows[0].body == "the thing exploded"
    assert rows[0].status == "unread"


def test_submit_feedback_rejects_empty_body(client, db):
    u = _make_user(db)
    r = client.post(
        "/v1/feedback",
        json={"kind": "suggestion", "body": ""},
        headers=auth_headers(u.user_id),
    )
    assert r.status_code in (400, 422)


def test_submit_feedback_with_context(client, db):
    u = _make_user(db)
    r = client.post(
        "/v1/feedback",
        json={
            "kind": "confused",
            "body": "I don't get the chip",
            "page_url": "https://lyraos.org/today",
            "user_agent": "Mozilla/5.0...",
            "error_context": [{"msg": "TypeError x"}],
        },
        headers=auth_headers(u.user_id),
    )
    assert r.status_code == 200
    row = db.query(Feedback).first()
    assert row.page_url == "https://lyraos.org/today"
    assert row.error_context == [{"msg": "TypeError x"}]


def test_admin_feedback_list_operator_only(client, db):
    op = _make_user(db, is_operator=True)
    user = _make_user(db)
    # Submit a feedback as the user
    client.post(
        "/v1/feedback",
        json={"kind": "bug", "body": "test row"},
        headers=auth_headers(user.user_id),
    )
    # Operator can list
    r = client.get("/v1/admin/feedback", headers=auth_headers(op.user_id))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["unread_count"] == 1
    assert body["items"][0]["body"] == "test row"
    assert body["items"][0]["user_email"] == user.email


def test_admin_feedback_list_non_operator_rejected(client, db):
    user = _make_user(db, is_operator=False)
    r = client.get("/v1/admin/feedback", headers=auth_headers(user.user_id))
    assert r.status_code == 403


def test_admin_feedback_resolve_flips_status(client, db):
    op = _make_user(db, is_operator=True)
    user = _make_user(db)
    s = client.post(
        "/v1/feedback",
        json={"kind": "bug", "body": "test"},
        headers=auth_headers(user.user_id),
    )
    fid = s.json()["feedback_id"]
    r = client.post(
        f"/v1/admin/feedback/{fid}/resolve",
        json={"status": "acted_on", "operator_note": "fixed in commit X"},
        headers=auth_headers(op.user_id),
    )
    assert r.status_code == 200
    row = db.query(Feedback).filter(Feedback.feedback_id == fid).first()
    assert row.status == "acted_on"
    assert row.operator_note == "fixed in commit X"
    assert row.resolved_at is not None
