"""Wave 2B stopwatch/re-entry idempotency regressions."""
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.db.models import PauseEvent, StopwatchSession, Task, TaskSource, TaskState, User
from app.db.scoping import set_current_user_id
from app.utils.time_utils import now_utc
from tests.conftest import TestingSession, auth_headers


USER_ID = 242


def _redis_available() -> bool:
    try:
        from app.utils.redis_client import RedisClient

        RedisClient().client.ping()
        return True
    except Exception:
        return False


needs_redis = pytest.mark.skipif(
    not _redis_available(), reason="redis not reachable"
)


@pytest.fixture(autouse=True)
def wave2_idempotency_env():
    set_current_user_id(None)
    try:
        from app.utils.redis_client import RedisClient

        rc = RedisClient()
        rc.clear_stopwatch_state(str(USER_ID))
        for key in rc.client.keys(f"idempotency:user:{USER_ID}:*"):
            rc.client.delete(key)
        for key in rc.client.keys(f"undo:{USER_ID}:*"):
            rc.client.delete(key)
    except Exception:
        pass

    wipe = TestingSession()
    try:
        wipe.execute(text("DELETE FROM pause_event"))
        wipe.execute(text("DELETE FROM stopwatch_session"))
        wipe.execute(text("DELETE FROM deadline_completion_event"))
        wipe.execute(text("DELETE FROM task"))
        wipe.execute(text("DELETE FROM user"))
        wipe.commit()
        wipe.add(
            User(
                user_id=USER_ID,
                email="wave2-idempotency@example.test",
                is_operator=False,
                notion_enabled=False,
                created_at=now_utc(),
            )
        )
        wipe.commit()
    finally:
        wipe.close()

    yield
    set_current_user_id(None)


def _headers(extra: dict | None = None) -> dict:
    headers = auth_headers(USER_ID)
    if extra:
        headers.update(extra)
    return headers


def _create_task(client, title: str = "Wave 2B timer") -> str:
    start = now_utc() + timedelta(minutes=10)
    end = start + timedelta(minutes=45)
    response = client.post(
        "/v1/create",
        json={
            "title": title,
            "start": start.replace(microsecond=0).isoformat() + "Z",
            "end": end.replace(microsecond=0).isoformat() + "Z",
        },
        headers=_headers(),
    )
    assert response.status_code == 200, response.text
    return response.json()["task_id"]


def _session_count(task_id: str) -> int:
    db = TestingSession()
    try:
        return (
            db.query(StopwatchSession)
            .filter(StopwatchSession.task_id == task_id)
            .count()
        )
    finally:
        db.close()


@needs_redis
def test_duplicate_start_same_task_returns_existing_session(client):
    task_id = _create_task(client)

    first = client.post(
        "/v1/stopwatch/start",
        json={"task_id": task_id, "pre_task_readiness": 3},
        headers=_headers({"X-Idempotency-Key": "start-once"}),
    )
    assert first.status_code == 200, first.text

    second = client.post(
        "/v1/stopwatch/start",
        json={"task_id": task_id, "pre_task_readiness": 3},
        headers=_headers({"X-Idempotency-Key": "different-tab"}),
    )
    assert second.status_code == 200, second.text
    assert second.json()["session_id"] == first.json()["session_id"]
    assert _session_count(task_id) == 1


@needs_redis
def test_duplicate_pause_and_resume_are_noops_not_extra_events(client):
    task_id = _create_task(client)
    started = client.post(
        "/v1/stopwatch/start",
        json={"task_id": task_id, "pre_task_readiness": 3},
        headers=_headers(),
    )
    assert started.status_code == 200, started.text

    first_pause = client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "intentional_break", "pause_initiator": "self"},
        headers=_headers(),
    )
    assert first_pause.status_code == 200, first_pause.text

    second_pause = client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "intentional_break", "pause_initiator": "self"},
        headers=_headers(),
    )
    assert second_pause.status_code == 200, second_pause.text

    db = TestingSession()
    try:
        session_id = started.json()["session_id"]
        assert (
            db.query(PauseEvent)
            .filter(PauseEvent.session_id == session_id)
            .count()
        ) == 1
    finally:
        db.close()

    first_resume = client.post("/v1/stopwatch/resume", headers=_headers())
    assert first_resume.status_code == 200, first_resume.text
    second_resume = client.post("/v1/stopwatch/resume", headers=_headers())
    assert second_resume.status_code == 200, second_resume.text
    assert second_resume.json()["paused_minutes"] == 0

    db = TestingSession()
    try:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        assert task.pause_count == 1
    finally:
        db.close()


@needs_redis
def test_stop_retry_with_same_key_replays_without_second_transition(client):
    task_id = _create_task(client)
    started = client.post(
        "/v1/stopwatch/start",
        json={"task_id": task_id, "pre_task_readiness": 3},
        headers=_headers(),
    )
    assert started.status_code == 200, started.text

    headers = _headers({"X-Idempotency-Key": "stop-finished"})
    first = client.post(
        "/v1/stopwatch/stop",
        params={"confirmed": "true"},
        json={"post_task_reflection": 4, "task_completion_percentage": 90},
        headers=headers,
    )
    assert first.status_code == 200, first.text

    second = client.post(
        "/v1/stopwatch/stop",
        params={"confirmed": "true"},
        json={"post_task_reflection": 4, "task_completion_percentage": 90},
        headers=headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["session_id"] == first.json()["session_id"]

    db = TestingSession()
    try:
        sessions = (
            db.query(StopwatchSession)
            .filter(StopwatchSession.task_id == task_id)
            .all()
        )
        assert len(sessions) == 1
        assert sessions[0].end_time_utc is not None
        task = db.query(Task).filter(Task.task_id == task_id).first()
        assert task.state == TaskState.EXECUTED
    finally:
        db.close()


def _seed_overdue(task_id: str, *, executed: bool = False, initiation_status: str = "not_started"):
    start = now_utc() - timedelta(hours=2)
    end = start + timedelta(minutes=45)
    db = TestingSession()
    try:
        task = Task(
            task_id=task_id,
            title=f"Task {task_id}",
            planned_start_utc=start,
            planned_end_utc=end,
            planned_duration_minutes=45,
            state=TaskState.EXECUTED if executed else TaskState.PLANNED,
            source=TaskSource.MANUAL,
            initiation_status=initiation_status,
            user_id=USER_ID,
        )
        if executed:
            task.executed_start_utc = start
            task.executed_end_utc = end
            task.executed_duration_minutes = 45
        db.add(task)
        db.commit()
    finally:
        db.close()


@needs_redis
def test_mark_done_is_idempotent_only_for_retroactive_done_shape(client):
    _seed_overdue("wave2-mark-done")

    first = client.post("/v1/tasks/wave2-mark-done/mark-done", headers=_headers())
    assert first.status_code == 200, first.text
    assert first.json()["previous_state"] == "PLANNED"

    second = client.post("/v1/tasks/wave2-mark-done/mark-done", headers=_headers())
    assert second.status_code == 200, second.text
    assert second.json()["previous_state"] == "EXECUTED"
    assert second.json()["initiation_status"] == "retroactive"

    _seed_overdue(
        "wave2-measured-executed",
        executed=True,
        initiation_status="initiated",
    )
    measured = client.post(
        "/v1/tasks/wave2-measured-executed/mark-done",
        headers=_headers(),
    )
    assert measured.status_code == 400
    assert "Only PLANNED or SKIPPED overdue tasks" in measured.json()["detail"]
