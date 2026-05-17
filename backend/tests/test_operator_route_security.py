"""Trusted-alpha operator/admin/JARVIS route gates."""
from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.db.models import User
from app.main import app
from tests.conftest import auth_headers


def _make_user(db, *, is_operator: bool) -> User:
    user = User(
        email=f"operator-route-{uuid4().hex[:8]}@example.test",
        timezone="Africa/Cairo",
        is_operator=is_operator,
        notion_enabled=False,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


OPERATOR_GET_PATHS = (
    "/v1/admin/dashboard",
    "/v1/admin/alpha_funnel",
    "/v1/admin/feedback",
    "/v1/jarvis/health",
    "/v1/analytics/behavioral_signature",
    "/v1/analytics/cortex/diagnostics",
    "/v1/analytics/output_surfaces/diagnostics",
    "/v1/health/env-invariants",
)


def test_non_operator_forbidden_on_operator_get_surfaces(client, db):
    user = _make_user(db, is_operator=False)

    for path in OPERATOR_GET_PATHS:
        response = client.get(path, headers=auth_headers(user.user_id))
        assert response.status_code == 403, f"{path}: {response.status_code} {response.text}"


def test_operator_can_reach_core_operator_get_surfaces(client, db, monkeypatch):
    operator = _make_user(db, is_operator=True)
    monkeypatch.setattr(
        "app.services.nvidia_nim_client.health_check",
        lambda: {"available": False, "model": "test", "reason": "mocked"},
    )

    for path in (
        "/v1/admin/alpha_funnel",
        "/v1/jarvis/health",
        "/v1/analytics/output_surfaces/diagnostics",
    ):
        response = client.get(path, headers=auth_headers(operator.user_id))
        assert response.status_code == 200, f"{path}: {response.status_code} {response.text}"


def test_unauthenticated_operator_surfaces_fail_closed_runtime():
    old_overrides = dict(app.dependency_overrides)
    app.dependency_overrides.pop(get_db, None)
    try:
        with TestClient(app, raise_server_exceptions=False) as runtime_client:
            for path in (
                "/v1/admin/alpha_funnel",
                "/v1/jarvis/health",
                "/v1/analytics/output_surfaces/diagnostics",
                "/v1/health/env-invariants",
            ):
                response = runtime_client.get(path)
                assert response.status_code == 401, (
                    f"{path}: {response.status_code} {response.text}"
                )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(old_overrides)


def test_x_user_id_cannot_authenticate_operator_surfaces_outside_test_harness():
    old_overrides = dict(app.dependency_overrides)
    previous = bool(getattr(app.state, "allow_test_identity_header", False))
    app.dependency_overrides.pop(get_db, None)
    app.state.allow_test_identity_header = False
    try:
        with TestClient(app, raise_server_exceptions=False) as runtime_client:
            response = runtime_client.get(
                "/v1/jarvis/health",
                headers={"X-User-Id": "1"},
            )
            assert response.status_code == 401
    finally:
        app.state.allow_test_identity_header = previous
        app.dependency_overrides.clear()
        app.dependency_overrides.update(old_overrides)
