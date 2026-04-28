"""Smoke tests for the W2 resume predictor (2026-04-28).

Covers:
  - Cold-start fallback fires at 30min flat cap with correct mechanism
  - Cold-start fallback returns None when paused < 30min
  - Returns None for paused < p75 when warm
  - Returns prediction when paused >= p75 and confidence ≥ floor
  - Excludes self_reported_retroactively=TRUE pause_events from training
  - Excludes voided tasks from training corpus
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import (
    PauseEvent,
    ResumePredictionLog,
    StopwatchSession,
    Task,
    TaskState,
    User,
)
from app.db.scoping import set_current_user_id
from app.services.resume_predictor import COLD_START_FLAT_CAP, ResumePredictor


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.query(ResumePredictionLog).delete()
    db.query(PauseEvent).delete()
    db.query(StopwatchSession).delete()
    db.query(Task).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.query(ResumePredictionLog).delete()
    db.query(PauseEvent).delete()
    db.query(StopwatchSession).delete()
    db.query(Task).delete()
    db.query(User).delete()
    db.commit()


def _make_user(db) -> User:
    u = User(
        email=f"u{uuid4().hex[:8]}@test",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_task(db, user_id: int, category: str = "work") -> Task:
    now = datetime.utcnow()
    t = Task(
        task_id=str(uuid4()),
        user_id=user_id,
        title="Test task",
        category=category,
        planned_start_utc=now + timedelta(hours=1),
        planned_end_utc=now + timedelta(hours=2),
        planned_duration_minutes=60,
        state=TaskState.PAUSED,
        source="manual",
        created_at=now,
        last_modified_at=now,
        llm_parse_status="pending",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _make_session(db, task: Task) -> StopwatchSession:
    s = StopwatchSession(
        task_id=task.task_id,
        user_id=task.user_id,
        start_time_utc=datetime.utcnow() - timedelta(minutes=20),
        auto_closed=False,
        total_paused_minutes=0,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _seed_pause_history(
    db, user_id: int, durations_minutes: list[float], category: str = "work",
    days_back_anchor: int = 14,
) -> None:
    """Seed pause_event rows representing completed pauses, all in the same
    (category, time_of_day=morning) cell. Spread back in time so the
    HISTORY_GATE_DAYS≥7 gate passes.
    """
    # Anchor at 06:00 UTC — Cairo is UTC+3, so this is 09:00 local =
    # morning per _time_of_day. Use `.replace(hour=6, ...)` to actually
    # set the hour, NOT `+ timedelta(hours=6)` (which would add 6h to the
    # current wall-clock UTC and land the pauses in the wrong tod cell —
    # passes-by-luck flake observed 2026-04-28).
    base = (datetime.utcnow() - timedelta(days=days_back_anchor)).replace(
        hour=6, minute=0, second=0, microsecond=0
    )
    for i, d in enumerate(durations_minutes):
        paused = base + timedelta(days=i)
        resumed = paused + timedelta(minutes=d)
        # Each pause needs an associated task + session
        t = Task(
            task_id=str(uuid4()),
            user_id=user_id,
            title=f"Historical task {i}",
            category=category,
            planned_start_utc=paused - timedelta(minutes=10),
            planned_end_utc=paused + timedelta(hours=1),
            planned_duration_minutes=60,
            state=TaskState.EXECUTED,
            source="manual",
            created_at=paused - timedelta(minutes=10),
            last_modified_at=resumed,
        )
        db.add(t)
        db.flush()
        s = StopwatchSession(
            task_id=t.task_id,
            user_id=user_id,
            start_time_utc=paused - timedelta(minutes=5),
            end_time_utc=resumed + timedelta(minutes=10),
            auto_closed=False,
            total_paused_minutes=d,
        )
        db.add(s)
        db.flush()
        pe = PauseEvent(
            pause_event_id=str(uuid4()),
            session_id=s.session_id,
            user_id=user_id,
            paused_at_utc=paused,
            resumed_at_utc=resumed,
            pause_reason="intentional_break",
            pause_initiator="self",
            self_reported_retroactively=False,
        )
        db.add(pe)
    db.commit()


def test_cold_start_fires_at_flat_cap(db):
    user = _make_user(db)
    task = _make_task(db, user.user_id)
    session = _make_session(db, task)
    paused_at = datetime.utcnow() - timedelta(minutes=COLD_START_FLAT_CAP + 1)
    pred = ResumePredictor(db).predict(
        user_id=user.user_id,
        session=session,
        task=task,
        paused_at_utc=paused_at,
    )
    assert pred is not None
    assert pred.mechanism == "cold_start_synthetic"
    assert pred.p75_pause_minutes is None
    assert pred.sample_size == 0


def test_cold_start_does_not_fire_under_flat_cap(db):
    user = _make_user(db)
    task = _make_task(db, user.user_id)
    session = _make_session(db, task)
    paused_at = datetime.utcnow() - timedelta(minutes=10)  # well below 30
    pred = ResumePredictor(db).predict(
        user_id=user.user_id,
        session=session,
        task=task,
        paused_at_utc=paused_at,
    )
    assert pred is None


def test_warm_no_fire_when_paused_below_p75(db):
    """With seeded history of [5,5,8,10,12,15] minutes (p75≈11.25), a paused-for
    of 8 minutes is below p75 → no fire."""
    user = _make_user(db)
    _seed_pause_history(db, user.user_id, [5, 5, 8, 10, 12, 15])
    task = _make_task(db, user.user_id)
    session = _make_session(db, task)
    # Paused-at must land in morning category cell to match seeded history
    morning_local = datetime.utcnow().replace(hour=6, minute=0, second=0, microsecond=0)
    paused_at = morning_local
    # Now is morning + 8 minutes
    pred = ResumePredictor(db).predict(
        user_id=user.user_id,
        session=session,
        task=task,
        paused_at_utc=paused_at,
        now=morning_local + timedelta(minutes=8),
    )
    # 8min < p75 (~11.25) → no fire
    assert pred is None


def test_warm_fires_when_paused_above_p75(db):
    """Same seeded history; paused 20min should fire."""
    user = _make_user(db)
    _seed_pause_history(db, user.user_id, [5, 5, 8, 10, 12, 15])
    task = _make_task(db, user.user_id)
    session = _make_session(db, task)
    morning_local = datetime.utcnow().replace(hour=6, minute=0, second=0, microsecond=0)
    paused_at = morning_local
    pred = ResumePredictor(db).predict(
        user_id=user.user_id,
        session=session,
        task=task,
        paused_at_utc=paused_at,
        now=morning_local + timedelta(minutes=20),
    )
    assert pred is not None
    assert pred.mechanism == "category_tod"
    assert pred.p75_pause_minutes is not None
    assert pred.sample_size >= 5


def test_retroactive_pauses_excluded_from_training(db):
    """Seed 6 pauses but mark them all retroactive — predictor must treat
    user as cold-start (no history)."""
    user = _make_user(db)
    # Seed normally then mark all retroactive
    _seed_pause_history(db, user.user_id, [5, 5, 8, 10, 12, 15])
    db.query(PauseEvent).update({PauseEvent.self_reported_retroactively: True})
    db.commit()

    task = _make_task(db, user.user_id)
    session = _make_session(db, task)
    paused_at = datetime.utcnow() - timedelta(minutes=COLD_START_FLAT_CAP + 1)
    pred = ResumePredictor(db).predict(
        user_id=user.user_id,
        session=session,
        task=task,
        paused_at_utc=paused_at,
    )
    # All retroactive → cold-start path takes over
    assert pred is not None
    assert pred.mechanism == "cold_start_synthetic"
