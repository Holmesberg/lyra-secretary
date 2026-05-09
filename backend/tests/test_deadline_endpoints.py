"""Phase F — deadline CRUD endpoint tests.

Covers:
- POST /v1/deadlines (happy path, 401 unauth)
- GET /v1/deadlines (list, state filter, voided exclusion)
- GET /v1/deadlines/{id} (happy, 404 not-found, 404 cross-user)
- PUT /v1/deadlines/{id} (field updates, valid transitions, invalid
  transitions rejected, terminal-state rejection, idempotent same-state)
- DELETE /v1/deadlines/{id} (soft-delete, idempotent, 404 not-found)
- voided_at_guard discipline: voided rows excluded by default

The TaskManager auto-transition planned→active on first task bind is
covered separately in test_create_task_with_deadline.py — not retested here.
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models import Deadline, Task, User
from app.db.scoping import set_current_user_id
from app.main import app


client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
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


def _create_deadline_payload(title="Hackathon", days_out=7):
    return {
        "title": title,
        "due_at_utc": (datetime.utcnow() + timedelta(days=days_out)).isoformat(),
        "description": "submit final speller backend",
        "category_hint": "academic",
    }


# ── POST /v1/deadlines ─────────────────────────────────────────────


def test_create_deadline_happy_path(db):
    user = _make_user(db, "post1@example.com")
    set_current_user_id(user.user_id)

    resp = client.post("/v1/deadlines", json=_create_deadline_payload())
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["title"] == "Hackathon"
    assert data["state"] == "planned"  # initial state
    assert data["voided_at"] is None
    assert data["completed_at"] is None
    assert data["user_id"] == user.user_id


def test_response_datetimes_carry_explicit_utc_offset(db):
    """Regression — Apr 27 dogfood: deadline created at 18:00 Cairo
    rendered as 3pm in the list view because the response emitted naive
    UTC datetimes ("2026-05-04T15:00:00") and `new Date(...)` in the
    browser parsed them as LOCAL. Schema field_serializer now stamps
    UTC explicitly. Pin that here so the bug can't silently come back.
    """
    user = _make_user(db, "tz@example.com")
    set_current_user_id(user.user_id)

    resp = client.post("/v1/deadlines", json=_create_deadline_payload())
    data = resp.json()
    # Aware datetimes serialize with either "+00:00" or "Z" suffix; both
    # are valid ISO 8601 UTC markers and both unambiguous to JS Date.
    for field in ("due_at_utc", "created_at"):
        s = data[field]
        assert s.endswith("+00:00") or s.endswith("Z"), (
            f"{field} lost its UTC marker: {s!r}"
        )


def _hdr(uid: int) -> dict:
    """Auth header for TestClient. UserScopeMiddleware reads X-User-Id and
    overwrites ContextVar — passing the header is the canonical way to
    simulate an authed request for a specific user.
    """
    return {"X-User-Id": str(uid)}


# ── GET /v1/deadlines (list) ─────────────────────────────────────


def test_list_deadlines_excludes_voided_by_default(db):
    user = _make_user(db, "list1@example.com")

    # Seed: 2 active, 1 voided
    for i in range(2):
        client.post("/v1/deadlines", json=_create_deadline_payload(title=f"Active {i}"), headers=_hdr(user.user_id))
    voided_resp = client.post("/v1/deadlines", json=_create_deadline_payload(title="Voided"), headers=_hdr(user.user_id))
    voided_id = voided_resp.json()["deadline_id"]
    client.delete(f"/v1/deadlines/{voided_id}", headers=_hdr(user.user_id))

    resp = client.get("/v1/deadlines", headers=_hdr(user.user_id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert all(d["voided_at"] is None for d in data["deadlines"])


def test_list_deadlines_state_filter(db):
    user = _make_user(db, "list2@example.com")
    h = _hdr(user.user_id)

    for i in range(2):
        client.post("/v1/deadlines", json=_create_deadline_payload(title=f"D{i}"), headers=h)

    deadlines = client.get("/v1/deadlines", headers=h).json()["deadlines"]
    advance_id = deadlines[0]["deadline_id"]
    client.put(f"/v1/deadlines/{advance_id}", json={"state": "active"}, headers=h)

    planned = client.get("/v1/deadlines?state=planned", headers=h).json()
    active = client.get("/v1/deadlines?state=active", headers=h).json()
    assert planned["total"] == 1
    assert active["total"] == 1
    assert active["deadlines"][0]["state"] == "active"


def test_list_deadlines_includes_voided_when_asked(db):
    user = _make_user(db, "list3@example.com")
    h = _hdr(user.user_id)

    voided_resp = client.post("/v1/deadlines", json=_create_deadline_payload(title="Will-void"), headers=h)
    voided_id = voided_resp.json()["deadline_id"]
    client.delete(f"/v1/deadlines/{voided_id}", headers=h)

    resp = client.get("/v1/deadlines?include_voided=true", headers=h)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["deadlines"][0]["voided_at"] is not None


def test_list_deadlines_cross_user_isolation(db):
    user_a = _make_user(db, "alice@example.com")
    user_b = _make_user(db, "bob@example.com")

    client.post(
        "/v1/deadlines",
        json=_create_deadline_payload(title="Alice's deadline"),
        headers=_hdr(user_a.user_id),
    )

    resp = client.get("/v1/deadlines", headers=_hdr(user_b.user_id))
    assert resp.status_code == 200
    # Bob sees zero — Alice's deadline is invisible
    assert resp.json()["total"] == 0


# ── GET /v1/deadlines/{id} ───────────────────────────────────────


def test_get_deadline_happy_path(db):
    user = _make_user(db, "get1@example.com")
    h = _hdr(user.user_id)

    created = client.post("/v1/deadlines", json=_create_deadline_payload(), headers=h).json()
    resp = client.get(f"/v1/deadlines/{created['deadline_id']}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["deadline_id"] == created["deadline_id"]


def test_get_deadline_not_found(db):
    user = _make_user(db, "get2@example.com")
    resp = client.get(f"/v1/deadlines/{uuid4()}", headers=_hdr(user.user_id))
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"] == "deadline_not_found"


def test_get_deadline_cross_user_returns_404(db):
    """Cross-user access returns 404 (not 403) to avoid existence-leak."""
    user_a = _make_user(db, "a-getx@example.com")
    user_b = _make_user(db, "b-getx@example.com")

    created = client.post(
        "/v1/deadlines",
        json=_create_deadline_payload(),
        headers=_hdr(user_a.user_id),
    ).json()

    resp = client.get(
        f"/v1/deadlines/{created['deadline_id']}",
        headers=_hdr(user_b.user_id),
    )
    assert resp.status_code == 404


# ── PUT /v1/deadlines/{id} ───────────────────────────────────────


def test_update_deadline_field_changes(db):
    user = _make_user(db, "put1@example.com")
    set_current_user_id(user.user_id)

    created = client.post("/v1/deadlines", json=_create_deadline_payload()).json()
    resp = client.put(
        f"/v1/deadlines/{created['deadline_id']}",
        json={"title": "Renamed", "category_hint": "personal"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Renamed"
    assert data["category_hint"] == "personal"


@pytest.mark.parametrize("from_state,to_state", [
    ("planned", "active"),
    ("planned", "skipped"),
    ("active", "completed"),
    ("active", "skipped"),
])
def test_valid_state_transitions(db, from_state, to_state):
    user = _make_user(db, f"transition-{from_state}-{to_state}@example.com")
    set_current_user_id(user.user_id)

    created = client.post("/v1/deadlines", json=_create_deadline_payload()).json()
    deadline_id = created["deadline_id"]

    # If from_state isn't 'planned' (the default), advance there first.
    if from_state == "active":
        client.put(f"/v1/deadlines/{deadline_id}", json={"state": "active"})

    resp = client.put(f"/v1/deadlines/{deadline_id}", json={"state": to_state})
    assert resp.status_code == 200, resp.text
    assert resp.json()["state"] == to_state
    if to_state == "completed":
        assert resp.json()["completed_at"] is not None


@pytest.mark.parametrize("invalid_transition", [
    # planned → completed used to be in this list; unlocked Apr 27 for
    # the no-bind manual-complete path. See
    # test_planned_to_completed_no_bind_path below.
    ("active", "planned"),     # active → planned is NOT allowed
])
def test_invalid_state_transitions_rejected(db, invalid_transition):
    from_state, to_state = invalid_transition
    user = _make_user(db, f"invalid-{from_state}-{to_state}@example.com")
    set_current_user_id(user.user_id)

    created = client.post("/v1/deadlines", json=_create_deadline_payload()).json()
    deadline_id = created["deadline_id"]

    if from_state == "active":
        client.put(f"/v1/deadlines/{deadline_id}", json={"state": "active"})

    resp = client.put(f"/v1/deadlines/{deadline_id}", json={"state": to_state})
    assert resp.status_code == 400
    assert "invalid_transition" in resp.json()["detail"]["error"]


def test_terminal_state_rejects_lateral_transitions(db):
    """Once 'completed', no LATERAL user-driven transitions allowed
    (e.g. completed → skipped is nonsensical). Reopen to planned IS
    allowed — see test_skipped_reopen_to_planned + sibling.
    """
    user = _make_user(db, "terminal@example.com")
    set_current_user_id(user.user_id)

    created = client.post("/v1/deadlines", json=_create_deadline_payload()).json()
    deadline_id = created["deadline_id"]

    # planned → active → completed
    client.put(f"/v1/deadlines/{deadline_id}", json={"state": "active"})
    client.put(f"/v1/deadlines/{deadline_id}", json={"state": "completed"})

    # Lateral transition (completed → skipped): rejected
    resp = client.put(f"/v1/deadlines/{deadline_id}", json={"state": "skipped"})
    assert resp.status_code == 400
    assert "invalid_transition" in resp.json()["detail"]["error"]


def test_planned_to_completed_no_bind_path(db):
    """A deadline can be marked complete directly from `planned` without
    a task ever being bound. Apr 27 dogfood — operator hit
    `deadline_invalid_transition: planned -> completed` because the
    prior graph forced planned → active → completed and `active` only
    fires automatically when a task binds. Operators completing a
    deadline manually (e.g. "I finished this offline") need a direct
    path.
    """
    user = _make_user(db, "no-bind-complete@example.com")
    set_current_user_id(user.user_id)

    created = client.post("/v1/deadlines", json=_create_deadline_payload()).json()
    deadline_id = created["deadline_id"]
    assert created["state"] == "planned"

    resp = client.put(
        f"/v1/deadlines/{deadline_id}", json={"state": "completed"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["state"] == "completed"


def test_missed_to_completed_late_completion_path(db):
    """A missed deadline can be marked complete without reopening first.

    The sweeper marks overdue active deadlines as `missed`, but that state is
    not evidence that the real-world obligation was never completed. The user
    needs the same one-click completion path after the due time passes.
    """
    user = _make_user(db, "missed-complete@example.com")
    set_current_user_id(user.user_id)

    created = client.post("/v1/deadlines", json=_create_deadline_payload()).json()
    deadline_id = created["deadline_id"]
    row = db.query(Deadline).filter(Deadline.deadline_id == deadline_id).first()
    row.state = "missed"
    row.due_at_utc = datetime.utcnow() - timedelta(days=1)
    db.commit()

    resp = client.put(
        f"/v1/deadlines/{deadline_id}", json={"state": "completed"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["state"] == "completed"
    assert data["completed_at"] is not None


def test_skipped_reopen_to_planned(db):
    """Apr 27 dogfood — operator misclicked 'Mark skipped' in the
    DeadlineModal and lost the ability to act on the deadline. Reopen
    to planned must be a user-driven path so the recovery is self-
    service rather than DB-only.
    """
    user = _make_user(db, "reopen@example.com")
    set_current_user_id(user.user_id)

    created = client.post("/v1/deadlines", json=_create_deadline_payload()).json()
    deadline_id = created["deadline_id"]

    # Skip the deadline (mistake)
    skip_resp = client.put(f"/v1/deadlines/{deadline_id}", json={"state": "skipped"})
    assert skip_resp.status_code == 200
    assert skip_resp.json()["state"] == "skipped"

    # Reopen — back to planned
    reopen = client.put(f"/v1/deadlines/{deadline_id}", json={"state": "planned"})
    assert reopen.status_code == 200, reopen.text
    assert reopen.json()["state"] == "planned"


def test_completed_reopen_to_planned(db):
    """Same recovery path from completed → planned (rare misclick,
    but symmetric with skipped recovery)."""
    user = _make_user(db, "completed-reopen@example.com")
    set_current_user_id(user.user_id)

    created = client.post("/v1/deadlines", json=_create_deadline_payload()).json()
    deadline_id = created["deadline_id"]

    client.put(f"/v1/deadlines/{deadline_id}", json={"state": "active"})
    client.put(f"/v1/deadlines/{deadline_id}", json={"state": "completed"})

    reopen = client.put(f"/v1/deadlines/{deadline_id}", json={"state": "planned"})
    assert reopen.status_code == 200
    assert reopen.json()["state"] == "planned"


def test_idempotent_same_state_transition(db):
    """state=current_state is a no-op (silent allow)."""
    user = _make_user(db, "idem@example.com")
    set_current_user_id(user.user_id)

    created = client.post("/v1/deadlines", json=_create_deadline_payload()).json()
    deadline_id = created["deadline_id"]

    # Twice: planned → planned should not error
    resp = client.put(f"/v1/deadlines/{deadline_id}", json={"state": "planned"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "planned"


def test_update_voided_state_rejected_by_pydantic(db):
    """Pydantic schema rejects 'voided' as a user-set state value."""
    user = _make_user(db, "noVoidViaPut@example.com")
    set_current_user_id(user.user_id)

    created = client.post("/v1/deadlines", json=_create_deadline_payload()).json()
    resp = client.put(
        f"/v1/deadlines/{created['deadline_id']}",
        json={"state": "voided"},
    )
    # Pydantic schema validator rejects this before reaching the manager.
    assert resp.status_code == 422


def test_update_deadline_not_found(db):
    user = _make_user(db, "notfound@example.com")
    set_current_user_id(user.user_id)

    resp = client.put(f"/v1/deadlines/{uuid4()}", json={"title": "Foo"})
    assert resp.status_code == 404


# ── DELETE /v1/deadlines/{id} ────────────────────────────────────


def test_delete_soft_deletes(db):
    user = _make_user(db, "del1@example.com")
    set_current_user_id(user.user_id)

    created = client.post("/v1/deadlines", json=_create_deadline_payload()).json()
    deadline_id = created["deadline_id"]

    resp = client.delete(f"/v1/deadlines/{deadline_id}")
    assert resp.status_code == 204

    # GET excludes voided by default → 404
    follow_up = client.get(f"/v1/deadlines/{deadline_id}")
    assert follow_up.status_code == 404


def test_delete_idempotent(db):
    user = _make_user(db, "del2@example.com")
    set_current_user_id(user.user_id)

    created = client.post("/v1/deadlines", json=_create_deadline_payload()).json()
    deadline_id = created["deadline_id"]

    client.delete(f"/v1/deadlines/{deadline_id}")
    second = client.delete(f"/v1/deadlines/{deadline_id}")
    # Second delete: still 204 (idempotent)
    assert second.status_code == 204


def test_delete_not_found(db):
    user = _make_user(db, "del3@example.com")
    set_current_user_id(user.user_id)

    resp = client.delete(f"/v1/deadlines/{uuid4()}")
    assert resp.status_code == 404
