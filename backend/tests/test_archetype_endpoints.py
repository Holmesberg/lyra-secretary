"""Integration tests for archetype survey + skip + retrofit-dismiss.

Focused on the highest-risk gap: does the full submit-flow score
correctly, write ArchetypeAssignment, and update User.archetype_id
so the next bias_factor_lookup picks up the new archetype?
"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import users as users_module
from app.db.models import Archetype, ArchetypeAssignment, User
from app.main import app
from tests.conftest import TestingSession

client = TestClient(app, raise_server_exceptions=False)


class _FakeIdempotencyRedis:
    IDEMPOTENCY_PENDING = "__pending__"

    def __init__(self):
        self.values = {}

    def _key(self, key, user_id):
        return (int(user_id), key)

    def check_idempotency(self, key, user_id=None):
        return self.values.get(self._key(key, user_id))

    def is_idempotency_pending(self, value):
        return value == self.IDEMPOTENCY_PENDING

    def reserve_idempotency(self, key, ttl_seconds=30, user_id=None):
        scoped = self._key(key, user_id)
        if scoped in self.values:
            return False
        self.values[scoped] = self.IDEMPOTENCY_PENDING
        return True

    def set_idempotency(
        self,
        key,
        response_json,
        ttl_seconds=30,
        user_id=None,
    ):
        self.values[self._key(key, user_id)] = response_json

    def clear_idempotency(self, key, user_id=None):
        return int(self.values.pop(self._key(key, user_id), None) is not None)


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


def _disciplined_lark_payload():
    return {
        "meq": [5, 4, 4, 4, 5],
        "bfi_c": [5, 1],
        "bscs": [5, 1, 1, 1, 1, 5, 1, 5, 1, 1, 5, 1, 1],
        "gp": [1, 1, 1, 1, 1, 1, 1, 1, 1],
    }


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
        json=_disciplined_lark_payload(),
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


def test_survey_request_key_is_user_scoped_and_preserves_explicit_retakes(
    monkeypatch,
):
    fake_redis = _FakeIdempotencyRedis()
    monkeypatch.setattr(users_module, "RedisClient", lambda: fake_redis)
    db = TestingSession()
    try:
        _seed_archetypes(db)
        first_uid = _make_user(db, "idempotent-survey-first@example.com")
        second_uid = _make_user(db, "idempotent-survey-second@example.com")
    finally:
        db.close()

    shared_key = "survey-retry-1"
    first_headers = {
        "X-User-Id": str(first_uid),
        "X-Idempotency-Key": shared_key,
    }
    first = client.post(
        "/v1/users/me/archetype/survey",
        json=_disciplined_lark_payload(),
        headers=first_headers,
    )
    replay = client.post(
        "/v1/users/me/archetype/survey",
        json=_disciplined_lark_payload(),
        headers=first_headers,
    )
    other_user = client.post(
        "/v1/users/me/archetype/survey",
        json=_disciplined_lark_payload(),
        headers={
            "X-User-Id": str(second_uid),
            "X-Idempotency-Key": shared_key,
        },
    )
    retake = client.post(
        "/v1/users/me/archetype/survey",
        json=_disciplined_lark_payload(),
        headers={
            "X-User-Id": str(first_uid),
            "X-Idempotency-Key": "survey-retake-2",
        },
    )

    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    assert replay.json() == first.json()
    assert other_user.status_code == 200, other_user.text
    assert retake.status_code == 200, retake.text
    db = TestingSession()
    try:
        assert (
            db.query(ArchetypeAssignment)
            .filter(ArchetypeAssignment.user_id == first_uid)
            .count()
            == 2
        )
        assert (
            db.query(ArchetypeAssignment)
            .filter(ArchetypeAssignment.user_id == second_uid)
            .count()
            == 1
        )
    finally:
        db.close()


def test_latest_assignment_order_is_deterministic_for_me_and_skip():
    db = TestingSession()
    try:
        _seed_archetypes(db)
        uid = _make_user(db, "latest-assignment-order@example.com")
        assigned_at = datetime.utcnow()
        db.add_all(
            [
                ArchetypeAssignment(
                    user_id=uid,
                    archetype_id="diffuse_average",
                    assigned_at=assigned_at,
                    completed=False,
                    skipped_at=assigned_at,
                ),
                ArchetypeAssignment(
                    user_id=uid,
                    archetype_id="disciplined_lark",
                    assigned_at=assigned_at,
                    completed=True,
                    skipped_at=None,
                    raw_responses=_disciplined_lark_payload(),
                ),
            ]
        )
        user = db.query(User).filter(User.user_id == uid).one()
        user.archetype_id = "disciplined_lark"
        db.commit()
    finally:
        db.close()

    me = client.get("/v1/users/me", headers={"X-User-Id": str(uid)})
    skipped = client.post(
        "/v1/users/me/archetype/skip",
        headers={"X-User-Id": str(uid)},
    )

    assert me.status_code == 200, me.text
    assert me.json()["archetype_assignment_completed"] is True
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()["completed"] is False
    db = TestingSession()
    try:
        assert (
            db.query(ArchetypeAssignment)
            .filter(ArchetypeAssignment.user_id == uid)
            .count()
            == 3
        )
        assert db.query(User).filter(User.user_id == uid).one().archetype_id == (
            "diffuse_average"
        )
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
    assert resp.status_code == 422

    db = TestingSession()
    try:
        user = db.query(User).filter(User.user_id == uid).one()
        assert user.archetype_id is None
        assert (
            db.query(ArchetypeAssignment)
            .filter(ArchetypeAssignment.user_id == uid)
            .count()
            == 0
        )
    finally:
        db.close()


@pytest.mark.parametrize(
    ("instrument", "invalid_values"),
    [
        ("bfi_c", [0, 3]),
        ("bscs", [3] * 12 + [6]),
        ("gp", [3] * 8 + [0]),
    ],
)
def test_survey_rejects_each_out_of_range_instrument_without_writes(
    instrument,
    invalid_values,
):
    db = TestingSession()
    try:
        _seed_archetypes(db)
        uid = _make_user(db, f"range-{instrument}-test@example.com")
    finally:
        db.close()

    payload = {
        "meq": [3, 3, 3, 3, 3],
        "bfi_c": [3, 3],
        "bscs": [3] * 13,
        "gp": [3] * 9,
    }
    payload[instrument] = invalid_values
    resp = client.post(
        "/v1/users/me/archetype/survey",
        json=payload,
        headers={"X-User-Id": str(uid)},
    )

    assert resp.status_code == 422
    db = TestingSession()
    try:
        user = db.query(User).filter(User.user_id == uid).one()
        assert user.archetype_id is None
        assert (
            db.query(ArchetypeAssignment)
            .filter(ArchetypeAssignment.user_id == uid)
            .count()
            == 0
        )
    finally:
        db.close()


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
