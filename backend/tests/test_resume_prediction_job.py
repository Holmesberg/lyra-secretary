"""Scheduler-contract tests for the resume_prediction worker.

Wave 0 stabilization: the Today banner is only useful if the worker creates
one continuity notification for a genuinely paused session, stays quiet on
fresh pauses and user-local quiet hours, and respects cooldown / max-fire caps.
"""
from datetime import datetime, timedelta
from unittest.mock import DEFAULT, patch
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.models import (
    PauseEvent,
    ResumePredictionLog,
    StopwatchSession,
    Task,
    TaskState,
    User,
)
from app.db.scoping import set_current_user_id
from app.services.resume_predictor import (
    COOLDOWN_MINUTES,
    COLD_START_FLAT_CAP,
    MAX_FIRES_PER_SESSION,
    ResumePrediction,
)
from app.utils.time_utils import now_utc
from app.workers.jobs import resume_prediction
from app.workers.jobs.resume_prediction import _run_for_one_user


TEST_NOW_UTC = datetime(2026, 7, 15, 12, 0)


@pytest.fixture(autouse=True)
def _stable_worker_clock(monkeypatch):
    monkeypatch.setattr(resume_prediction, "now_utc", lambda: TEST_NOW_UTC)
    monkeypatch.setitem(globals(), "now_utc", lambda: TEST_NOW_UTC)


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM resume_prediction_log"))
    db.execute(text("DELETE FROM pause_event"))
    db.execute(text("DELETE FROM stopwatch_session"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM user"))
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM resume_prediction_log"))
    db.execute(text("DELETE FROM pause_event"))
    db.execute(text("DELETE FROM stopwatch_session"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM user"))
    db.commit()


def _make_user(db, user_id: int = 920) -> User:
    user = User(
        user_id=user_id,
        email=f"resume-job-{user_id}@test",
        is_operator=False,
        notion_enabled=False,
        created_at=now_utc(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_paused_task_with_open_pause(
    db,
    user_id: int,
    *,
    paused_for_minutes: int = COLD_START_FLAT_CAP + 1,
) -> tuple[Task, StopwatchSession, PauseEvent]:
    now = now_utc()
    task = Task(
        task_id=str(uuid4()),
        user_id=user_id,
        title=f"Paused task {user_id}",
        category="work",
        state=TaskState.PAUSED,
        planned_start_utc=now - timedelta(minutes=20),
        planned_end_utc=now + timedelta(minutes=40),
        planned_duration_minutes=60,
        source="manual",
        created_at=now - timedelta(hours=1),
        last_modified_at=now,
    )
    db.add(task)
    db.flush()
    session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=user_id,
        start_time_utc=now - timedelta(minutes=paused_for_minutes + 15),
        end_time_utc=None,
        auto_closed=False,
        total_paused_minutes=0,
    )
    db.add(session)
    db.flush()
    pause = PauseEvent(
        pause_event_id=str(uuid4()),
        session_id=session.session_id,
        user_id=user_id,
        paused_at_utc=now - timedelta(minutes=paused_for_minutes),
        resumed_at_utc=None,
        pause_reason="intentional_break",
        pause_initiator="self",
        self_reported_retroactively=False,
    )
    db.add(pause)
    db.commit()
    db.refresh(task)
    db.refresh(session)
    db.refresh(pause)
    return task, session, pause


def _prediction(user_id: int, session: StopwatchSession, task: Task) -> ResumePrediction:
    return ResumePrediction(
        user_id=user_id,
        session_id=session.session_id,
        task_id=task.task_id,
        fired_at=now_utc(),
        paused_for_minutes=35.0,
        p75_pause_minutes=None,
        mechanism="cold_start_synthetic",
        confidence=0.4,
        sample_size=0,
    )


def _patch_delivery():
    return patch.multiple(
        "app.workers.jobs.resume_prediction",
        enqueue_user_notification=DEFAULT,
        create_output_surface_decision=DEFAULT,
        emit_surface_suppression=DEFAULT,
    )


def test_resume_prediction_firing_writes_log_and_queues_notification(db):
    user = _make_user(db)
    task, session, _pause = _make_paused_task_with_open_pause(db, user.user_id)
    set_current_user_id(user.user_id)

    with patch("app.workers.jobs.resume_prediction.ResumePredictor") as mock_cls, \
         _patch_delivery() as patched:
        mock_cls.return_value.predict.return_value = _prediction(
            user.user_id, session, task
        )
        _run_for_one_user(db, user)

    rows = db.query(ResumePredictionLog).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.user_id == user.user_id
    assert row.session_id == session.session_id
    assert row.task_id == task.task_id
    assert row.mechanism == "cold_start_synthetic"
    assert patched["enqueue_user_notification"].call_count == 1
    payload = patched["enqueue_user_notification"].call_args.args[1]
    assert payload["type"] == "resume_prediction"
    assert payload["task_id"] == task.task_id
    assert payload["firing_id"] == row.firing_id
    assert payload["surface_id"] == "worker.resume_prediction"
    assert payload["exposure_id"]
    assert patched["enqueue_user_notification"].call_args.kwargs["db"] is db
    assert (
        patched["enqueue_user_notification"].call_args.kwargs["surface_id"]
        == "worker.resume_prediction"
    )
    assert patched["create_output_surface_decision"].call_count == 1
    decision_kwargs = patched["create_output_surface_decision"].call_args.kwargs
    assert decision_kwargs["decision_status"] == "queued"
    assert decision_kwargs["delivered_at"] is None


def test_quiet_hours_skip_resume_prediction_before_any_write(db):
    user = _make_user(db)
    user.timezone = "Asia/Tokyo"
    db.commit()
    _make_paused_task_with_open_pause(db, user.user_id)
    set_current_user_id(user.user_id)

    with patch(
        "app.workers.jobs.resume_prediction.now_utc",
        return_value=datetime(2026, 7, 15, 13, 0),
    ), patch(
        "app.workers.jobs.resume_prediction.ResumePredictor"
    ) as mock_cls, _patch_delivery() as patched:
        _run_for_one_user(db, user)

    assert mock_cls.return_value.predict.call_count == 0
    assert patched["enqueue_user_notification"].call_count == 0
    assert patched["create_output_surface_decision"].call_count == 0
    assert db.query(ResumePredictionLog).count() == 0


def test_invalid_timezone_fails_closed_for_resume_prediction(db):
    user = _make_user(db)
    user.timezone = "Not/A-Timezone"
    db.commit()
    _make_paused_task_with_open_pause(db, user.user_id)
    set_current_user_id(user.user_id)

    with patch(
        "app.workers.jobs.resume_prediction.ResumePredictor"
    ) as mock_cls, _patch_delivery() as patched:
        _run_for_one_user(db, user)

    assert mock_cls.return_value.predict.call_count == 0
    assert patched["enqueue_user_notification"].call_count == 0
    assert db.query(ResumePredictionLog).count() == 0


def test_fresh_pause_does_not_fire_resume_prediction(db):
    user = _make_user(db)
    _make_paused_task_with_open_pause(db, user.user_id, paused_for_minutes=5)
    set_current_user_id(user.user_id)

    with _patch_delivery() as patched:
        _run_for_one_user(db, user)

    assert db.query(ResumePredictionLog).count() == 0
    assert patched["enqueue_user_notification"].call_count == 0


def test_resume_prediction_cooldown_blocks_refire(db):
    user = _make_user(db)
    task, session, _pause = _make_paused_task_with_open_pause(db, user.user_id)
    db.add(
        ResumePredictionLog(
            user_id=user.user_id,
            session_id=session.session_id,
            task_id=task.task_id,
            fired_at=now_utc() - timedelta(minutes=COOLDOWN_MINUTES - 1),
            paused_for_minutes=35,
            p75_pause_minutes=None,
            mechanism="cold_start_synthetic",
            confidence=0.4,
            sample_size=0,
        )
    )
    db.commit()
    set_current_user_id(user.user_id)

    with patch("app.workers.jobs.resume_prediction.ResumePredictor") as mock_cls, \
         _patch_delivery() as patched:
        mock_cls.return_value.predict.return_value = _prediction(
            user.user_id, session, task
        )
        _run_for_one_user(db, user)

    assert db.query(ResumePredictionLog).count() == 1
    assert mock_cls.return_value.predict.call_count == 0
    assert patched["enqueue_user_notification"].call_count == 0


def test_resume_prediction_max_fire_cap_blocks_nagging(db):
    assert MAX_FIRES_PER_SESSION == 2
    user = _make_user(db)
    task, session, _pause = _make_paused_task_with_open_pause(db, user.user_id)
    for i in range(MAX_FIRES_PER_SESSION):
        db.add(
            ResumePredictionLog(
                user_id=user.user_id,
                session_id=session.session_id,
                task_id=task.task_id,
                fired_at=now_utc()
                - timedelta(minutes=COOLDOWN_MINUTES * (i + 2)),
                paused_for_minutes=35 + i,
                p75_pause_minutes=None,
                mechanism="cold_start_synthetic",
                confidence=0.4,
                sample_size=0,
            )
        )
    db.commit()
    set_current_user_id(user.user_id)

    with patch("app.workers.jobs.resume_prediction.ResumePredictor") as mock_cls, \
         _patch_delivery() as patched:
        mock_cls.return_value.predict.return_value = _prediction(
            user.user_id, session, task
        )
        _run_for_one_user(db, user)

    assert db.query(ResumePredictionLog).count() == MAX_FIRES_PER_SESSION
    assert mock_cls.return_value.predict.call_count == 0
    assert patched["enqueue_user_notification"].call_count == 0


def test_resume_prediction_job_stays_scoped_to_current_user(db):
    user_a = _make_user(db, user_id=921)
    user_b = _make_user(db, user_id=922)
    task_a, session_a, _pause_a = _make_paused_task_with_open_pause(
        db, user_a.user_id
    )
    _task_b, _session_b, _pause_b = _make_paused_task_with_open_pause(
        db, user_b.user_id
    )
    set_current_user_id(user_a.user_id)

    with patch("app.workers.jobs.resume_prediction.ResumePredictor") as mock_cls, \
         _patch_delivery():
        mock_cls.return_value.predict.return_value = _prediction(
            user_a.user_id, session_a, task_a
        )
        _run_for_one_user(db, user_a)

    rows = db.query(ResumePredictionLog).all()
    assert len(rows) == 1
    assert rows[0].user_id == user_a.user_id
    assert rows[0].task_id == task_a.task_id
    assert mock_cls.return_value.predict.call_count == 1
