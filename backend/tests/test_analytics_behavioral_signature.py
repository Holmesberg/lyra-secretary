"""GET /v1/analytics/behavioral_signature — operator-only; mirrors JARVIS aggregate."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.db.models import User
from app.main import app
from tests.conftest import auth_headers

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clean_users(db):
    db.rollback()
    db.query(User).delete()
    db.commit()
    yield
    db.rollback()
    db.query(User).delete()
    db.commit()


def _user(db, *, email: str, is_operator: bool) -> User:
    u = User(
        email=email,
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


def test_behavioral_signature_403_non_operator(db):
    u = _user(db, email="student@uni.test", is_operator=False)
    r = client.get(
        "/v1/analytics/behavioral_signature",
        headers=auth_headers(u.user_id),
    )
    assert r.status_code == 403


def test_behavioral_signature_200_operator_cold_start(db):
    u = _user(db, email="operator@uni.test", is_operator=True)
    r = client.get(
        "/v1/analytics/behavioral_signature?window_days=7",
        headers=auth_headers(u.user_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["window_days"] == 7
    assert body["n_sessions"] == 0
    assert "valence_distribution" in body
    assert "pause_distribution" in body
