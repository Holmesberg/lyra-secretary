"""Parked JARVIS endpoint tests.

JARVIS is no longer an active runtime assistant. These tests preserve the
operator gate and prove the compatibility endpoints do not call models, tools,
or mutation paths while historical JarvisInvocation rows remain exportable and
deletable through the data-sovereignty registry.
"""
from datetime import datetime
from uuid import uuid4

import pytest

from app.db.models import Deadline, JarvisInvocation, Task, User
from app.db.scoping import set_current_user_id
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.query(JarvisInvocation).delete()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.query(JarvisInvocation).delete()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()


def _make_user(db, *, is_operator: bool = False) -> User:
    user = User(
        email=f"u{uuid4().hex[:8]}@test",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=is_operator,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _assert_jarvis_disabled(response):
    assert response.status_code == 410, response.text
    detail = response.json()["detail"]
    assert detail["error"] == "jarvis_disabled"
    assert detail["status"] == "parked"


def test_jarvis_ask_non_operator_forbidden(client, db):
    user = _make_user(db, is_operator=False)
    response = client.post(
        "/v1/jarvis/ask",
        json={"message": "hi", "history": []},
        headers=auth_headers(user.user_id),
    )
    assert response.status_code == 403


def test_jarvis_ask_unauthenticated(client):
    response = client.post("/v1/jarvis/ask", json={"message": "hi", "history": []})
    assert response.status_code == 401


def test_jarvis_health_non_operator_forbidden(client, db):
    user = _make_user(db, is_operator=False)
    response = client.get("/v1/jarvis/health", headers=auth_headers(user.user_id))
    assert response.status_code == 403


def test_operator_jarvis_ask_is_parked_and_does_not_write(client, db):
    operator = _make_user(db, is_operator=True)

    response = client.post(
        "/v1/jarvis/ask",
        json={"message": "create a task", "history": []},
        headers=auth_headers(operator.user_id),
    )

    _assert_jarvis_disabled(response)
    assert db.query(JarvisInvocation).count() == 0
    assert db.query(Task).count() == 0


def test_operator_jarvis_confirm_is_parked_and_does_not_write(client, db):
    operator = _make_user(db, is_operator=True)

    response = client.post(
        "/v1/jarvis/confirm",
        json={
            "tool_call_id": "call_parked",
            "name": "create_task",
            "args": {"title": "must not be created"},
            "history": [],
            "confirmed": True,
        },
        headers=auth_headers(operator.user_id),
    )

    _assert_jarvis_disabled(response)
    assert db.query(JarvisInvocation).count() == 0
    assert db.query(Task).count() == 0


def test_operator_jarvis_health_is_parked(client, db):
    operator = _make_user(db, is_operator=True)

    response = client.get("/v1/jarvis/health", headers=auth_headers(operator.user_id))

    _assert_jarvis_disabled(response)
