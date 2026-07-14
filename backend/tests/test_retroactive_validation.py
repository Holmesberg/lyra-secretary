"""
Tests for retroactive endpoint missing_fields validation.
The validation block runs before any DB call, so only the shared test DB
from conftest.py is needed.
"""
from fastapi.testclient import TestClient
from uuid import uuid4
from app.main import app
from app.db.models import Task, User
from tests.conftest import auth_headers

client = TestClient(app, raise_server_exceptions=False)

BASE = {"title": "Deep work", "start_time": "2026-04-07T14:00:00", "end_time": "2026-04-07T16:00:00"}


def test_missing_all_three_returns_400():
    r = client.post("/v1/stopwatch/retroactive", json=BASE)
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["error"] == "missing_required_fields"
    fields = [f["field"] for f in detail["missing_fields"]]
    assert set(fields) == {"post_task_reflection", "total_paused_minutes", "unplanned_reason"}


def test_missing_reflection_and_paused_minutes():
    r = client.post("/v1/stopwatch/retroactive", json={**BASE, "unplanned_reason": "forgot"})
    assert r.status_code == 400
    fields = [f["field"] for f in r.json()["detail"]["missing_fields"]]
    assert "post_task_reflection" in fields
    assert "total_paused_minutes" in fields
    assert "unplanned_reason" not in fields


def test_planned_task_still_requires_unplanned_reason():
    """planned_duration_minutes does NOT bypass unplanned_reason — always required."""
    r = client.post("/v1/stopwatch/retroactive", json={
        **BASE,
        "post_task_reflection": 4,
        "total_paused_minutes": 0,
        "planned_duration_minutes": 120,
    })
    assert r.status_code == 400
    fields = [f["field"] for f in r.json()["detail"]["missing_fields"]]
    assert "unplanned_reason" in fields


def test_missing_only_unplanned_reason():
    r = client.post("/v1/stopwatch/retroactive", json={
        **BASE,
        "post_task_reflection": 3,
        "total_paused_minutes": 10,
    })
    assert r.status_code == 400
    fields = [f["field"] for f in r.json()["detail"]["missing_fields"]]
    assert fields == ["unplanned_reason"]


def test_missing_fields_include_prompts():
    r = client.post("/v1/stopwatch/retroactive", json=BASE)
    missing = r.json()["detail"]["missing_fields"]
    for entry in missing:
        assert "prompt" in entry
        assert len(entry["prompt"]) > 0


def test_unplanned_reason_options_present():
    r = client.post("/v1/stopwatch/retroactive", json={
        **BASE,
        "post_task_reflection": 3,
        "total_paused_minutes": 0,
    })
    missing = r.json()["detail"]["missing_fields"]
    unplanned = next(f for f in missing if f["field"] == "unplanned_reason")
    assert "options" in unplanned
    assert unplanned["options"]["1"] == "unexpected_task"


def test_retroactive_planned_duration_does_not_override_explicit_end_time(client, db):
    user = User(
        email=f"retroactive-explicit-end-{uuid4().hex[:8]}@example.test",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    r = client.post(
        "/v1/stopwatch/retroactive",
        json={
            "title": "Debugging",
            "start_time": "2026-04-07T14:37:00",
            "end_time": "2026-04-07T16:00:00",
            "post_task_reflection": 4,
            "total_paused_minutes": 0,
            "unplanned_reason": "forgot_to_log",
            "planned_duration_minutes": 54,
        },
        headers=auth_headers(user.user_id),
    )

    assert r.status_code == 200
    body = r.json()
    assert body["duration_minutes"] == 83
    assert body["planned_duration_minutes"] == 54
    assert body["delta_minutes"] == -29
    assert body["end_time"].startswith("2026-04-07T16:00:00")

    task = db.query(Task).filter(Task.task_id == body["task_id"]).one()
    assert task.executed_duration_minutes == 83
    assert task.executed_end_utc is not None
    assert task.planned_duration_minutes == 54
    assert task.planned_end_utc != task.executed_end_utc
