"""Pins the GET /v1/analytics/pause_prediction response shape (Commit 5a).

The endpoint is per-user scoped (like every other analytics endpoint) —
cross-user analysis lives in the Commit 5c notebook via direct DB reads.
The notebook reads specific keys so any shape change is a breaking change;
these tests freeze the contract.

Covers:
  * Empty history → zero counts, acceptance_rate=0.0.
  * Mixed reconciled/unreconciled → counts split, rate computed from
    reconciled denominator only (unreconciled excluded from both
    numerator and denominator).
  * Snooze re-fires (parent_firing_id IS NOT NULL) → excluded from
    summary; surfaced via snooze_refires_excluded.
  * by_mechanism split is correct across clock_anchor and work_rhythm.
  * Scoping: another user's rows never leak into the caller's view.
"""
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.db.models import PausePredictionLog, User
from app.db.scoping import set_current_user_id
from app.utils.time_utils import now_utc

# The TestClient defaults X-User-Id to "1" (app/api/deps.py:18). Every
# seeded row in these tests uses USER_ID so it is visible to the request,
# and the scoping-leak test uses OTHER to confirm cross-user filtering.
USER_ID = 1
OTHER_USER_ID = 2


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM pause_prediction_log"))
    db.execute(text("DELETE FROM user"))
    db.commit()
    # Seed both users so FK references are valid.
    now = now_utc()
    db.add_all([
        User(user_id=USER_ID, email="primary@test", is_operator=True, notion_enabled=False, created_at=now),
        User(user_id=OTHER_USER_ID, email="other@test", is_operator=False, notion_enabled=False, created_at=now),
    ])
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM pause_prediction_log"))
    db.execute(text("DELETE FROM user"))
    db.commit()


def _seed(
    db,
    *,
    user_id: int = USER_ID,
    mechanism: str = "clock_anchor",
    user_response=None,
    parent_firing_id=None,
    fired_minutes_ago: int = 20,
):
    now = now_utc()
    row = PausePredictionLog(
        user_id=user_id,
        fired_at=now - timedelta(minutes=fired_minutes_ago),
        predicted_at=now - timedelta(minutes=fired_minutes_ago - 3),
        mechanism=mechanism,
        confidence=0.60,
        lead_minutes=3,
        sample_size=6,
        user_response=user_response,
        response_at=now - timedelta(minutes=fired_minutes_ago - 3) if user_response else None,
        parent_firing_id=parent_firing_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_empty_history_returns_zeros(client, db):
    r = client.get("/v1/analytics/pause_prediction")
    body = r.json()
    assert r.status_code == 200
    assert body["summary"]["total_fires"] == 0
    assert body["summary"]["acceptance_rate"] == 0.0
    assert body["summary"]["snooze_refires_excluded"] == 0
    assert body["by_mechanism"] == [
        {"mechanism": "clock_anchor", "fires": 0, "reconciled": 0, "accepted": 0, "acceptance_rate": 0.0},
        {"mechanism": "work_rhythm", "fires": 0, "reconciled": 0, "accepted": 0, "acceptance_rate": 0.0},
    ]


def test_acceptance_rate_uses_reconciled_denominator(db, client):
    # 3 accepted, 1 no_response, 1 unreconciled → rate = 3/4 = 0.75
    _seed(db, user_response="pause_now")
    _seed(db, user_response="pause_now")
    _seed(db, user_response="pause_now")
    _seed(db, user_response="no_response")
    _seed(db, user_response=None)

    r = client.get("/v1/analytics/pause_prediction")
    body = r.json()
    assert body["summary"]["total_fires"] == 5
    assert body["summary"]["total_reconciled"] == 4
    assert body["summary"]["total_unreconciled"] == 1
    assert body["summary"]["accepted"] == 3
    assert body["summary"]["no_response"] == 1
    assert body["summary"]["acceptance_rate"] == 0.75


def test_snooze_refires_excluded_from_summary(db, client):
    parent = _seed(db, user_response="snooze")
    # Re-fire from the snooze chain
    _seed(db, user_response="pause_now", parent_firing_id=parent.firing_id)
    # A plain accepted primary firing
    _seed(db, user_response="pause_now")

    r = client.get("/v1/analytics/pause_prediction")
    body = r.json()
    # Primary-only count: parent (snooze) + plain-accepted = 2
    assert body["summary"]["total_fires"] == 2
    # snooze refire was excluded
    assert body["summary"]["snooze_refires_excluded"] == 1
    # Acceptance rate denominator = reconciled primaries (both counted);
    # numerator = primaries marked pause_now (plain-accepted only —
    # the parent's outcome is 'snooze', not 'pause_now').
    assert body["summary"]["accepted"] == 1
    assert body["summary"]["acceptance_rate"] == 0.5


def test_by_mechanism_split(db, client):
    _seed(db, mechanism="clock_anchor", user_response="pause_now")
    _seed(db, mechanism="clock_anchor", user_response="no_response")
    _seed(db, mechanism="work_rhythm", user_response="pause_now")
    _seed(db, mechanism="work_rhythm", user_response="pause_now")

    r = client.get("/v1/analytics/pause_prediction")
    body = r.json()
    clock = next(m for m in body["by_mechanism"] if m["mechanism"] == "clock_anchor")
    rhythm = next(m for m in body["by_mechanism"] if m["mechanism"] == "work_rhythm")
    assert clock == {"mechanism": "clock_anchor", "fires": 2, "reconciled": 2, "accepted": 1, "acceptance_rate": 0.5}
    assert rhythm == {"mechanism": "work_rhythm", "fires": 2, "reconciled": 2, "accepted": 2, "acceptance_rate": 1.0}


def test_other_user_rows_are_not_visible(db, client):
    """Scoping defense: caller is user_id=1; seeded rows for user_id=2 must not leak."""
    _seed(db, user_id=USER_ID, user_response="pause_now")
    _seed(db, user_id=OTHER_USER_ID, user_response="pause_now")
    _seed(db, user_id=OTHER_USER_ID, user_response="pause_now")
    _seed(db, user_id=OTHER_USER_ID, user_response="pause_now")

    r = client.get("/v1/analytics/pause_prediction")
    body = r.json()
    # Only the caller's 1 row — the other user's 3 must be filtered out.
    assert body["summary"]["total_fires"] == 1
    assert body["summary"]["accepted"] == 1
