"""
Tests for LYR-061: Insights must not fire on noise data.
- _insight_discrepancy_signal() must return None when no real signal
- Global gate must block insights below MIN_SESSIONS
"""
from unittest.mock import MagicMock
from app.db.models import Task, TaskState
from app.api.v1.endpoints.analytics import (
    _insight_discrepancy_signal,
    _insight_time_of_day,
)
from app.utils.time_utils import now_utc
from datetime import timedelta


def _task(delta=None, disc_score=None, pre=None, post=None, state=TaskState.EXECUTED, tod_hour=9):
    t = MagicMock(spec=Task)
    t.state = state
    t.duration_delta_minutes = delta
    t.discrepancy_score = disc_score
    t.pre_task_readiness = pre
    t.post_task_reflection = post
    t.planned_start_utc = now_utc().replace(hour=tod_hour, minute=0, second=0)
    t.executed_end_utc = t.planned_start_utc + timedelta(minutes=60)
    t.executed_duration_minutes = 60 if delta is not None else None
    return t


def test_discrepancy_signal_returns_none_when_no_signal():
    """No 20% spread between high/low discrepancy buckets → None, not a noise message."""
    tasks = (
        [_task(delta=10, disc_score=4) for _ in range(3)] +
        [_task(delta=12, disc_score=0) for _ in range(3)]
    )
    result = _insight_discrepancy_signal(tasks)
    assert result is None


def test_discrepancy_signal_fires_when_real_signal():
    """High discrepancy sessions have significantly more error → insight fires."""
    tasks = (
        [_task(delta=50, disc_score=4) for _ in range(3)] +   # high disc, big error
        [_task(delta=5,  disc_score=0) for _ in range(3)]     # low disc, small error
    )
    result = _insight_discrepancy_signal(tasks)
    assert result is not None
    assert "higher" in result["observation"]


def test_discrepancy_signal_needs_min_3_per_bucket():
    """Returns None if either bucket has fewer than 3 sessions."""
    tasks = (
        [_task(delta=50, disc_score=4) for _ in range(2)] +
        [_task(delta=5,  disc_score=0) for _ in range(3)]
    )
    result = _insight_discrepancy_signal(tasks)
    assert result is None


def test_time_of_day_requires_3_sessions():
    """Should not fire with only 2 sessions in a time-of-day bucket."""
    tasks = [_task(delta=30, tod_hour=9), _task(delta=25, tod_hour=9)]
    result = _insight_time_of_day(tasks)
    assert result is None
