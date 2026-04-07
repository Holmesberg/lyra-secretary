"""
Tests for retroactive endpoint missing_fields validation.
The validation block runs before any DB call, so only the shared test DB
from conftest.py is needed.
"""
from fastapi.testclient import TestClient
from app.main import app

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


def test_planned_task_skips_unplanned_reason():
    """planned_duration_minutes present → unplanned_reason not required.
    Validation passes; any downstream error (service/DB) is outside this test's scope."""
    r = client.post("/v1/stopwatch/retroactive", json={
        **BASE,
        "post_task_reflection": 4,
        "total_paused_minutes": 0,
        "planned_duration_minutes": 120,
    })
    # Validation must not reject with missing_required_fields
    if r.status_code == 400:
        assert r.json().get("detail", {}).get("error") != "missing_required_fields"


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
    assert unplanned["options"]["1"] == "unexpected"
