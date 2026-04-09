"""
Tests for GET /v1/analytics/cascade — complete field coverage.
"""
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import Task, TaskState, TaskSource
from app.utils.time_utils import now_utc
from datetime import timedelta
from tests.conftest import TestingSession

client = TestClient(app, raise_server_exceptions=False)


def _seed_task(task_id, state, hour_offset=1):
    db = TestingSession()
    t = Task(
        task_id=task_id,
        title=f"Task {task_id}",
        planned_start_utc=now_utc() - timedelta(hours=hour_offset),
        planned_end_utc=now_utc() - timedelta(hours=hour_offset) + timedelta(hours=1),
        planned_duration_minutes=60,
        state=state,
        source=TaskSource.MANUAL,
        initiation_status="abandoned" if state == TaskState.SKIPPED else "not_started",
        category="fitness",
        user_id=1,
    )
    db.add(t)
    db.commit()
    db.close()


def test_cascade_response_has_required_fields():
    r = client.get("/v1/analytics/cascade?days=7")
    assert r.status_code == 200
    body = r.json()
    assert "cascade_score" in body
    assert "summary" in body
    assert "morning_anchor" in body
    assert "daily" in body

    summary = body["summary"]
    for field in ("avg_cascade_score", "skip_propagation_probability",
                  "morning_anchor_execution_rate", "most_cascade_prone_category",
                  "most_cascade_prone_time_of_day"):
        assert field in summary, f"Missing summary field: {field}"


def test_cascade_daily_has_spec_fields():
    _seed_task("cas-1", TaskState.EXECUTED, hour_offset=2)
    _seed_task("cas-2", TaskState.SKIPPED, hour_offset=1)

    r = client.get("/v1/analytics/cascade?days=7")
    assert r.status_code == 200
    daily = r.json()["daily"]
    assert len(daily) > 0

    day = daily[0]
    for field in ("total_tasks", "total_executed", "total_skipped",
                  "cascade_score", "morning_anchor_executed",
                  "first_skip_time", "consecutive_skip_sequences"):
        assert field in day, f"Missing daily field: {field}"


def test_skip_propagation_probability():
    """Two consecutive skips → skip-followed-by-any >= 1."""
    _seed_task("cas-3", TaskState.SKIPPED, hour_offset=4)
    _seed_task("cas-4", TaskState.SKIPPED, hour_offset=3)

    r = client.get("/v1/analytics/cascade?days=7")
    body = r.json()
    assert body["total_skip_followed_by_any"] >= 1
