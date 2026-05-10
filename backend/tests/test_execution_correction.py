from datetime import datetime, timedelta

from app.db.models import StopwatchSession, Task, TaskExecutionCorrection, TaskState
from app.services.cortex import measured_execution_query
from tests.conftest import auth_headers


USER_ID = 77


def _seed_executed(db, *, task_id: str = "exec-correction-1") -> Task:
    start = datetime(2026, 5, 10, 10, 0, 0)
    task = Task(
        task_id=task_id,
        title="Forgotten stop",
        category="work",
        planned_start_utc=start,
        planned_end_utc=start + timedelta(minutes=60),
        planned_duration_minutes=60,
        executed_start_utc=start,
        executed_end_utc=start + timedelta(minutes=180),
        executed_duration_minutes=180,
        state=TaskState.EXECUTED,
        initiation_status="initiated",
        user_id=USER_ID,
    )
    db.add(task)
    db.add(
        StopwatchSession(
            task_id=task.task_id,
            start_time_utc=task.executed_start_utc,
            end_time_utc=task.executed_end_utc,
            total_paused_minutes=0.0,
            user_id=USER_ID,
        )
    )
    db.commit()
    return task


def test_execution_correction_is_append_only_and_query_exposes_effective_fields(client, db):
    task = _seed_executed(db, task_id="exec-correction-append")

    r = client.post(
        f"/v1/tasks/{task.task_id}/execution-correction",
        json={"corrected_duration_minutes": 75},
        headers=auth_headers(USER_ID),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["corrected"] is True
    assert body["provenance"] == "retroactive"
    assert body["vt17_eligible"] is False
    assert body["original_executed_duration_minutes"] == 180
    assert body["corrected_executed_duration_minutes"] == 75

    db.refresh(task)
    assert task.executed_duration_minutes == 180
    assert task.executed_end_utc == datetime(2026, 5, 10, 13, 0, 0)

    row = db.query(TaskExecutionCorrection).filter_by(task_id=task.task_id).one()
    assert row.reason == "forgot_to_stop_timer"
    assert row.corrected_executed_duration_minutes == 75

    q = client.get(
        "/v1/tasks/query?date_from=2026-05-10&date_to=2026-05-10&state=all",
        headers=auth_headers(USER_ID),
    )
    assert q.status_code == 200
    tasks = q.json()["tasks"]
    corrected = next(t for t in tasks if t["task_id"] == task.task_id)
    assert corrected["executed_duration_minutes"] == 180
    assert corrected["effective_executed_duration_minutes"] == 75
    assert corrected["effective_duration_delta_minutes"] == -15
    assert corrected["execution_duration_provenance"] == "retroactive"
    assert corrected["execution_correction_id"] == body["correction_id"]


def test_execution_correction_rejects_non_executed_tasks(client, db):
    start = datetime(2026, 5, 10, 11, 0, 0)
    task = Task(
        task_id="exec-correction-planned",
        title="Still planned",
        planned_start_utc=start,
        planned_end_utc=start + timedelta(minutes=30),
        planned_duration_minutes=30,
        state=TaskState.PLANNED,
        initiation_status="not_started",
        user_id=USER_ID,
    )
    db.add(task)
    db.commit()

    r = client.post(
        f"/v1/tasks/{task.task_id}/execution-correction",
        json={"corrected_duration_minutes": 10},
        headers=auth_headers(USER_ID),
    )
    assert r.status_code == 400
    assert "Only EXECUTED tasks" in r.json()["detail"]


def test_execution_correction_rejects_retroactive_logs(client, db):
    task = _seed_executed(db, task_id="exec-correction-retroactive")
    task.initiation_status = "retroactive"
    db.commit()

    r = client.post(
        f"/v1/tasks/{task.task_id}/execution-correction",
        json={"corrected_duration_minutes": 75},
        headers=auth_headers(USER_ID),
    )
    assert r.status_code == 400
    assert "only for observed stopwatch sessions" in r.json()["detail"]


def test_execution_correction_excluded_from_measured_execution_query(client, db):
    task = _seed_executed(db, task_id="exec-correction-baseline")
    before = measured_execution_query(db, user_id=USER_ID).all()
    assert any(t.task_id == task.task_id for t in before)

    r = client.post(
        f"/v1/tasks/{task.task_id}/execution-correction",
        json={"corrected_duration_minutes": 90},
        headers=auth_headers(USER_ID),
    )
    assert r.status_code == 200

    after = measured_execution_query(db, user_id=USER_ID).all()
    assert all(t.task_id != task.task_id for t in after)
