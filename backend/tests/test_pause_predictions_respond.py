"""Pins the Commit 5b contract for POST /v1/pause_predictions/{firing_id}/respond.

  * Valid response writes user_response + response_at; the reconcile job
    will leave the row alone on the next tick.
  * Unknown firing_id → 404 (also covers the scoping defense: a firing
    that belongs to another user is invisible to the caller and 404s).
  * Already-reconciled firing → 409 (pre-registration forbids
    overwriting a closed window).
  * user_response must be one of pause_now | dismiss | snooze; any other
    string fails pydantic validation (422).
"""
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.models import PausePredictionLog, User
from app.db.scoping import set_current_user_id
from app.utils.time_utils import now_utc

# TestClient defaults X-User-Id to "1" (app/api/deps.py). Seeds use
# USER_ID=1 so they're visible to the request; OTHER_USER_ID=2 tests
# scoping isolation.
USER_ID = 1
OTHER_USER_ID = 2


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM pause_prediction_log"))
    db.execute(text("DELETE FROM user"))
    db.commit()
    now = now_utc()
    db.add_all([
        User(user_id=USER_ID, email="respond-1@test", is_operator=True, notion_enabled=False, created_at=now),
        User(user_id=OTHER_USER_ID, email="respond-2@test", is_operator=False, notion_enabled=False, created_at=now),
    ])
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM pause_prediction_log"))
    db.execute(text("DELETE FROM user"))
    db.commit()


def _seed_firing(
    db,
    *,
    user_id: int = USER_ID,
    user_response=None,
    response_at=None,
) -> PausePredictionLog:
    now = now_utc()
    row = PausePredictionLog(
        user_id=user_id,
        fired_at=now - timedelta(minutes=4),
        predicted_at=now - timedelta(minutes=1),
        mechanism="clock_anchor",
        confidence=0.62,
        lead_minutes=3,
        sample_size=6,
        user_response=user_response,
        response_at=response_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_respond_pause_now_records_response_and_timestamp(db, client):
    row = _seed_firing(db)

    r = client.post(
        f"/v1/pause_predictions/{row.firing_id}/respond",
        json={"user_response": "pause_now"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["firing_id"] == row.firing_id
    assert body["user_response"] == "pause_now"
    assert body["response_at"] is not None

    db.expire(row)
    assert row.user_response == "pause_now"
    assert row.response_at is not None


def test_respond_dismiss_and_snooze_both_accepted(db, client):
    row_a = _seed_firing(db)
    row_b = _seed_firing(db)

    ra = client.post(
        f"/v1/pause_predictions/{row_a.firing_id}/respond",
        json={"user_response": "dismiss"},
    )
    rb = client.post(
        f"/v1/pause_predictions/{row_b.firing_id}/respond",
        json={"user_response": "snooze"},
    )
    assert ra.status_code == 200
    assert rb.status_code == 200
    assert ra.json()["user_response"] == "dismiss"
    assert rb.json()["user_response"] == "snooze"


def test_respond_unknown_firing_id_returns_404(client):
    r = client.post(
        f"/v1/pause_predictions/{uuid4()}/respond",
        json={"user_response": "pause_now"},
    )
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


def test_respond_other_users_firing_is_invisible_404(db, client):
    """Scoping defense: a firing for user_id=2 must 404 for user_id=1."""
    other_row = _seed_firing(db, user_id=OTHER_USER_ID)

    r = client.post(
        f"/v1/pause_predictions/{other_row.firing_id}/respond",
        json={"user_response": "pause_now"},
    )
    assert r.status_code == 404


def test_respond_already_reconciled_returns_409(db, client):
    row = _seed_firing(
        db,
        user_response="no_response",
        response_at=now_utc() - timedelta(minutes=2),
    )

    r = client.post(
        f"/v1/pause_predictions/{row.firing_id}/respond",
        json={"user_response": "pause_now"},
    )
    assert r.status_code == 409
    assert "already reconciled" in r.json()["detail"].lower()
    # The original value must remain — no silent overwrite.
    db.expire(row)
    assert row.user_response == "no_response"


def test_respond_rejects_invalid_user_response(db, client):
    row = _seed_firing(db)

    r = client.post(
        f"/v1/pause_predictions/{row.firing_id}/respond",
        json={"user_response": "procrastinate"},
    )
    assert r.status_code == 422
