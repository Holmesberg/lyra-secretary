import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.main import app
from app.db.models import User
from tests.conftest import auth_headers


def _contract() -> dict:
    return json.loads((Path(__file__).resolve().parents[2] / "runtime_topology.json").read_text())


def test_runtime_topology_contract_keeps_public_off_localhost():
    public = _contract()["topologies"]["public"]

    assert public["frontend_origin"] == "https://lyraos.org"
    assert public["api_origin"] == "https://api.lyraos.org"
    assert public["nextauth_url"] == "https://lyraos.org"
    assert "localhost" not in public["frontend_origin"]
    assert "localhost" not in public["api_origin"]
    assert "localhost" not in public["nextauth_url"]


def test_runtime_topology_contract_keeps_local_off_public_api():
    local = _contract()["topologies"]["local"]

    assert local["frontend_origin"] == "http://localhost:3000"
    assert local["api_origin"] == "http://localhost:8000"
    assert local["nextauth_url"] == "http://localhost:3000"
    assert "api.lyraos.org" not in local["api_origin"]
    assert "lyraos.org" not in local["frontend_origin"]
    assert "lyraos.org" not in local["nextauth_url"]


def test_backend_topology_self_report_public_and_local(client):
    public = client.get("/v1/health/topology", headers={"host": "api.lyraos.org"}).json()
    assert public["topology_class"] == "public"
    assert public["api_origin"] == "https://api.lyraos.org"
    assert public["expected_frontend_origin"] == "https://lyraos.org"
    assert public["verified_topology"] is True

    local = client.get("/v1/health/topology", headers={"host": "localhost:8000"}).json()
    assert local["topology_class"] == "local"
    assert local["api_origin"] == "http://localhost:8000"
    assert local["expected_frontend_origin"] == "http://localhost:3000"
    assert local["verified_topology"] is True


def test_cors_accepts_declared_origins_only():
    with TestClient(app, raise_server_exceptions=False) as client:
        for origin in _contract()["declared_browser_origins"]:
            response = client.options(
                "/v1/users/me",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "authorization,x-idempotency-key",
                },
            )
            assert response.status_code == 200
            assert response.headers.get("access-control-allow-origin") == origin
            assert "x-idempotency-key" in (
                response.headers.get("access-control-allow-headers", "").lower()
            )

        rogue = client.options(
            "/v1/users/me",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,x-idempotency-key",
            },
        )
        assert rogue.headers.get("access-control-allow-origin") is None
        assert rogue.status_code in {400, 403}


def test_topology_signed_diagnostics_remain_operator_only(db, client):
    operator = User(
        email=f"topology-operator-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        is_operator=True,
    )
    non_operator = User(
        email=f"topology-non-operator-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        is_operator=False,
    )
    db.add_all([operator, non_operator])
    db.commit()

    denied = client.get(
        "/v1/analytics/output_surfaces/diagnostics",
        headers=auth_headers(non_operator.user_id),
    )
    assert denied.status_code == 403

    allowed = client.get(
        "/v1/analytics/output_surfaces/diagnostics",
        headers={**auth_headers(operator.user_id), "host": "api.lyraos.org"},
    )
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["topology"]["topology_class"] == "public"
    assert body["topology"]["verified_topology"] is True


def test_no_auth_product_endpoints_fail_closed_under_topology_contract():
    old_overrides = dict(app.dependency_overrides)
    app.dependency_overrides.pop(get_db, None)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            for path in (
                "/v1/users/me",
                "/v1/analytics/insights",
                "/v1/analytics/archetype/proximity?days=14",
            ):
                response = client.get(path)
                assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(old_overrides)
