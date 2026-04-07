"""
Shared test fixtures. All integration tests use one in-memory SQLite engine
registered as the get_db override. This prevents module-level overrides from
clobbering each other when pytest runs the full suite.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base import Base
from app.api.deps import get_db
from app.main import app

# One engine shared across all integration tests in this session
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
