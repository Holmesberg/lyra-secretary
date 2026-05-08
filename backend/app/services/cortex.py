"""Cortex Core v0 read-time contract helpers.

This module implements the canonicalization layer documented in
``docs/cortex_contract_v0.md``. It intentionally does not write new state.
All metrics are derived at query time from existing observables.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.db.models import (
    CalibrationNudgeEvent,
    Deadline,
    PauseEvent,
    PausePredictionLog,
    ReflectionViewLog,
    ResumePredictionLog,
    StopwatchSession,
    Task,
    TaskState,
)
from app.utils.time_utils import now_utc, strip_tz

CortexProvenance = Literal[
    "observed",
    "self_reported",
    "derived",
    "retroactive",
    "external_import",
    "system_recovered",
    "unknown",
]
CortexExposureState = Literal["none", "exposed", "intervention", "unknown"]
CortexTopology = Literal["bounded", "expanding", "fragmented", "biological", "unknown"]

EVENT_FIELDS = (
    "event_id",
    "source",
    "source_id",
    "user_id",
    "task_id",
    "event_type",
    "occurred_at",
    "provenance",
    "exposure_state",
    "payload",
)

DERIVED_PAYLOAD_KEYS = {
    "execution_multiplier",
    "log_execution_multiplier",
    "active_delta_minutes",
    "wall_delta_minutes",
    "bias_factor",
    "duration_delta_minutes",
    "confidence_tier",
}

LATENT_PAYLOAD_KEYS = {
    "flow",
    "friction",
    "cognitive_load",
    "execution_quality",
    "readiness_state",
    "calibration",
    "self_model_error",
    "truth_gap",
    "quality_score",
    "productivity_score",
}

BIOLOGICAL_CATEGORIES = {"sleep", "meal", "meals", "food", "breakfast", "lunch", "dinner"}


@dataclass(frozen=True)
class CortexTaskMetrics:
    planned_active_minutes: float
    executed_active_minutes: float
    wall_clock_elapsed_minutes: Optional[float]
    paused_minutes: Optional[float]
    execution_multiplier: float
    log_execution_multiplier: float
    active_delta_minutes: float
    wall_delta_minutes: Optional[float]
    legacy_duration_delta_minutes: float


@dataclass(frozen=True)
class CortexEvent:
    event_id: str
    source: str
    source_id: str
    user_id: str
    task_id: Optional[str]
    event_type: str
    occurred_at: str
    provenance: CortexProvenance
    exposure_state: CortexExposureState
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # Keep the envelope exact even if the dataclass grows later.
        return {key: data[key] for key in EVENT_FIELDS}


def task_metrics(task: Task) -> CortexTaskMetrics:
    """Compute canonical Cortex metrics for one executed task.

    Raises ValueError when the row cannot support measured execution metrics.
    """
    planned = task.planned_duration_minutes
    executed = task.executed_duration_minutes
    if planned is None or planned <= 0:
        raise ValueError("planned_active_minutes must be > 0")
    if executed is None:
        raise ValueError("executed_active_minutes is required")

    planned_f = float(planned)
    executed_f = float(executed)
    execution_multiplier = executed_f / planned_f
    log_execution_multiplier = math.log(execution_multiplier)
    active_delta = executed_f - planned_f

    wall = None
    if task.executed_start_utc is not None and task.executed_end_utc is not None:
        start = strip_tz(task.executed_start_utc)
        end = strip_tz(task.executed_end_utc)
        if start is not None and end is not None:
            wall = max(0.0, (end - start).total_seconds() / 60.0)

    paused = wall - executed_f if wall is not None else None
    if paused is not None:
        paused = max(0.0, paused)

    return CortexTaskMetrics(
        planned_active_minutes=planned_f,
        executed_active_minutes=executed_f,
        wall_clock_elapsed_minutes=wall,
        paused_minutes=paused,
        execution_multiplier=execution_multiplier,
        log_execution_multiplier=log_execution_multiplier,
        active_delta_minutes=active_delta,
        wall_delta_minutes=(wall - planned_f) if wall is not None else None,
        legacy_duration_delta_minutes=planned_f - executed_f,
    )


def validate_event_payload(payload: dict[str, Any]) -> None:
    """Reject derived or latent keys in the raw Cortex event payload."""
    keys = set(payload)
    derived = sorted(keys & DERIVED_PAYLOAD_KEYS)
    latent = sorted(keys & LATENT_PAYLOAD_KEYS)
    if derived or latent:
        parts = []
        if derived:
            parts.append(f"derived={derived}")
        if latent:
            parts.append(f"latent={latent}")
        raise ValueError("Cortex payload cannot contain " + ", ".join(parts))


def cortex_event(
    *,
    source: str,
    source_id: str,
    user_id: int | str,
    task_id: Optional[str],
    event_type: str,
    occurred_at: datetime,
    provenance: CortexProvenance,
    exposure_state: CortexExposureState,
    payload: dict[str, Any],
) -> CortexEvent:
    validate_event_payload(payload)
    event_id = f"{source}:{source_id}:{event_type}"
    return CortexEvent(
        event_id=event_id,
        source=source,
        source_id=str(source_id),
        user_id=str(user_id),
        task_id=task_id,
        event_type=event_type,
        occurred_at=strip_tz(occurred_at).isoformat() if strip_tz(occurred_at) else "",
        provenance=provenance,
        exposure_state=exposure_state,
        payload=payload,
    )


def measured_execution_query(
    db: Session,
    *,
    user_id: int,
    cutoff: Optional[datetime] = None,
) -> Query:
    q = db.query(Task).filter(
        Task.user_id == user_id,
        Task.state == TaskState.EXECUTED,
        Task.voided_at.is_(None),
        Task.initiation_status != "system_error",
        Task.initiation_status != "retroactive",
        Task.executed_duration_minutes.isnot(None),
        Task.planned_duration_minutes >= 5,
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
            StopwatchSession.data_quality_flag.is_(None),
            Task.voided_at.is_(None),
        )
    )
    if cutoff is not None:
        q = q.filter(PauseEvent.paused_at_utc >= cutoff)
    return q


def classify_topology(task: Task) -> CortexTopology:
    """Strict v0 topology classifier.

    Returns ``unknown`` when evidence is missing or conflicting. This is
    deliberately conservative: topology is a hypothesis, not ground truth.
    """
    labels: set[CortexTopology] = set()
    category = (task.category or "").strip().lower()

    if category in BIOLOGICAL_CATEGORIES:
        labels.add("biological")

    if task.scope_outcome == "expanded":
        labels.add("expanding")
    elif (
        task.scope_bullet_count_at_plan is not None
        and task.scope_bullet_count_at_execute is not None
        and task.scope_bullet_count_at_plan >= 2
        and task.scope_bullet_count_at_execute >= math.ceil(task.scope_bullet_count_at_plan * 1.5)
        and (task.scope_bullet_count_at_execute - task.scope_bullet_count_at_plan) >= 2
    ):
        labels.add("expanding")

    if (task.pause_count or 0) >= 3 or task.parent_task_id is not None or task.interruption_type is not None:
        labels.add("fragmented")

    if (
        not labels
        and (
            task.scope_outcome == "stuck_to_plan"
            or (
                task.scope_bullet_count_at_plan is not None
                and task.scope_bullet_count_at_execute is not None
                and task.scope_bullet_count_at_plan == task.scope_bullet_count_at_execute
            )
        )
    ):
        labels.add("bounded")

    if len(labels) == 1:
        return next(iter(labels))
    return "unknown"


def cortex_diagnostics(db: Session, *, user_id: int, window_days: int = 30) -> dict[str, Any]:
    cutoff = now_utc() - timedelta(days=max(1, min(365, int(window_days))))

    base = db.query(Task).filter(Task.user_id == user_id, Task.planned_start_utc >= cutoff)
    exclusions = {
        "not_executed": base.filter(Task.state != TaskState.EXECUTED).count(),
        "voided": base.filter(Task.voided_at.isnot(None)).count(),
        "system_error": base.filter(Task.initiation_status == "system_error").count(),
        "retroactive": base.filter(Task.initiation_status == "retroactive").count(),
        "missing_executed_duration": base.filter(
            Task.state == TaskState.EXECUTED,
            Task.executed_duration_minutes.is_(None),
        ).count(),
        "planned_under_5": base.filter(Task.planned_duration_minutes < 5).count(),
    }

    external_deadline_bound = (
        base.outerjoin(Deadline, Task.deadline_id == Deadline.deadline_id)
        .filter(Task.deadline_id.isnot(None), Deadline.external_source.isnot(None))
        .count()
    )
    exclusions["external_deadline_bound"] = external_deadline_bound

    measured_tasks = measured_execution_query(db, user_id=user_id, cutoff=cutoff).all()
    planning_tasks = planning_calibration_query(db, user_id=user_id, cutoff=cutoff).all()
    pause_rows = pause_process_query(db, user_id=user_id, cutoff=cutoff).all()

    by_category: dict[str, list[CortexTaskMetrics]] = defaultdict(list)
    topology_counts: Counter[str] = Counter()
    invariant_violations: list[dict[str, Any]] = []

    for task in measured_tasks:
        topology_counts[classify_topology(task)] += 1
        try:
            metric = task_metrics(task)
        except ValueError as exc:
            invariant_violations.append({"task_id": task.task_id, "reason": str(exc)})
            continue
        by_category[task.category or "uncategorized"].append(metric)

    category_summary = {}
    for category, rows in sorted(by_category.items()):
        if not rows:
            continue
        sum_planned = sum(r.planned_active_minutes for r in rows)
        sum_executed = sum(r.executed_active_minutes for r in rows)
        logs = [r.log_execution_multiplier for r in rows]
        category_summary[category] = {
            "n": len(rows),
            "execution_multiplier_sum_ratio": round(sum_executed / sum_planned, 3) if sum_planned else None,
            "mean_log_execution_multiplier": round(sum(logs) / len(logs), 4),
            "overrun_count": sum(1 for r in rows if r.execution_multiplier > 1.0),
            "underrun_count": sum(1 for r in rows if r.execution_multiplier < 1.0),
        }

    exposure_counts = {
        "reflection_impressions": db.query(ReflectionViewLog).filter(
            ReflectionViewLog.user_id == user_id,
            ReflectionViewLog.event_class == "impression",
            ReflectionViewLog.fired_at >= cutoff,
        ).count(),
        "reflection_telemetry": db.query(ReflectionViewLog).filter(
            ReflectionViewLog.user_id == user_id,
            ReflectionViewLog.event_class == "telemetry",
            ReflectionViewLog.fired_at >= cutoff,
        ).count(),
        "pause_predictions": db.query(PausePredictionLog).filter(
            PausePredictionLog.user_id == user_id,
            PausePredictionLog.fired_at >= cutoff,
        ).count(),
        "resume_predictions": db.query(ResumePredictionLog).filter(
            ResumePredictionLog.user_id == user_id,
            ResumePredictionLog.fired_at >= cutoff,
        ).count(),
        "calibration_nudges": db.query(CalibrationNudgeEvent).filter(
            CalibrationNudgeEvent.user_id == user_id,
            CalibrationNudgeEvent.decided_at >= cutoff,
        ).count(),
    }

    return {
        "schema_version": "cortex_contract_v0",
        "window_days": max(1, min(365, int(window_days))),
        "counts": {
            "tasks_in_window": base.count(),
            "measured_execution": len(measured_tasks),
            "planning_calibration": len(planning_tasks),
            "pause_process_events": len(pause_rows),
        },
        "exclusions": exclusions,
        "topology_counts": dict(sorted(topology_counts.items())),
        "by_category": category_summary,
        "exposure_counts": exposure_counts,
        "invariant_violations": invariant_violations,
        "notes": [
            "Cortex v0 computes derived metrics at read time; no derived metrics are persisted.",
            "Latent topology labels are conservative hypotheses, not ground truth.",
        ],
    }
