"""
Tests for LYR-036: GET /v1/tasks/last for follow-up correction context.
"""
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import Task, TaskState, TaskSource
from app.utils.time_utils import now_utc
from datetime import timedelta
from tests.conftest import TestingSession

client = TestClient(app, raise_server_exceptions=False)


def test_last_task_404_when_no_recent_operation():
    with patch("app.api.v1.endpoints.query.RedisClient") as mock_redis_cls:
        mock_redis_cls.return_value.get_last_task.return_value = None
        r = client.get("/v1/tasks/last")
    assert r.status_code == 404


def test_last_task_returns_task_info():
    db = TestingSession()
    task = Task(
        task_id="test-last-001",
        title="Write tests",
        planned_start_utc=now_utc() + timedelta(hours=1),
        planned_end_utc=now_utc() + timedelta(hours=2),
        planned_duration_minutes=60,
        state=TaskState.PLANNED,
        source=TaskSource.MANUAL,
    )
    db.add(task)
    db.commit()
    db.close()

    redis_data = {"task_id": "test-last-001", "title": "Write tests", "state": "PLANNED"}
    with patch("app.api.v1.endpoints.query.RedisClient") as mock_redis_cls:
        mock_redis_cls.return_value.get_last_task.return_value = redis_data
        r = client.get("/v1/tasks/last")

    assert r.status_code == 200
    data = r.json()
    assert data["task_id"] == "test-last-001"
    assert data["title"] == "Write tests"
    assert data["state"] == "PLANNED"
