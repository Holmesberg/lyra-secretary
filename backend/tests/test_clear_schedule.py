"""
Tests for POST /v1/schedule/clear.
- Blocks with 400 if stopwatch active
- Deletes PLANNED tasks only when no active timer
- Never touches EXECUTING / PAUSED
"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.db.models import Task, TaskSource, TaskState
from app.main import app
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


def test_clear_blocked_when_timer_active():
    """400 returned if stopwatch is active."""
    with patch("app.api.v1.endpoints.tasks.StopwatchManager") as mock_sw:
        mock_sw.return_value.get_status.return_value = {
            "active": True,
            "task_title": "Deep work",
        }
        r = client.post("/v1/schedule/clear")

    assert r.status_code == 400
    body = r.json()
    assert body["detail"]["error"] == "active_timer"
    assert "Deep work" in body["detail"]["message"]


def test_clear_deletes_planned_tasks():
    """PLANNED tasks are removed when no active timer."""
    _seed(TaskState.PLANNED, "clear-p1")
    _seed(TaskState.PLANNED, "clear-p2")

    with patch("app.api.v1.endpoints.tasks.StopwatchManager") as mock_sw:
        mock_sw.return_value.get_status.return_value = {"active": False}
        r = client.post("/v1/schedule/clear")

    assert r.status_code == 200
    body = r.json()
    assert body["cleared"] is True
    assert body["planned_deleted"] >= 2


def test_clear_does_not_touch_executing():
    """EXECUTING tasks are left untouched."""
    _seed(TaskState.EXECUTING, "clear-e1")

    with patch("app.api.v1.endpoints.tasks.StopwatchManager") as mock_sw:
        mock_sw.return_value.get_status.return_value = {"active": False}
        r = client.post("/v1/schedule/clear")

    assert r.status_code == 200
    # EXECUTING task still in DB
    db = TestingSession()
    t = db.query(Task).filter(Task.task_id == "clear-e1").first()
    db.close()
    assert t is not None
    assert t.state == TaskState.EXECUTING
