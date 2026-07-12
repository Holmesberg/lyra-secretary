from datetime import datetime, timedelta
from uuid import uuid4

from app.api.v1.endpoints import query as query_endpoint
from app.db.models import Task, TaskState, User
from app.utils import tasks_range_cache


class _GenerationRedis:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, _ttl, value):
        self.values[key] = value

    def delete(self, key):
        return int(self.values.pop(key, None) is not None)

    def incr(self, key):
        value = int(self.values.get(key) or 0) + 1
        self.values[key] = str(value)
        return value


def _install_fake(monkeypatch):
    fake = _GenerationRedis()
    monkeypatch.setattr(
        tasks_range_cache,
        "RedisClient",
        lambda: type("Client", (), {"client": fake})(),
    )
    return fake


def test_stale_query_cannot_republish_after_task_mutation(monkeypatch):
    _install_fake(monkeypatch)
    user_id = 91
    date_from = "2026-07-01"
    date_to = "2026-07-14"

    cached, stale_epoch = tasks_range_cache.get_cached_range_with_epoch(
        user_id,
        date_from,
        date_to,
    )
    assert cached is None
    assert stale_epoch == 0

    tasks_range_cache.invalidate_user_ranges(user_id)
    assert tasks_range_cache.set_cached_range_if_epoch(
        user_id,
        date_from,
        date_to,
        {"tasks": [], "total": 0, "truncated": False},
        stale_epoch,
    )

    current, current_epoch = tasks_range_cache.get_cached_range_with_epoch(
        user_id,
        date_from,
        date_to,
    )
    assert current is None
    assert current_epoch == 1

    fresh = {
        "tasks": [{"task_id": 123, "name": "Visible after create"}],
        "total": 1,
        "truncated": False,
    }
    assert tasks_range_cache.set_cached_range_if_epoch(
        user_id,
        date_from,
        date_to,
        fresh,
        current_epoch,
    )
    assert tasks_range_cache.get_cached_range(user_id, date_from, date_to) == fresh


def test_range_generations_are_user_scoped(monkeypatch):
    _install_fake(monkeypatch)
    date_from = "2026-07-01"
    date_to = "2026-07-14"

    tasks_range_cache.set_cached_range(
        1,
        date_from,
        date_to,
        {"tasks": [{"task_id": 1}]},
    )
    tasks_range_cache.set_cached_range(
        2,
        date_from,
        date_to,
        {"tasks": [{"task_id": 2}]},
    )
    tasks_range_cache.invalidate_user_ranges(1)

    assert tasks_range_cache.get_cached_range(1, date_from, date_to) is None
    assert tasks_range_cache.get_cached_range(2, date_from, date_to) == {
        "tasks": [{"task_id": 2}]
    }


def test_range_endpoint_publishes_only_to_captured_generation(
    db,
    client,
    monkeypatch,
):
    user_id = 9191
    now = datetime.utcnow()
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        db.add(
            User(
                user_id=user_id,
                email="range-generation@example.test",
                is_operator=False,
                created_at=now,
            )
        )
    task = Task(
        task_id=str(uuid4()),
        user_id=user_id,
        title="Generation-wired range task",
        category="study",
        planned_start_utc=now + timedelta(hours=1),
        planned_end_utc=now + timedelta(hours=2),
        planned_duration_minutes=60,
        state=TaskState.PLANNED,
        source="manual",
        created_at=now,
        last_modified_at=now,
    )
    db.add(task)
    db.commit()

    published = []
    monkeypatch.setattr(
        query_endpoint,
        "get_cached_range_with_epoch",
        lambda *_args: (None, 7),
    )
    monkeypatch.setattr(
        query_endpoint,
        "set_cached_range_if_epoch",
        lambda *args: published.append(args) or True,
    )

    date_from = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    date_to = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    response = client.get(
        f"/v1/tasks/query?date_from={date_from}&date_to={date_to}&state=all",
        headers={"X-User-Id": str(user_id)},
    )

    assert response.status_code == 200
    assert task.task_id in {row["task_id"] for row in response.json()["tasks"]}
    assert len(published) == 1
    assert published[0][-1] == 7
