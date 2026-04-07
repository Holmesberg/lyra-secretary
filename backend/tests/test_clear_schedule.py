"""
Tests for LYR-042: POST /v1/schedule/clear must handle EXECUTING tasks.
"""
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.db.models import Task, TaskState, TaskSource
from app.utils.time_utils import now_utc
from datetime import timedelta
from tests.conftest import TestingSession

client = TestClient(app, raise_server_exceptions=False)


def _seed(state: TaskState, task_id: str):
    db = TestingSession()
    t = Task(
        task_id=task_id,
        title=f"Task {task_id}",
        planned_start_utc=now_utc() + timedelta(hours=1),
        planned_end_utc=now_utc() + timedelta(hours=2),
        planned_duration_minutes=60,
        state=state,
        source=TaskSource.MANUAL,
    )
    db.add(t)
    db.commit()
    db.close()


def test_clear_deletes_planned_tasks():
    _seed(TaskState.PLANNED, "clear-p1")
    _seed(TaskState.PLANNED, "clear-p2")

    with patch("app.api.v1.endpoints.tasks.StopwatchManager") as mock_sw:
        mock_sw.return_value.stop.side_effect = Exception("no active")
        r = client.post("/v1/schedule/clear")

    assert r.status_code == 200
    body = r.json()
    assert body["cleared"] is True
    assert body["planned_deleted"] >= 2


def test_clear_abandons_executing_tasks():
    _seed(TaskState.EXECUTING, "clear-e1")

    with patch("app.api.v1.endpoints.tasks.StopwatchManager") as mock_sw:
        mock_sw.return_value.stop.side_effect = Exception("no active")
        r = client.post("/v1/schedule/clear")

    assert r.status_code == 200
    body = r.json()
    assert body["cleared"] is True
    assert body["executing_abandoned"] >= 1


def test_clear_response_shape():
    r = client.post("/v1/schedule/clear")
    assert r.status_code == 200
    body = r.json()
    for field in ("cleared", "stopwatch_stopped", "planned_deleted", "executing_abandoned", "total_affected"):
        assert field in body
