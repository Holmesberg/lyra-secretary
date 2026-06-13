"""Interruption-derived metrics for recovery and planning surfaces.

Execution time stays canonical active work. This module computes the
downstream planning footprint around it: pause overhead, session span,
occupancy time, execution efficiency, and recovery friction.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import median
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import PauseEvent, StopwatchSession, Task
from app.utils.time_utils import to_local


MIN_PAUSE_OVERHEAD_SAMPLES = 3
MAX_CLEAN_PAUSE_OVERHEAD_MINUTES = 240.0
MAX_CLEAN_SESSION_SPAN_MINUTES = 8 * 60.0


@dataclass(frozen=True)
class TaskInterruptionMetrics:
    execution_time_minutes: Optional[int]
    session_span_minutes: Optional[int]
    pause_overhead_minutes: int
    occupancy_time_minutes: Optional[int]
    execution_efficiency: Optional[float]
    recovery_friction_minutes: Optional[int]


def round_to_nearest_5(minutes: float) -> int:
    """Round a positive planning window to the nearest 5-minute boundary."""
    return max(5, int(round(minutes / 5.0) * 5))


def duration_bucket(minutes: int) -> str:
    if minutes < 30:
        return "short"
    if minutes > 60:
        return "long"
    return "medium"


def _time_of_day(local_dt) -> str:
    h = local_dt.hour
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 17:
        return "afternoon"
    if 17 <= h < 21:
        return "evening"
    return "night"


def _session_wall_minutes(session: StopwatchSession) -> Optional[float]:
    if session.start_time_utc is None or session.end_time_utc is None:
        return None
    return (session.end_time_utc - session.start_time_utc).total_seconds() / 60.0


def _is_clean_closed_session(session: StopwatchSession) -> bool:
    if session.end_time_utc is None:
        return False
    if session.auto_closed:
        return False
    if session.data_quality_flag is not None:
        return False
    wall = _session_wall_minutes(session)
    if wall is None or wall < 0 or wall > MAX_CLEAN_SESSION_SPAN_MINUTES:
        return False
    paused = float(session.total_paused_minutes or 0.0)
    if paused < 0 or paused > MAX_CLEAN_PAUSE_OVERHEAD_MINUTES:
        return False
    if paused > wall:
        return False
    return True


def _task_pause_overhead_sample(sessions: list[StopwatchSession]) -> Optional[float]:
    """Return one clean task-level pause-overhead sample, including zero."""
    if not sessions:
        return None
    if any(not _is_clean_closed_session(session) for session in sessions):
        return None
    overhead = sum(float(session.total_paused_minutes or 0.0) for session in sessions)
    span = sum(float(_session_wall_minutes(session) or 0.0) for session in sessions)
    if overhead > MAX_CLEAN_PAUSE_OVERHEAD_MINUTES:
        return None
    if span <= 0 or span > MAX_CLEAN_SESSION_SPAN_MINUTES:
        return None
    return overhead


def _task_matches_signal(
    task: Task,
    *,
    category: str,
    tod: str,
    planned_minutes: int,
    signal_level: str,
) -> bool:
    if getattr(task, "initiation_status", None) == "retroactive":
        return False
    if (task.category or "uncategorized") != category:
        return False
    if signal_level in {"category_tod", "category_tod_duration"}:
        if _time_of_day(to_local(task.planned_start_utc)) != tod:
            return False
    if signal_level == "category_tod_duration":
        if duration_bucket(task.planned_duration_minutes) != duration_bucket(planned_minutes):
            return False
    return signal_level in {"category", "category_tod", "category_tod_duration"}


def pause_overhead_samples_for_signal(
    db: Session,
    *,
    tasks: list[Task],
    category: str,
    tod: str,
    planned_minutes: int,
    signal_level: str,
) -> list[float]:
    """Clean personal pause-overhead samples for the same bias signal cell.

    Each task contributes one value. Zero-pause sessions are retained; dirty,
    auto-closed, stale, overnight-sized, and open sessions exclude the task.
    """
    matched = [
        task for task in tasks
        if _task_matches_signal(
            task,
            category=category,
            tod=tod,
            planned_minutes=planned_minutes,
            signal_level=signal_level,
        )
    ]
    task_ids = [task.task_id for task in matched]
    if not task_ids:
        return []

    sessions_by_task: dict[str, list[StopwatchSession]] = defaultdict(list)
    for session in (
        db.query(StopwatchSession)
        .filter(StopwatchSession.task_id.in_(task_ids))
        .all()
    ):
        sessions_by_task[session.task_id].append(session)

    samples: list[float] = []
    for task in matched:
        sample = _task_pause_overhead_sample(sessions_by_task.get(task.task_id, []))
        if sample is not None:
            samples.append(sample)
    return samples


def occupancy_projection(
    db: Session,
    *,
    tasks: list[Task],
    category: str,
    tod: str,
    planned_minutes: int,
    bias_factor_final: float,
    source: Optional[str],
    signal_level: Optional[str],
) -> dict:
    """Project a planning-window footprint without changing execution truth."""
    execution_suggested = round_to_nearest_5(planned_minutes * bias_factor_final)
    base = {
        "execution_suggested_minutes": execution_suggested,
        "pause_overhead_minutes": 0,
        "pause_overhead_sample_size": 0,
        "occupancy_suggested_minutes": execution_suggested,
        "occupancy_strategy": "execution_only",
        "occupancy_factor": round(execution_suggested / planned_minutes, 3)
        if planned_minutes > 0 else None,
    }

    if source != "personal" or signal_level == "research":
        base["occupancy_strategy"] = "execution_only_research_prior"
        return base

    samples = pause_overhead_samples_for_signal(
        db,
        tasks=tasks,
        category=category,
        tod=tod,
        planned_minutes=planned_minutes,
        signal_level=signal_level or "",
    )
    base["pause_overhead_sample_size"] = len(samples)
    if len(samples) < MIN_PAUSE_OVERHEAD_SAMPLES:
        base["occupancy_strategy"] = "execution_only_insufficient_pause_overhead"
        return base

    pause_overhead = int(round(median(samples)))
    occupancy = round_to_nearest_5(execution_suggested + pause_overhead)
    return {
        **base,
        "pause_overhead_minutes": pause_overhead,
        "occupancy_suggested_minutes": occupancy,
        "occupancy_strategy": "execution_plus_median_pause_overhead",
        "occupancy_factor": round(occupancy / planned_minutes, 3)
        if planned_minutes > 0 else None,
    }


def task_interruption_metrics_from_sessions(
    task: Task,
    sessions: list[StopwatchSession],
    *,
    recovery_friction_minutes: Optional[int] = None,
) -> TaskInterruptionMetrics:
    """Observed interruption metrics from already-loaded session rows."""
    clean_sessions = [
        session for session in sessions
        if _is_clean_closed_session(session)
    ]

    execution = task.executed_duration_minutes
    pause_overhead = int(round(
        sum(float(session.total_paused_minutes or 0.0) for session in clean_sessions)
    ))
    span_raw = sum(float(_session_wall_minutes(session) or 0.0) for session in clean_sessions)
    span = int(round(span_raw)) if span_raw > 0 else None
    occupancy = (
        int(execution) + pause_overhead
        if execution is not None
        else None
    )
    efficiency = (
        round(float(execution) / span, 3)
        if execution is not None and span and span > 0
        else None
    )

    return TaskInterruptionMetrics(
        execution_time_minutes=execution,
        session_span_minutes=span,
        pause_overhead_minutes=pause_overhead,
        occupancy_time_minutes=occupancy,
        execution_efficiency=efficiency,
        recovery_friction_minutes=recovery_friction_minutes,
    )


def task_interruption_metrics(db: Session, task: Task) -> TaskInterruptionMetrics:
    """Observed interruption metrics for a completed task."""
    sessions = (
        db.query(StopwatchSession)
        .filter(StopwatchSession.task_id == task.task_id)
        .all()
    )
    clean_sessions = [
        session for session in sessions
        if _is_clean_closed_session(session)
    ]
    session_ids = [session.session_id for session in clean_sessions]
    pause_durations: list[float] = []
    if session_ids:
        events = (
            db.query(PauseEvent)
            .filter(
                PauseEvent.session_id.in_(session_ids),
                PauseEvent.duration_minutes.is_not(None),
                PauseEvent.self_reported_retroactively.is_(False),
            )
            .all()
        )
        for event in events:
            duration = float(event.duration_minutes or 0.0)
            if 0 <= duration <= MAX_CLEAN_PAUSE_OVERHEAD_MINUTES:
                pause_durations.append(duration)

    return task_interruption_metrics_from_sessions(
        task,
        sessions,
        recovery_friction_minutes=(
            int(round(median(pause_durations))) if pause_durations else None
        ),
    )
