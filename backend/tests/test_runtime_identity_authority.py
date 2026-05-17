"""Wave 5 runtime identity authority regressions.

The app runtime may use Bearer/JWT identity only. X-User-Id remains as
pytest plumbing, but it must never authenticate unauthenticated manual HTTP
or override a bearer-resolved user.
"""
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy.exc import OperationalError

from app.core import security
from app.db.models import User
from app.main import app
from app.utils.me_cache import invalidate_me
from tests.conftest import auth_headers


def _upsert_user(db, user_id: int, email: str) -> None:
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        user = User(
            user_id=user_id,
            email=email,
            google_id=f"wave5-{user_id}",
            timezone="Africa/Cairo",
            is_operator=False,
            notion_enabled=False,
            created_at=datetime.utcnow(),
        )
        db.add(user)
    else:
        user.email = email
        user.google_id = f"wave5-{user_id}"
        user.timezone = "Africa/Cairo"
        user.is_operator = False
        user.notion_enabled = False
    db.commit()
    invalidate_me(user_id)


def test_bearer_scope_beats_x_user_id_header(client, db, monkeypatch):
    _upsert_user(db, 1, "wave5-header-user@example.test")
    _upsert_user(db, 15, "wave5-bearer-user@example.test")

    def _resolve_user_from_token(_token: str):
        return SimpleNamespace(user_id=15)

    monkeypatch.setattr(security, "resolve_user_from_token", _resolve_user_from_token)

    response = client.get(
        "/v1/users/me",
        headers={"Authorization": "Bearer wave5-test", "X-User-Id": "1"},
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == 15


def test_x_user_id_cannot_authenticate_runtime_http(client):
    previous = bool(getattr(app.state, "allow_test_identity_header", False))
    app.state.allow_test_identity_header = False
    try:
        response = client.get("/v1/users/me", headers={"X-User-Id": "1"})
    finally:
        app.state.allow_test_identity_header = previous

    assert response.status_code == 401


def test_x_user_id_still_available_to_explicit_test_harness(client, db):
    _upsert_user(db, 15, "wave5-test-harness@example.test")

    response = client.get("/v1/users/me", headers=auth_headers(15))

    assert response.status_code == 200
    assert response.json()["user_id"] == 15


def test_bearer_db_unavailable_fails_closed_as_platform_degradation(client, monkeypatch):
    def _resolve_user_from_token(_token: str):
        raise OperationalError("SELECT user", {}, Exception("pooler unavailable"))

    monkeypatch.setattr(security, "resolve_user_from_token", _resolve_user_from_token)

    response = client.get(
        "/v1/users/me",
        headers={"Authorization": "Bearer db-unavailable"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "authentication database temporarily unavailable"


def test_app_code_has_no_operator_identity_fallbacks():
    """Kernel guard: runtime code must not silently fall back to user_id=1."""

    offenders: list[str] = []
    forbidden_tokens = (
        "get_current_user_id() or 1",
        "get_current_user_id()or 1",
    )

    app_dir = Path(__file__).resolve().parents[1] / "app"
    for path in app_dir.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                offenders.append(f"{path.relative_to(app_dir.parent)}:{token}")

    assert offenders == []
