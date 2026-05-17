"""
Shared test fixtures for integration tests.

Pytest may load this file as `conftest`, while test modules may also import
`tests.conftest` for helpers. Both names must point at the same in-memory
SQLite engine, otherwise tests seed one database while FastAPI endpoints read
another. The stable sys.modules key below keeps that state canonical across
both import paths.
"""
import sys
from types import SimpleNamespace

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.db.scoping import get_current_user_id, set_current_user_id
from app.main import app

_STATE_MODULE = "_lyra_tests_shared_db_state"
_state = sys.modules.get(_STATE_MODULE)
if _state is not None:
    _engine = _state.engine
    TestingSession = _state.TestingSession
else:
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(bind=_engine)
    sys.modules[_STATE_MODULE] = SimpleNamespace(
        engine=_engine,
        TestingSession=TestingSession,
    )


def _request_user_id(request: Request) -> int:
    raw = request.headers.get("X-User-Id")
    if raw is None:
        return 1
    try:
        return int(raw)
    except ValueError:
        return 1


def _override_get_db(request: Request):
    scope_set_here = False
    if get_current_user_id() is None:
        set_current_user_id(_request_user_id(request))
        scope_set_here = True
    db = TestingSession()
    try:
        yield db
    finally:
        if scope_set_here:
            set_current_user_id(None)
        db.close()


def _install_test_overrides() -> None:
    app.state.allow_test_identity_header = True
    app.dependency_overrides[get_db] = _override_get_db
    try:
        import app.services.security_audit as security_audit

        security_audit.SessionLocal = TestingSession
    except Exception:
        pass


_install_test_overrides()


@pytest.fixture(autouse=True)
def _keep_test_overrides_installed():
    _install_test_overrides()
    yield
    _install_test_overrides()


@pytest.fixture
def db():
    """Provide a DB session for seeding test data."""
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """Provide a TestClient backed by the shared test DB."""
    return TestClient(app, raise_server_exceptions=False)


def auth_headers(user_id: int) -> dict:
    """Build an X-User-Id header dict for TestClient requests.

    Always use this when calling client.{post,get,put,delete} from a test.
    Without it, UserScopeMiddleware defaults to user_id=1 silently, so a
    test that seeded user_id=77's data and then forgot the header runs as
    user_id=1 and most assertions fall through to coincidental pass. See
    `docs/testing_patterns.md` for the full pattern guide.

    Pattern:
        from tests.conftest import auth_headers
        client.post("/v1/...", json={...}, headers=auth_headers(77))
    """
    return {"X-User-Id": str(user_id)}
