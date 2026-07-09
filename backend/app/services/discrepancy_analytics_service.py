"""Read-only discrepancy analytics snapshot service."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.db.models import StopwatchSession, Task, TaskState
from app.services.analytics_insight_helpers import (
    average as _avg,
    time_of_day as _time_of_day,
)
from app.utils.time_utils import to_local


def discrepancy_snapshot(db: Session) -> dict:
    """Return discrepancy measurement data in research and product layers."""
    tasks = (
        db.query(Task)
        .filter(
            (Task.state == TaskState.EXECUTED)
            | (Task.initiation_status.in_(["initiated", "abandoned"]))
        )
        .filter(Task.initiation_status != "system_error", Task.voided_at.is_(None))
        .order_by(Task.planned_start_utc)
        .all()
    )

    research_sessions = []
    product_sessions = []

    for task in tasks:
        local_start = to_local(task.planned_start_utc)
        session_idx = (
            task.session_index_in_day
            if task.session_index_in_day is not None
            else 0
        )
        common = {
            "task_id": task.task_id,
            "title": task.title,
            "date": local_start.date().isoformat(),
            "category": task.category,
            "time_of_day": _time_of_day(local_start),
            "session_index_in_day": session_idx,
        }

        sessions_for_task = (
            db.query(StopwatchSession)
            .filter(StopwatchSession.task_id == task.task_id)
            .all()
        )
        total_paused = sum(session.total_paused_minutes for session in sessions_for_task)
        pause_reasons = [
            session.pause_reason for session in sessions_for_task if session.pause_reason
        ]
        pause_initiators = [
            session.pause_initiator
            for session in sessions_for_task
            if session.pause_initiator
        ]
        first_pause_minute = None
        for session in sessions_for_task:
            if session.paused_at_utc and session.start_time_utc:
                mins = int(
                    (session.paused_at_utc - session.start_time_utc).total_seconds()
                    / 60
                )
                if first_pause_minute is None or mins < first_pause_minute:
                    first_pause_minute = mins

        research_sessions.append({
            **common,
            "planned_duration_minutes": task.planned_duration_minutes,
            "executed_duration_minutes": task.executed_duration_minutes,
            "delta_minutes": task.duration_delta_minutes,
            "initiation_status": task.initiation_status,
            "initiation_delay_minutes": task.initiation_delay_minutes,
            "pause_count": task.pause_count,
            "total_paused_minutes": total_paused,
            "pause_pattern": {
                "pause_count": task.pause_count or 0,
                "total_paused_minutes": total_paused,
                "first_pause_at_minute": first_pause_minute,
                "pause_reasons": pause_reasons,
                "pause_initiators": pause_initiators,
            },
            "parent_task_id": task.parent_task_id,
            "interruption_type": task.interruption_type,
            "replaces_task_id": task.replaces_task_id,
        })

        product_sessions.append({
            **common,
            "pre_task_readiness": task.pre_task_readiness,
            "post_task_reflection": task.post_task_reflection,
            "discrepancy_score": task.discrepancy_score,
            "signed_discrepancy": task.signed_discrepancy,
        })

    voided_count = (
        db.query(Task)
        .filter(
            Task.voided_at.is_not(None),
            Task.initiation_status == "system_error",
        )
        .count()
    )
    total = len(research_sessions)
    initiated = [
        session
        for session in research_sessions
        if session["initiation_status"] == "initiated"
    ]
    abandoned = [
        session
        for session in research_sessions
        if session["initiation_status"] == "abandoned"
    ]
    retroactive = [
        session
        for session in research_sessions
        if session["initiation_status"] == "retroactive"
    ]
    delta_vals = [
        session["delta_minutes"]
        for session in research_sessions
        if session["delta_minutes"] is not None
    ]
    delay_vals = [
        session["initiation_delay_minutes"]
        for session in research_sessions
        if session["initiation_delay_minutes"] is not None
    ]
    interrupted = [session for session in research_sessions if session.get("parent_task_id")]
    substituted = [
        session for session in research_sessions if session.get("replaces_task_id")
    ]

    reason_counts: dict[str, int] = defaultdict(int)
    for task in tasks:
        if task.initiation_status == "retroactive" and task.unplanned_reason:
            reason_counts[task.unplanned_reason] += 1

    consistency_buckets: dict[str, list[int]] = defaultdict(list)
    for task in tasks:
        if task.discrepancy_score is not None and task.category:
            tod = _time_of_day(to_local(task.planned_start_utc))
            consistency_buckets[f"{task.category}_{tod}"].append(
                task.discrepancy_score
            )

    self_consistency = []
    for key, scores in consistency_buckets.items():
        if len(scores) < 2:
            continue
        mean = sum(scores) / len(scores)
        variance = round(sum((score - mean) ** 2 for score in scores) / len(scores), 2)
        category, tod = key.rsplit("_", 1)
        self_consistency.append({
            "category": category,
            "time_of_day": tod,
            "variance": variance,
            "sessions": len(scores),
        })

    research_summary = {
        "total_sessions": total,
        "initiated_count": len(initiated),
        "abandoned_count": len(abandoned),
        "abandoned_rate": round(len(abandoned) / total, 3) if total else 0.0,
        "retroactive_count": len(retroactive),
        "unplanned_execution_rate": round(len(retroactive) / total, 3)
        if total
        else 0.0,
        "unplanned_reason_breakdown": dict(reason_counts),
        "avg_delta_minutes": _avg(delta_vals),
        "avg_initiation_delay_minutes": _avg(delay_vals),
        "interruption_rate": round(len(interrupted) / total, 3) if total else 0.0,
        "substitution_rate": round(len(substituted) / total, 3) if total else 0.0,
        "self_consistency_scores": self_consistency,
        "voided_count": voided_count,
    }

    disc_vals = [
        session["discrepancy_score"]
        for session in product_sessions
        if session["discrepancy_score"] is not None
    ]
    signed_vals = [
        session["signed_discrepancy"]
        for session in product_sessions
        if session["signed_discrepancy"] is not None
    ]
    depleting = [value for value in signed_vals if value < 0]
    product_summary = {
        "total_sessions_with_scores": len(disc_vals),
        "avg_discrepancy": _avg(disc_vals),
        "avg_signed_discrepancy": _avg(signed_vals),
        "depletion_rate": round(len(depleting) / len(signed_vals), 3)
        if signed_vals
        else 0.0,
    }

    return {
        "research_layer": {
            "sessions": research_sessions,
            "summary": research_summary,
        },
        "product_layer": {
            "sessions": product_sessions,
            "summary": product_summary,
        },
    }
