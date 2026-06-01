"""Unit tests for services/pause_predictor.py.

Pins the VT-17 research-integrity contract:
  * Predictor returns None while pause_event history < HISTORY_GATE_DAYS (7).
  * Small-sample buckets (<MIN_SAMPLES) suppress the firing.
  * Lead window is [MIN_LEAD_MINUTES, MAX_LEAD_MINUTES] (2–3 min).
  * clock_anchor bucket is (hour-of-day, weekday-vs-weekend).
  * work_rhythm excludes auto_closed + data_quality_flag + voided sessions.
  * MIN_CONFIDENCE floor suppresses low-confidence fires.

Datetimes are naive UTC throughout — matches the `now_utc()` convention
(utils/time_utils.py line 42-44 strips tzinfo before returning).
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.models import PauseEvent, StopwatchSession, Task, TaskState
from app.services import pause_predictor as pp
from app.services.pause_predictor import PausePredictor
from tests.conftest import TestingSession


@pytest.fixture
def clean_db(db):
    """Wipe pause_event, stopwatch_session, task between tests so seeded
    samples don't leak across predictor scenarios. Wipe on the same session
    we yield — using a separate TestingSession + StaticPool left stale rows
    visible to the test session across runs."""
    db.rollback()
    db.execute(text("DELETE FROM pause_event"))
    db.execute(text("DELETE FROM stopwatch_session"))
    db.execute(text("DELETE FROM task"))
    db.commit()
    db.expire_all()
    yield db


def _seed_pause_event(db, *, user_id: int, paused_at: datetime, category: str = "dev"):
    """Seed a minimal (task, session, pause_event) triple with the pause at `paused_at`."""
    task = Task(
        task_id=str(uuid4()),
        user_id=user_id,
        title="seed",
        category=category,
        state=TaskState.EXECUTED,
        planned_start_utc=paused_at - timedelta(minutes=5),
        planned_end_utc=paused_at + timedelta(minutes=25),
        planned_duration_minutes=30,
        source="manual",
    )
    session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=user_id,
        start_time_utc=paused_at - timedelta(minutes=1),
        total_paused_minutes=0.0,
    )
    evt = PauseEvent(
        pause_event_id=str(uuid4()),
        session_id=session.session_id,
        user_id=user_id,
        paused_at_utc=paused_at,
        pause_reason="distraction",
        pause_initiator="self",
    )
    db.add_all([task, session, evt])
    db.commit()
    return task, session, evt


def _seed_rhythm_session(
    db,
    *,
    user_id: int,
    category: str,
    start_utc: datetime,
    first_pause_after_min: int,
    auto_closed: bool = False,
    data_quality_flag=None,
    voided: bool = False,
):
    """Seed a completed session with a known time-to-first-pause."""
    task = Task(
        task_id=str(uuid4()),
        user_id=user_id,
        title=f"rhythm-{category}",
        category=category,
        state=TaskState.EXECUTED,
        planned_start_utc=start_utc,
        planned_end_utc=start_utc + timedelta(minutes=60),
        planned_duration_minutes=60,
        executed_start_utc=start_utc,
        executed_end_utc=start_utc + timedelta(minutes=60),
        source="manual",
        voided_at=datetime.utcnow() if voided else None,
    )
    session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=user_id,
        start_time_utc=start_utc,
        end_time_utc=start_utc + timedelta(minutes=60),
        auto_closed=auto_closed,
        total_paused_minutes=0.0,
        data_quality_flag=data_quality_flag,
    )
    paused_at = start_utc + timedelta(minutes=first_pause_after_min)
    evt = PauseEvent(
        pause_event_id=str(uuid4()),
        session_id=session.session_id,
        user_id=user_id,
        paused_at_utc=paused_at,
        resumed_at_utc=paused_at + timedelta(minutes=2),
        duration_minutes=2.0,
        pause_reason="distraction",
        pause_initiator="self",
    )
    db.add_all([task, session, evt])
    db.commit()
    return task, session


# ---------- History gate ----------

def test_predict_returns_none_when_history_under_7_days(clean_db):
    now = datetime(2026, 4, 14, 10, 45)  # Tuesday, weekday
    _seed_pause_event(clean_db, user_id=1, paused_at=now - timedelta(days=6))
    assert PausePredictor(clean_db).predict(user_id=1, active_task=None, now=now) is None


def test_predict_returns_none_when_user_has_no_history(clean_db):
    now = datetime(2026, 4, 14, 10, 45)
    assert PausePredictor(clean_db).predict(user_id=999, active_task=None, now=now) is None


# ---------- Clock anchor ----------

def test_clock_anchor_fires_when_bucket_has_enough_samples(clean_db):
    """Seed ≥5 weekday 10:48 pauses, predict at weekday 10:45 — expect ~3 min lead."""
    now = datetime(2026, 4, 13, 10, 45)  # Monday (weekday 0)
    # All within 28-day lookback; all weekdays relative to 2026-04-13.
    for day_offset in [3, 4, 5, 6, 7, 10, 11, 12, 13, 14]:
        paused = (now - timedelta(days=day_offset)).replace(
            hour=10, minute=48, second=0, microsecond=0
        )
        assert paused.weekday() < 5, f"seed day {paused} wasn't a weekday"
        _seed_pause_event(clean_db, user_id=1, paused_at=paused)

    result = PausePredictor(clean_db).predict(user_id=1, active_task=None, now=now)
    assert result is not None
    assert result.mechanism == "clock_anchor"
    assert 2 <= result.lead_minutes <= 3
    assert result.sample_size >= 5
    assert result.predicted_at.hour == 10


def test_clock_anchor_weekend_samples_excluded_on_weekday(clean_db):
    """Weekday prediction must not count weekend pauses in the bucket."""
    now = datetime(2026, 4, 13, 10, 45)  # Monday
    # Seed weekend pauses only — bucket filter should exclude all.
    for day_offset in [5, 6, 12, 13, 19, 20, 26, 27]:
        paused = (now - timedelta(days=day_offset)).replace(
            hour=10, minute=48, second=0, microsecond=0
        )
        if paused.weekday() < 5:
            continue
        _seed_pause_event(clean_db, user_id=1, paused_at=paused)
    # Plus an older row so history gate is satisfied but bucket stays empty.
    _seed_pause_event(
        clean_db, user_id=1,
        paused_at=now - timedelta(days=10, hours=3),
    )
    assert PausePredictor(clean_db).predict(user_id=1, active_task=None, now=now) is None


def test_clock_anchor_out_of_lead_window_returns_none(clean_db):
    """Median minute 10:50, now 10:45 — lead = 5 min, above MAX_LEAD_MINUTES."""
    now = datetime(2026, 4, 13, 10, 45)
    for day_offset in [3, 4, 5, 6, 7, 10, 11, 12, 13, 14]:
        paused = (now - timedelta(days=day_offset)).replace(
            hour=10, minute=50, second=0, microsecond=0
        )
        _seed_pause_event(clean_db, user_id=1, paused_at=paused)
    assert PausePredictor(clean_db).predict(user_id=1, active_task=None, now=now) is None


def test_clock_anchor_small_sample_returns_none(clean_db):
    """3 bucket samples — below MIN_SAMPLES=5."""
    now = datetime(2026, 4, 13, 10, 45)
    for day_offset in [3, 6, 10]:  # all weekdays
        paused = (now - timedelta(days=day_offset)).replace(
            hour=10, minute=48, second=0, microsecond=0
        )
        _seed_pause_event(clean_db, user_id=1, paused_at=paused)
    # History gate filler outside the bucket.
    _seed_pause_event(
        clean_db, user_id=1,
        paused_at=now - timedelta(days=10, hours=3),
    )
    assert PausePredictor(clean_db).predict(user_id=1, active_task=None, now=now) is None


# ---------- Work rhythm ----------

def test_work_rhythm_fires_when_category_has_enough_samples(clean_db):
    """5 historical dev sessions pause at ~28 min in; active task started 25 min ago.
    Predicted pause = start + 28 → 3 min lead."""
    now = datetime(2026, 4, 13, 10, 45)
    active_start = now - timedelta(minutes=25)

    # History-gate filler uses a non-dev category so it doesn't pollute the
    # work_rhythm query (which filters by category).
    _seed_pause_event(
        clean_db, user_id=1,
        paused_at=now - timedelta(days=10),
        category="other",
    )
    for d in [2, 3, 4, 5, 6]:
        _seed_rhythm_session(
            clean_db, user_id=1, category="dev",
            start_utc=now - timedelta(days=d),
            first_pause_after_min=28,
        )

    active_task = Task(
        task_id=str(uuid4()),
        user_id=1,
        title="active",
        category="dev",
        state=TaskState.EXECUTING,
        planned_start_utc=active_start,
        planned_end_utc=active_start + timedelta(minutes=60),
        planned_duration_minutes=60,
        executed_start_utc=active_start,
        source="manual",
    )
    clean_db.add(active_task)
    clean_db.commit()

    result = PausePredictor(clean_db).predict(
        user_id=1, active_task=active_task, now=now
    )
    assert result is not None
    assert result.mechanism == "work_rhythm"
    assert 2 <= result.lead_minutes <= 3
    assert result.active_task_id == active_task.task_id
    assert result.sample_size == 5


def test_work_rhythm_uses_open_session_start_for_live_task(clean_db):
    """Live EXECUTING tasks do not get executed_start_utc until stop.

    The predictor must anchor against the open StopwatchSession start while
    the timer is running; otherwise the work-rhythm mechanism can never fire
    in the moment it is meant to help.
    """
    now = datetime(2026, 4, 13, 10, 45)
    active_start = now - timedelta(minutes=25)

    _seed_pause_event(
        clean_db, user_id=1,
        paused_at=now - timedelta(days=10),
        category="other",
    )
    for d in [2, 3, 4, 5, 6]:
        _seed_rhythm_session(
            clean_db, user_id=1, category="study",
            start_utc=now - timedelta(days=d),
            first_pause_after_min=28,
        )

    active_task = Task(
        task_id=str(uuid4()),
        user_id=1,
        title="active study",
        category="study",
        state=TaskState.EXECUTING,
        planned_start_utc=active_start,
        planned_end_utc=active_start + timedelta(minutes=60),
        planned_duration_minutes=60,
        executed_start_utc=None,
        source="manual",
    )
    active_session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=active_task.task_id,
        user_id=1,
        start_time_utc=active_start,
        end_time_utc=None,
        auto_closed=False,
        total_paused_minutes=0.0,
    )
    clean_db.add_all([active_task, active_session])
    clean_db.commit()

    result = PausePredictor(clean_db).predict(
        user_id=1, active_task=active_task, now=now
    )

    assert result is not None
    assert result.mechanism == "work_rhythm"
    assert 2 <= result.lead_minutes <= 3
    assert result.active_task_id == active_task.task_id


def test_work_rhythm_excludes_contaminated_sessions(clean_db):
    """Flagged / auto_closed / voided sessions must not contribute."""
    now = datetime(2026, 4, 13, 10, 45)
    active_start = now - timedelta(minutes=25)
    _seed_pause_event(clean_db, user_id=1, paused_at=now - timedelta(days=10))

    # 3 clean + 3 contaminated. After exclusion: 3 < MIN_SAMPLES.
    for d in [2, 3, 4]:
        _seed_rhythm_session(
            clean_db, user_id=1, category="dev",
            start_utc=now - timedelta(days=d),
            first_pause_after_min=28,
        )
    _seed_rhythm_session(
        clean_db, user_id=1, category="dev",
        start_utc=now - timedelta(days=5),
        first_pause_after_min=28,
        data_quality_flag="pause_reason_lost_to_overwrite",
    )
    _seed_rhythm_session(
        clean_db, user_id=1, category="dev",
        start_utc=now - timedelta(days=6),
        first_pause_after_min=28,
        auto_closed=True,
    )
    _seed_rhythm_session(
        clean_db, user_id=1, category="dev",
        start_utc=now - timedelta(days=7),
        first_pause_after_min=28,
        voided=True,
    )

    active_task = Task(
        task_id=str(uuid4()),
        user_id=1,
        title="active",
        category="dev",
        state=TaskState.EXECUTING,
        planned_start_utc=active_start,
        planned_end_utc=active_start + timedelta(minutes=60),
        planned_duration_minutes=60,
        executed_start_utc=active_start,
        source="manual",
    )
    clean_db.add(active_task)
    clean_db.commit()

    assert PausePredictor(clean_db).predict(
        user_id=1, active_task=active_task, now=now
    ) is None


# ---------- Firing-threshold floor ----------

def test_predict_suppresses_when_confidence_below_floor(clean_db, monkeypatch):
    """Raising MIN_CONFIDENCE above computable max suppresses all fires."""
    monkeypatch.setattr(pp, "MIN_CONFIDENCE", 0.99)
    now = datetime(2026, 4, 13, 10, 45)
    for day_offset in [3, 4, 5, 6, 7, 10, 11, 12, 13, 14]:
        paused = (now - timedelta(days=day_offset)).replace(
            hour=10, minute=48, second=0, microsecond=0
        )
        _seed_pause_event(clean_db, user_id=1, paused_at=paused)
    assert PausePredictor(clean_db).predict(user_id=1, active_task=None, now=now) is None
