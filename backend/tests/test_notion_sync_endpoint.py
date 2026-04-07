"""
Tests for POST /v1/tasks/{task_id}/sync — manual Notion backfill (LYR-015).
"""
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.db.models import Task, TaskState, TaskSource
from app.utils.time_utils import now_utc
from datetime import timedelta
from tests.conftest import TestingSession

client = TestClient(app, raise_server_exceptions=False)


def _seed(task_id):
    db = TestingSession()
    t = Task(
        task_id=task_id,
        title="Backfill me",
        planned_start_utc=now_utc() + timedelta(hours=1),
        planned_end_utc=now_utc() + timedelta(hours=2),
        planned_duration_minutes=60,
        state=TaskState.PLANNED,
        source=TaskSource.MANUAL,
    )
    db.add(t)
    db.commit()
    db.close()


def test_sync_404_for_missing_task():
    r = client.post("/v1/tasks/nonexistent-id/sync")
    assert r.status_code == 404


def test_sync_returns_synced_true():
    _seed("sync-test-001")
    with patch("app.api.v1.endpoints.tasks.NotionClient") as mock_cls:
        mock_cls.return_value.sync_task.return_value = "notion-page-abc"
        r = client.post("/v1/tasks/sync-test-001/sync")
    assert r.status_code == 200
    body = r.json()
    assert body["synced"] is True
    assert body["task_id"] == "sync-test-001"
    assert body["notion_page_id"] == "notion-page-abc"


def test_sync_502_when_notion_fails():
    _seed("sync-test-002")
    with patch("app.api.v1.endpoints.tasks.NotionClient") as mock_cls:
        mock_cls.return_value.sync_task.side_effect = Exception("Notion down")
        r = client.post("/v1/tasks/sync-test-002/sync")
    assert r.status_code == 502
