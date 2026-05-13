"""Wave 7A idempotency scoping regressions."""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.db.models import Task, User
from app.db.scoping import set_current_user_id
from tests.conftest import TestingSession, auth_headers


class _FakeRedisClient:
    store: dict[tuple[str | None, str], str] = {}

    def check_idempotency(self, key: str, user_id=None):
        return self.store.get((str(user_id) if user_id is not None else None, key))

    def set_idempotency(self, key: str, response_json: str, ttl_seconds: int = 30, user_id=None):
        self.store[(str(user_id) if user_id is not None else None, key)] = response_json

    def queue_notion_sync(self, *args, **kwargs):
        return None

    def cache_undo_action(self, *args, **kwargs):
        return None

    def set_last_task(self, *args, **kwargs):
        return None


@pytest.fixture
def two_users(db, monkeypatch):
    _FakeRedisClient.store.clear()
    monkeypatch.setattr("app.api.v1.endpoints.tasks.RedisClient", _FakeRedisClient)
    monkeypatch.setattr("app.services.task_manager.RedisClient", _FakeRedisClient)

    set_current_user_id(None)
    wipe = TestingSession()
    try:
        wipe.execute(text("DELETE FROM stopwatch_session"))
        wipe.execute(text("DELETE FROM task"))
        wipe.execute(text("DELETE FROM user"))
        wipe.commit()
    finally:
        wipe.close()

    now = datetime.utcnow()
    db.add_all([
        User(user_id=15, email="idempotency-a@example.test", is_operator=False, notion_enabled=False, created_at=now),
        User(user_id=16, email="idempotency-b@example.test", is_operator=False, notion_enabled=False, created_at=now),
    ])
    db.commit()
    yield
    set_current_user_id(None)


def _future_payload(title: str, offset_minutes: int) -> dict:
    start = datetime.utcnow() + timedelta(minutes=offset_minutes)
    end = start + timedelta(minutes=30)
    return {
        "title": title,
        "start": start.replace(microsecond=0).isoformat() + "Z",
        "end": end.replace(microsecond=0).isoformat() + "Z",
        "force": True,
    }


def _task_user_id(task_id: str) -> int:
    set_current_user_id(None)
    session = TestingSession()
    try:
        task = session.query(Task).filter(Task.task_id == task_id).first()
        assert task is not None
        return task.user_id
    finally:
        session.close()


def test_create_idempotency_key_is_scoped_by_user(client, two_users):
    key = "same-client-generated-key"

    first = client.post(
        "/v1/create",
        json=_future_payload("user 15 first", 120),
        headers={**auth_headers(15), "X-Idempotency-Key": key},
    )
    assert first.status_code == 200, first.text
    first_id = first.json()["task_id"]

    replay = client.post(
        "/v1/create",
        json=_future_payload("user 15 replay should not create", 160),
        headers={**auth_headers(15), "X-Idempotency-Key": key},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["task_id"] == first_id

    second_user = client.post(
        "/v1/create",
        json=_future_payload("user 16 same key", 200),
        headers={**auth_headers(16), "X-Idempotency-Key": key},
    )
    assert second_user.status_code == 200, second_user.text
    second_id = second_user.json()["task_id"]

    assert second_id != first_id
    assert _task_user_id(first_id) == 15
    assert _task_user_id(second_id) == 16
