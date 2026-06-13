import logging
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import text

from app.db.models import PauseEvent, StopwatchSession, Task, TaskState, User
from app.services.cortex import planning_calibration_query
from app.services.stopwatch_manager import (
    STALE_PAUSE_RESOLUTION_FLAG,
    STALE_PAUSE_TASK_STATUS,
)
from app.utils.time_utils import now_utc
from app.workers.jobs import stale_session_recovery
from tests.conftest import auth_headers


class _FakeRedis:
    def get_active_stopwatch(self, _user_id):
        return None

    def get_pause_state(self, _user_id):
        return None

    def clear_stopwatch_state(self, _user_id):
        return None

    def clear_pause_state(self, _user_id):
        return None


class _FakeActiveRedis(_FakeRedis):
    def __init__(self, session_id, task_id):
        self.session_id = session_id
        self.task_id = task_id

    def get_active_stopwatch(self, _user_id):
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "title": "Long parked work",
        }


def _clean(db):
    db.rollback()
    db.execute(text("DELETE FROM pause_event"))
    db.execute(text("DELETE FROM stopwatch_session"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM user"))
    db.commit()


def _seed_paused(db, *, user_id=9911, paused_hours=73):
    now = now_utc()
    user = User(
        user_id=user_id,
        email=f"stale-{user_id}@example.test",
        is_operator=True,
        created_at=now - timedelta(days=10),
    )
    task = Task(
        task_id=str(uuid4()),
        user_id=user_id,
        title="Long parked work",
        category="study",
        planned_start_utc=now - timedelta(hours=paused_hours + 3),
        planned_end_utc=now - timedelta(hours=paused_hours + 2),
        planned_duration_minutes=60,
        state=TaskState.PAUSED,
        source="manual",
        created_at=now - timedelta(hours=paused_hours + 3),
        last_modified_at=now - timedelta(hours=paused_hours),
    )
    paused_at = now - timedelta(hours=paused_hours)
    session = StopwatchSession(
        session_id=str(uuid4()),
        user_id=user_id,
        task_id=task.task_id,
        start_time_utc=paused_at - timedelta(minutes=130),
        end_time_utc=None,
        paused_at_utc=paused_at,
        total_paused_minutes=10,
        auto_closed=False,
    )
    evt = PauseEvent(
        pause_event_id=str(uuid4()),
        session_id=session.session_id,
        user_id=user_id,
        paused_at_utc=paused_at,
        pause_reason="intentional_break",
        pause_initiator="self",
        active_elapsed_at_pause_seconds=120 * 60,
    )
    db.add_all([user, task, session, evt])
    db.commit()
    return task, session


def test_stale_pause_resolution_marks_executed_and_dirty_for_calibration(
    db, client, monkeypatch
):
    _clean(db)
    task, session = _seed_paused(db)
    paused_at = session.paused_at_utc

    monkeypatch.setattr(
        "app.services.stopwatch_manager.RedisClient",
        lambda: _FakeRedis(),
    )

    res = client.post(
        f"/v1/stopwatch/stale-pauses/{session.session_id}/resolve",
        headers=auth_headers(task.user_id),
        json={
            "post_task_reflection": 2,
            "task_completion_percentage": 90,
            "scope_outcome": "expanded",
        },
    )

    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["resolved"] is True
    assert payload["new_state"] == "EXECUTED"
    assert payload["active_minutes"] == 120
    assert payload["data_quality_flag"] == STALE_PAUSE_RESOLUTION_FLAG

    db.expire_all()
    refreshed_task = db.query(Task).filter(Task.task_id == task.task_id).one()
    refreshed_session = (
        db.query(StopwatchSession)
        .filter(StopwatchSession.session_id == session.session_id)
        .one()
    )
    assert refreshed_task.state == TaskState.EXECUTED
    assert refreshed_task.executed_duration_minutes == 120
    assert refreshed_task.post_task_reflection == 2
    assert refreshed_task.scope_outcome == "expanded"
    assert refreshed_task.initiation_status == STALE_PAUSE_TASK_STATUS
    assert refreshed_session.end_time_utc == paused_at
    assert refreshed_session.paused_at_utc is None
    assert refreshed_session.task_completion_percentage == 90
    assert refreshed_session.data_quality_flag == STALE_PAUSE_RESOLUTION_FLAG
    assert planning_calibration_query(db, user_id=task.user_id).count() == 0


def test_fresh_pause_cannot_use_stale_resolution(db, client, monkeypatch):
    _clean(db)
    task, session = _seed_paused(db, user_id=9912, paused_hours=2)
    monkeypatch.setattr(
        "app.services.stopwatch_manager.RedisClient",
        lambda: _FakeRedis(),
    )

    res = client.post(
        f"/v1/stopwatch/stale-pauses/{session.session_id}/resolve",
        headers=auth_headers(task.user_id),
        json={
            "post_task_reflection": 2,
            "task_completion_percentage": 90,
            "scope_outcome": "expanded",
        },
    )

    assert res.status_code == 400
    assert "at least 72h" in res.text


def test_just_under_72h_pause_cannot_use_stale_resolution(db, client, monkeypatch):
    _clean(db)
    task, session = _seed_paused(db, user_id=9914, paused_hours=71 + (59 / 60))
    monkeypatch.setattr(
        "app.services.stopwatch_manager.RedisClient",
        lambda: _FakeRedis(),
    )

    res = client.post(
        f"/v1/stopwatch/stale-pauses/{session.session_id}/resolve",
        headers=auth_headers(task.user_id),
        json={
            "post_task_reflection": 2,
            "task_completion_percentage": 90,
            "scope_outcome": "expanded",
        },
    )

    assert res.status_code == 400
    assert "at least 72h" in res.text


def test_exact_72h_pause_can_resolve_at_80_percent_boundary(
    db, client, monkeypatch
):
    _clean(db)
    task, session = _seed_paused(db, user_id=9915, paused_hours=72)
    monkeypatch.setattr(
        "app.services.stopwatch_manager.RedisClient",
        lambda: _FakeRedis(),
    )

    res = client.post(
        f"/v1/stopwatch/stale-pauses/{session.session_id}/resolve",
        headers=auth_headers(task.user_id),
        json={
            "post_task_reflection": 2,
            "task_completion_percentage": 80,
            "scope_outcome": "expanded",
        },
    )

    assert res.status_code == 200, res.text
    db.expire_all()
    refreshed_task = db.query(Task).filter(Task.task_id == task.task_id).one()
    assert refreshed_task.state == TaskState.EXECUTED


def test_stale_pause_resolution_below_completion_marks_skipped(db, client, monkeypatch):
    _clean(db)
    task, session = _seed_paused(db, user_id=9913)
    monkeypatch.setattr(
        "app.services.stopwatch_manager.RedisClient",
        lambda: _FakeRedis(),
    )

    res = client.post(
        f"/v1/stopwatch/stale-pauses/{session.session_id}/resolve",
        headers=auth_headers(task.user_id),
        json={
            "post_task_reflection": 2,
            "task_completion_percentage": 79,
            "scope_outcome": "reduced",
        },
    )

    assert res.status_code == 200, res.text
    db.expire_all()
    refreshed_task = db.query(Task).filter(Task.task_id == task.task_id).one()
    assert refreshed_task.state == TaskState.SKIPPED
    assert refreshed_task.executed_duration_minutes == 120
    assert refreshed_task.scope_outcome == "reduced"


def test_stale_pause_resolution_is_not_double_resolved(db, client, monkeypatch):
    _clean(db)
    task, session = _seed_paused(db, user_id=9916)
    monkeypatch.setattr(
        "app.services.stopwatch_manager.RedisClient",
        lambda: _FakeRedis(),
    )
    payload = {
        "post_task_reflection": 2,
        "task_completion_percentage": 90,
        "scope_outcome": "expanded",
    }

    first = client.post(
        f"/v1/stopwatch/stale-pauses/{session.session_id}/resolve",
        headers=auth_headers(task.user_id),
        json=payload,
    )
    second = client.post(
        f"/v1/stopwatch/stale-pauses/{session.session_id}/resolve",
        headers=auth_headers(task.user_id),
        json=payload,
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 400
    assert "already closed" in second.text


def test_redis_active_73h_paused_session_is_left_for_user_resolution(
    db, monkeypatch, caplog
):
    _clean(db)
    task, session = _seed_paused(db, user_id=9917, paused_hours=73)
    fake = _FakeActiveRedis(session.session_id, task.task_id)
    monkeypatch.setattr(
        "app.workers.jobs.stale_session_recovery.RedisClient",
        lambda: fake,
    )
    caplog.set_level(logging.INFO, logger="app.workers.jobs.stale_session_recovery")

    stale_session_recovery._run_for_one_user(
        db, db.query(User).filter(User.user_id == task.user_id).one()
    )

    db.expire_all()
    refreshed_task = db.query(Task).filter(Task.task_id == task.task_id).one()
    refreshed_session = (
        db.query(StopwatchSession)
        .filter(StopwatchSession.session_id == session.session_id)
        .one()
    )
    assert refreshed_task.state == TaskState.PAUSED
    assert refreshed_session.end_time_utc is None
    assert refreshed_session.auto_closed is False
    assert "leaving open for user reflection resolution" in caplog.text
