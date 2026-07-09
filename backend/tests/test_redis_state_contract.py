"""Redis state mutation contracts.

These tests do not require a live Redis server. They assert that multi-key
stopwatch state changes use a Redis transaction so frontend polling cannot
observe split active/pause state during resume, switch, or recovery paths.
"""
from __future__ import annotations

import fnmatch
import json

from app.utils.redis_client import RedisClient, STOPWATCH_TTL_SECONDS


class FakePipeline:
    def __init__(self) -> None:
        self.ops: list[tuple] = []
        self.executed = False

    def set(self, key, value, ex=None):
        self.ops.append(("set", key, json.loads(value), ex))
        return self

    def delete(self, key):
        self.ops.append(("delete", key))
        return self

    def execute(self):
        self.executed = True
        return []


class FakeRedis:
    def __init__(self) -> None:
        self.pipelines: list[tuple[bool, FakePipeline]] = []
        self.keys: set[str] = set()
        self.deleted: list[str] = []

    def pipeline(self, transaction=True):
        pipe = FakePipeline()
        self.pipelines.append((transaction, pipe))
        return pipe

    def scan_iter(self, match=None, count=None):
        del count
        for key in sorted(self.keys):
            if match is None or fnmatch.fnmatch(key, match):
                yield key

    def delete(self, *keys):
        for key in keys:
            self.deleted.append(str(key))
            self.keys.discard(str(key))
        return len(keys)


def _client(fake: FakeRedis) -> RedisClient:
    client = RedisClient.__new__(RedisClient)
    client.client = fake
    return client


def test_activate_stopwatch_sets_active_and_clears_pause_atomically():
    fake = FakeRedis()
    redis = _client(fake)

    redis.activate_stopwatch(
        user_id="7",
        session_id="session-1",
        task_id="task-1",
        title="Deep work",
        start_time="2026-05-18T12:00:00",
    )

    assert len(fake.pipelines) == 1
    transaction, pipe = fake.pipelines[0]
    assert transaction is True
    assert pipe.executed is True
    assert pipe.ops == [
        (
            "set",
            "stopwatch:active:7",
            {
                "session_id": "session-1",
                "task_id": "task-1",
                "title": "Deep work",
                "start_time": "2026-05-18T12:00:00",
            },
            STOPWATCH_TTL_SECONDS,
        ),
        ("delete", "stopwatch:paused:7"),
    ]


def test_activate_paused_stopwatch_sets_active_and_pause_atomically():
    fake = FakeRedis()
    redis = _client(fake)

    redis.activate_paused_stopwatch(
        user_id="7",
        session_id="session-1",
        task_id="task-1",
        title="Deep work",
        start_time="2026-05-18T12:00:00",
        paused_at="2026-05-18T12:30:00",
    )

    assert len(fake.pipelines) == 1
    transaction, pipe = fake.pipelines[0]
    assert transaction is True
    assert pipe.executed is True
    assert pipe.ops == [
        (
            "set",
            "stopwatch:active:7",
            {
                "session_id": "session-1",
                "task_id": "task-1",
                "title": "Deep work",
                "start_time": "2026-05-18T12:00:00",
            },
            STOPWATCH_TTL_SECONDS,
        ),
        (
            "set",
            "stopwatch:paused:7",
            {"session_id": "session-1", "paused_at": "2026-05-18T12:30:00"},
            STOPWATCH_TTL_SECONDS,
        ),
    ]


def test_clear_stopwatch_state_clears_active_and_pause_atomically():
    fake = FakeRedis()
    redis = _client(fake)

    redis.clear_stopwatch_state("7")

    assert len(fake.pipelines) == 1
    transaction, pipe = fake.pipelines[0]
    assert transaction is True
    assert pipe.executed is True
    assert pipe.ops == [
        ("delete", "stopwatch:active:7"),
        ("delete", "stopwatch:paused:7"),
    ]


def test_purge_user_runtime_state_deletes_known_user_scoped_keys():
    fake = FakeRedis()
    fake.keys.update(
        {
            "stopwatch:active:7",
            "stopwatch:paused:7",
            "notifications:pending:7",
            "notion:sync_queue:7",
            "last_operated_task:7",
            "gcal:access_token:7",
            "undo:7:task-1",
            "idempotency:user:7:stopwatch:start:key",
            "tasks_range:7:2026-06-01:2026-06-15:v1",
            "me:7:v1",
            "gcal:events:7:2026-06-01:2026-06-15",
            "reminder_sent:7:task-1",
            "overflow_sent:7:session-1",
            "insight_shown:7:insight-1",
            "stopwatch:active:8",
            "notifications:pending:8",
            "undo:8:task-2",
        }
    )
    redis = _client(fake)

    deleted = redis.purge_user_runtime_state("7")

    assert deleted == 14
    assert fake.keys == {
        "stopwatch:active:8",
        "notifications:pending:8",
        "undo:8:task-2",
    }
