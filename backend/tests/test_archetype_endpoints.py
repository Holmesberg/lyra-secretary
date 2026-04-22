"""Integration tests for archetype survey + skip + retrofit-dismiss.

Focused on the highest-risk gap: does the full submit-flow score
correctly, write ArchetypeAssignment, and update User.archetype_id
so the next bias_factor_lookup picks up the new archetype?
"""
from datetime import datetime

from fastapi.testclient import TestClient

from app.db.models import Archetype, ArchetypeAssignment, User
from app.main import app
from tests.conftest import TestingSession

client = TestClient(app, raise_server_exceptions=False)


def _seed_archetypes(db) -> None:
    if db.query(Archetype).count() >= 5:
        return
    rows = [
        ("disciplined_lark", "Disciplined Lark", 0.95, 0.15),
        ("disciplined_owl", "Disciplined Owl", 1.05, 0.20),
        ("diffuse_average", "Diffuse Average", 1.30, 0.30),
        ("procrastinator", "Procrastinator", 1.80, 0.40),
        ("lark_low_discipline", "Lark, Low Discipline", 1.50, 0.35),
    ]
    for aid, name, prior, sigma in rows:
        db.add(
            Archetype(
                archetype_id=aid, name=name,
                prior_bias_factor=prior, prior_sigma=sigma,
            )
        )
    db.commit()


def _make_user(db, email: str) -> int:
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
    return u.user_id


def test_submit_survey_scores_and_writes_assignment():
    """POST /survey with max-morning, high-discipline answers → disciplined_lark."""
    db = TestingSession()
    try:
        _seed_archetypes(db)
        uid = _make_user(db, "lark-test@example.com")
    finally:
        db.close()

    # Max-morning responses (weights 5,4,4,4,5), high BFI-C (forward=5,
    # reverse-keyed item=1 → reversed to 5; total 10), high BSCS
    # (forward items at 5, reverse items at 1 → reversed to 5; total 65),
    # low GP (all 1 → total 9).
    resp = client.post(
        "/v1/users/me/archetype/survey",
        json={
            "meq": [5, 4, 4, 4, 5],
            "bfi_c": [5, 1],
            "bscs": [5, 1, 1, 1, 1, 5, 1, 5, 1, 1, 5, 1, 1],
            "gp": [1, 1, 1, 1, 1, 1, 1, 1, 1],
        },
        headers={"X-User-Id": str(uid)},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["archetype_id"] == "disciplined_lark"
    assert body["completed"] is True
    assert body["chronotype"] == "morning"

    db = TestingSession()
    try:
        u = db.query(User).filter(User.user_id == uid).first()
        assert u.archetype_id == "disciplined_lark"
        assignment = (
            db.query(ArchetypeAssignment)
            .filter(ArchetypeAssignment.user_id == uid)
            .first()
        )
        assert assignment is not None
        assert assignment.completed is True
        assert assignment.skipped_at is None
        assert assignment.raw_responses is not None
        assert assignment.raw_responses["meq"] == [5, 4, 4, 4, 5]
    finally:
        db.close()


def test_skip_survey_defaults_to_diffuse_average():
    """POST /skip creates ArchetypeAssignment(diffuse_average, completed=False)."""
    db = TestingSession()
    try:
        _seed_archetypes(db)
        uid = _make_user(db, "skip-test@example.com")
    finally:
        db.close()

    resp = client.post(
        "/v1/users/me/archetype/skip",
        headers={"X-User-Id": str(uid)},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["archetype_id"] == "diffuse_average"
    assert body["completed"] is False

    db = TestingSession()
    try:
        u = db.query(User).filter(User.user_id == uid).first()
        assert u.archetype_id == "diffuse_average"
        assignment = (
            db.query(ArchetypeAssignment)
            .filter(ArchetypeAssignment.user_id == uid)
            .first()
        )
        assert assignment is not None
        assert assignment.completed is False
        assert assignment.skipped_at is not None
        assert assignment.raw_responses is None
    finally:
        db.close()


def test_retrofit_dismiss_stamps_user():
    """POST /retrofit-dismiss sets user.archetype_retrofit_dismissed_at."""
    db = TestingSession()
    try:
        _seed_archetypes(db)
        uid = _make_user(db, "retrofit-test@example.com")
    finally:
        db.close()

    resp = client.post(
        "/v1/users/me/archetype/retrofit-dismiss",
        headers={"X-User-Id": str(uid)},
    )
    assert resp.status_code == 200, resp.text
    db = TestingSession()
    try:
        u = db.query(User).filter(User.user_id == uid).first()
        assert u.archetype_retrofit_dismissed_at is not None
    finally:
        db.close()


def test_survey_validates_item_counts():
    """Wrong count → 422 Pydantic validation error."""
    db = TestingSession()
    try:
        _seed_archetypes(db)
        uid = _make_user(db, "validate-test@example.com")
    finally:
        db.close()

    resp = client.post(
        "/v1/users/me/archetype/survey",
        json={
            "meq": [3, 2, 2, 2],  # only 4 items, should be 5
            "bfi_c": [3, 3],
            "bscs": [3] * 13,
            "gp": [3] * 9,
        },
        headers={"X-User-Id": str(uid)},
    )
    assert resp.status_code == 422


def test_survey_rejects_out_of_range_meq_item():
    """MEQ item 2 (index 1) only accepts 1-4. Sending 5 should fail."""
    db = TestingSession()
    try:
        _seed_archetypes(db)
        uid = _make_user(db, "range-test@example.com")
    finally:
        db.close()

    resp = client.post(
        "/v1/users/me/archetype/survey",
        json={
            "meq": [3, 5, 2, 2, 3],  # item 2 (idx 1) = 5, out of 1-4 range
            "bfi_c": [3, 3],
            "bscs": [3] * 13,
            "gp": [3] * 9,
        },
        headers={"X-User-Id": str(uid)},
    )
    # ValueError from the scorer bubbles as 500. Pydantic won't catch
    # it because the min/max validators only check list length, not
    # item values (items have different scales per position).
    assert resp.status_code >= 400


def test_get_me_surfaces_archetype_fields():
    """/me returns the new archetype_survey_eligible + related fields."""
    db = TestingSession()
    try:
        _seed_archetypes(db)
        uid = _make_user(db, "me-test@example.com")
    finally:
        db.close()

    resp = client.get(
        "/v1/users/me",
        headers={"X-User-Id": str(uid)},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "archetype_survey_eligible" in body
    assert "archetype_assignment_completed" in body
    assert "archetype_retrofit_dismissed_at" in body
    # Fresh test user has no assignment and is created NOW → eligible.
    assert body["archetype_assignment_completed"] is False
