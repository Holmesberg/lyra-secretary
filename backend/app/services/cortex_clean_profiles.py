"""Cortex clean-data profile query helpers.

These helpers centralize the read-only row-eligibility profiles used by Cortex
and analytics compatibility paths. They must not mutate domain state.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.db.models import (
    Deadline,
    PauseEvent,
    StopwatchSession,
    Task,
    TaskExecutionCorrection,
    TaskState,
)
from app.services.exposure_ledger import exposure_results_for_task


def measured_execution_query(
    db: Session,
    *,
    user_id: int,
    cutoff: Optional[datetime] = None,
) -> Query:
    clean_stopwatch_exists = (
        db.query(StopwatchSession.session_id)
        .filter(
            StopwatchSession.task_id == Task.task_id,
            StopwatchSession.user_id == user_id,
            StopwatchSession.end_time_utc.isnot(None),
            StopwatchSession.auto_closed.is_(False),
            StopwatchSession.data_quality_flag.is_(None),
        )
        .exists()
    )
    auto_closed_stopwatch_exists = (
        db.query(StopwatchSession.session_id)
        .filter(
            StopwatchSession.task_id == Task.task_id,
            StopwatchSession.user_id == user_id,
            StopwatchSession.auto_closed.is_(True),
        )
        .exists()
    )
    q = db.query(Task).filter(
        Task.user_id == user_id,
        Task.state == TaskState.EXECUTED,
        Task.voided_at.is_(None),
        Task.is_anchor.is_(False),
        Task.initiation_status != "system_error",
        Task.initiation_status != "retroactive",
        Task.executed_duration_minutes.isnot(None),
        Task.planned_duration_minutes >= 5,
        ~db.query(TaskExecutionCorrection.correction_id)
        .filter(TaskExecutionCorrection.task_id == Task.task_id)
        .exists(),
        clean_stopwatch_exists,
        ~auto_closed_stopwatch_exists,
    )
    if cutoff is not None:
        q = q.filter(Task.planned_start_utc >= cutoff)
    return q


def planning_calibration_query(
    db: Session,
    *,
    user_id: int,
    cutoff: Optional[datetime] = None,
) -> Query:
    q = (
        measured_execution_query(db, user_id=user_id, cutoff=cutoff)
        .outerjoin(Deadline, Task.deadline_id == Deadline.deadline_id)
        .filter(or_(Task.deadline_id.is_(None), Deadline.external_source.is_(None)))
    )
    return q


def measured_execution_baseline_tasks(
    db: Session,
    *,
    user_id: int,
    cutoff: Optional[datetime] = None,
) -> list[Task]:
    """Measured-execution rows that pass exposure context for duration behavior."""
    return [
        task
        for task in measured_execution_query(db, user_id=user_id, cutoff=cutoff).all()
        if all(
            result.state == "NONE"
            for result in exposure_results_for_task(
                db,
                task=task,
                signal_targets=["duration_behavior"],
            )
        )
    ]


def planning_calibration_baseline_tasks(
    db: Session,
    *,
    user_id: int,
    cutoff: Optional[datetime] = None,
) -> list[Task]:
    """Planning-calibration rows that pass exposure context for plan and execution."""
    return [
        task
        for task in planning_calibration_query(db, user_id=user_id, cutoff=cutoff).all()
        if all(
            result.state == "NONE"
            for result in exposure_results_for_task(
                db,
                task=task,
                signal_targets=["planning_estimate", "duration_behavior"],
            )
        )
    ]


def pause_process_query(
    db: Session,
    *,
    user_id: int,
    cutoff: Optional[datetime] = None,
) -> Query:
    q = (
        db.query(PauseEvent)
        .join(StopwatchSession, StopwatchSession.session_id == PauseEvent.session_id)
        .join(Task, Task.task_id == StopwatchSession.task_id)
        .filter(
            PauseEvent.user_id == user_id,
            PauseEvent.self_reported_retroactively.is_(False),
            StopwatchSession.auto_closed.is_(False),
            StopwatchSession.data_quality_flag.is_(None),
            Task.voided_at.is_(None),
        )
    )
    if cutoff is not None:
        q = q.filter(PauseEvent.paused_at_utc >= cutoff)
    return q
