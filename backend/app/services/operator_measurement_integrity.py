"""Read-only measurement-integrity snapshot for the operator dashboard."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models import (
    Deadline,
    StopwatchSession,
    Task,
    TaskExecutionCorrection,
    TaskState,
    User,
)
from app.services.exposure_ledger import exposure_results_for_task
from app.services.operator_readiness import (
    READINESS_GREEN_TRACE_RATIO,
    READINESS_RED_TRACE_RATIO,
)
from app.services.operator_user_projection import (
    is_test_or_synthetic_user,
    pct,
    short_hash,
)


def _metric_meta(
    *,
    basis: str = "derived",
    confidence: str = "medium",
    readiness_impact: str = "informational",
) -> dict[str, Any]:
    return {
        "basis": basis,
        "confidence": confidence,
        "readiness_impact": readiness_impact,
    }


def _denominator_exclusion_for(
    session: StopwatchSession,
    task: Task,
    user: User,
) -> str | None:
    if user.is_operator:
        return "operator_user_sessions"
    if is_test_or_synthetic_user(user):
        return "test_or_synthetic_user_sessions"
    if session.post_deletion_retained_at or task.post_deletion_retained_at:
        return "deleted_retained_sessions"
    if task.voided_at is not None or task.state == TaskState.DELETED:
        return "voided_or_deleted_task_sessions"
    return None


def _dirty_reasons_for_session(
    db: Session,
    *,
    session: StopwatchSession,
    task: Task,
    corrected_task_ids: set[str],
) -> set[str]:
    reasons: set[str] = set()
    if session.auto_closed:
        reasons.add("auto_closed")
    if session.data_quality_flag:
        reasons.add("stale_recovered")
    if task.initiation_status == "retroactive":
        reasons.add("retroactive")
    if task.task_id in corrected_task_ids:
        reasons.add("corrected")
    if task.voided_at is not None:
        reasons.add("voided")
    if not session.start_time_utc or not session.end_time_utc:
        reasons.add("missing_timestamps")
    if (
        session.start_time_utc
        and session.end_time_utc
        and session.end_time_utc < session.start_time_utc
    ):
        reasons.add("impossible_duration")
    exposure_results = exposure_results_for_task(
        db,
        task=task,
        signal_targets=["planning_estimate", "duration_behavior"],
    )
    if any(result.state == "UNKNOWN" for result in exposure_results):
        reasons.add("unknown_exposure")
    if any(result.state in {"EXPOSED", "INTERVENTION"} for result in exposure_results):
        reasons.add("exposure_contaminated")
    return reasons


def measurement_integrity_snapshot(
    db: Session,
    *,
    user_ids: list[int],
    since: datetime,
) -> dict[str, Any]:
    """Read-only clean-trace denominator and dirty-reason snapshot."""
    provider_only = (
        db.query(func.count(Deadline.deadline_id))
        .filter(Deadline.user_id.in_(user_ids) if user_ids else False)
        .filter(Deadline.external_source.isnot(None), Deadline.voided_at.is_(None))
        .scalar()
        or 0
    )
    all_session_task_ids = {
        row[0]
        for row in (
            db.query(StopwatchSession.task_id)
            .join(Task, Task.task_id == StopwatchSession.task_id)
            .filter(Task.user_id.in_(user_ids) if user_ids else False)
            .all()
        )
    }
    non_session_tasks = (
        db.query(Task)
        .filter(Task.user_id.in_(user_ids) if user_ids else False)
        .filter(Task.voided_at.is_(None))
        .filter(Task.state != TaskState.DELETED)
        .filter(or_(Task.created_at >= since, Task.last_modified_at >= since))
        .all()
    )
    non_session_task_count = sum(
        1 for task in non_session_tasks if task.task_id not in all_session_task_ids
    )

    closed_sessions_all = (
        db.query(StopwatchSession, Task, User)
        .join(Task, Task.task_id == StopwatchSession.task_id)
        .join(User, User.user_id == StopwatchSession.user_id)
        .filter(StopwatchSession.end_time_utc.isnot(None))
        .filter(StopwatchSession.end_time_utc >= since)
        .all()
    )
    denominator_exclusions = Counter(
        {
            "operator_user_sessions": 0,
            "test_or_synthetic_user_sessions": 0,
            "voided_or_deleted_task_sessions": 0,
            "deleted_retained_sessions": 0,
            "provider_only_rows": int(provider_only),
            "non_session_tasks": int(non_session_task_count),
        }
    )
    eligible_sessions: list[tuple[StopwatchSession, Task]] = []
    for session, task, user in closed_sessions_all:
        exclusion = _denominator_exclusion_for(session, task, user)
        if exclusion:
            denominator_exclusions[exclusion] += 1
            continue
        eligible_sessions.append((session, task))

    corrected_task_ids = {
        row[0]
        for row in (
            db.query(TaskExecutionCorrection.task_id)
            .filter(TaskExecutionCorrection.created_at >= since)
            .all()
        )
    }
    dirty_reasons = Counter(
        {
            "auto_closed": 0,
            "stale_recovered": 0,
            "retroactive": 0,
            "corrected": 0,
            "voided": 0,
            "missing_timestamps": 0,
            "impossible_duration": 0,
            "unknown_exposure": 0,
            "provider_only": 0,
            "exposure_contaminated": 0,
        }
    )
    clean_closed = 0
    clean_session_ids: set[str] = set()
    dirty_session_reason_map: dict[str, list[str]] = {}
    closed_sessions_by_user: Counter[int] = Counter()
    clean_sessions_by_user: Counter[int] = Counter()
    for session, task in eligible_sessions:
        closed_sessions_by_user[int(session.user_id)] += 1
        reasons = _dirty_reasons_for_session(
            db,
            session=session,
            task=task,
            corrected_task_ids=corrected_task_ids,
        )
        if reasons:
            dirty_reasons.update(reasons)
            dirty_session_reason_map[session.session_id] = sorted(reasons)
        else:
            clean_closed += 1
            clean_session_ids.add(session.session_id)
            clean_sessions_by_user[int(session.user_id)] += 1
    dirty_reasons["provider_only"] = int(provider_only)

    closed_count = len(eligible_sessions)
    clean_trace_ratio = pct(clean_closed, closed_count) if closed_count else None
    dirty_trace_count = closed_count - clean_closed
    measurement_integrity = {
        **_metric_meta(basis="derived", confidence="high", readiness_impact="blocker"),
        "clean_trace_ratio": clean_trace_ratio,
        "dirty_trace_count": dirty_trace_count,
        "dirty_reasons": {k: int(v) for k, v in dirty_reasons.items()},
        "dirty_reason_distribution": {k: int(v) for k, v in dirty_reasons.items()},
        "clean_trace_ratio_basis": {
            "definition": "clean eligible explicit stopwatch sessions / all eligible explicit stopwatch sessions",
            "window_days": 14,
            "numerator": clean_closed,
            "denominator": closed_count,
            "excluded_from_denominator": {
                k: int(v) for k, v in denominator_exclusions.items()
            },
        },
        "dirty_session_reason_sample": dict(
            (short_hash(session_id), reasons)
            for session_id, reasons in list(dirty_session_reason_map.items())[:5]
        ),
        "analytic_blockers": [],
        "calibration_safe": bool(
            clean_trace_ratio is not None
            and clean_trace_ratio >= READINESS_GREEN_TRACE_RATIO
        ),
        "insights_safe": bool(
            clean_trace_ratio is not None
            and clean_trace_ratio >= READINESS_RED_TRACE_RATIO
        ),
    }
    if closed_count == 0:
        measurement_integrity["analytic_blockers"].append("no_closed_sessions_last_14d")
    if dirty_reasons["missing_timestamps"] or dirty_reasons["impossible_duration"]:
        measurement_integrity["analytic_blockers"].append("timestamp_or_duration_integrity")

    return {
        "measurement_integrity": measurement_integrity,
        "provider_only_rows": int(provider_only),
        "clean_trace_ratio": clean_trace_ratio,
        "closed_session_count": closed_count,
        "clean_session_count": clean_closed,
        "dirty_trace_count": dirty_trace_count,
        "closed_sessions_by_user": dict(closed_sessions_by_user),
        "clean_sessions_by_user": dict(clean_sessions_by_user),
    }
