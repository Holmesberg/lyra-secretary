import pytest

from app.core import security


def _public_runtime(monkeypatch, *, jwt_secret: str):
    monkeypatch.setattr(security.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(security.settings, "FRONTEND_URL", "https://lyraos.org")
    monkeypatch.setattr(security.settings, "JWT_SECRET", jwt_secret)


def test_public_runtime_rejects_default_jwt_secret(monkeypatch):
    _public_runtime(monkeypatch, jwt_secret=security.DEFAULT_JWT_SECRET)
    monkeypatch.delenv("NEXTAUTH_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        security.validate_runtime_jwt_secret()


def test_public_runtime_rejects_blank_jwt_secret(monkeypatch):
    _public_runtime(monkeypatch, jwt_secret="")
    monkeypatch.delenv("NEXTAUTH_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        security.validate_runtime_jwt_secret()


def test_public_runtime_rejects_frontend_backend_secret_mismatch(monkeypatch):
    strong_backend = "backend-secret-for-test-only-32chars"
    strong_frontend = "frontend-secret-for-test-only-32cha"
    _public_runtime(monkeypatch, jwt_secret=strong_backend)
    monkeypatch.setenv("NEXTAUTH_SECRET", strong_frontend)

    with pytest.raises(RuntimeError, match="NEXTAUTH_SECRET"):
        security.validate_runtime_jwt_secret()


def test_public_runtime_accepts_strong_matching_secret(monkeypatch):
    strong_secret = "shared-secret-for-test-only-32chars"
    _public_runtime(monkeypatch, jwt_secret=strong_secret)
    monkeypatch.setenv("NEXTAUTH_SECRET", strong_secret)

    security.validate_runtime_jwt_secret()
