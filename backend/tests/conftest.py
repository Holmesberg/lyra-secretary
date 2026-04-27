"""
Shared test fixtures. All integration tests use one in-memory SQLite engine
registered as the get_db override. This prevents module-level overrides from
clobbering each other when pytest runs the full suite.

Singleton guard: pytest loads this file as `conftest` (rootdir-anchored)
while `from tests.conftest import TestingSession` in other test files loads
it a SECOND time as `tests.conftest`. Without the guard below, the second
load creates a fresh in-memory engine + Session factory — the test fixtures
still point at the original engine but FastAPI's dependency override gets
re-registered to the second engine. The test writes to engine1, the
endpoint reads engine2 → ghost "missing rows" failures that only appear
in full-suite runs. We deduplicate by reusing whichever instance landed
in sys.modules first.
"""
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base import Base
from app.api.deps import get_db
from app.main import app

_twin = sys.modules.get("tests.conftest") if __name__ == "conftest" else sys.modules.get("conftest")
if _twin is not None and hasattr(_twin, "_engine"):
    _engine = _twin._engine
    TestingSession = _twin.TestingSession
else:
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(bind=_engine)


def _override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


# Register once — highest priority because conftest runs first
app.dependency_overrides[get_db] = _override_get_db


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
    Without it, UserScopeMiddleware defaults to user_id=1 silently — a
    test that seeded user_id=77's data and then forgot the header runs as
    user_id=1 and most assertions fall through to coincidental pass. See
    `docs/testing_patterns.md` for the full pattern guide.

    Pattern:
        from tests.conftest import auth_headers
        client.post("/v1/...", json={...}, headers=auth_headers(77))
    """
    return {"X-User-Id": str(user_id)}
