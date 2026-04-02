"""Analytics endpoints — discrepancy experiment measurement layer."""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Task, TaskState
from app.utils.time_utils import to_local

router = APIRouter()


def _time_of_day(local_dt) -> str:
    h = local_dt.hour
    if 5 <= h < 12:
        return "morning"
    elif 12 <= h < 17:
        return "afternoon"
    elif 17 <= h < 21:
        return "evening"
    else:
        return "night"


@router.get("/analytics/discrepancy")
async def get_discrepancy(db: Session = Depends(get_db)) -> dict:
    """
    Return all discrepancy measurement data.

    Includes every task that has been initiated, abandoned, or executed —
    plus computed fields for time-of-day, session index, and discrepancy score.
    """
    # Fetch tasks with any meaningful measurement signal, ordered by planned start
    tasks = (
        db.query(Task)
        .filter(
            (Task.state == TaskState.EXECUTED) |
            (Task.initiation_status.in_(["initiated", "abandoned"]))
        )
        .order_by(Task.planned_start_utc)
        .all()
    )

    # Build a local-date → sorted list of (planned_start_utc, task_id) for index calculation
    day_index: dict[date, list[str]] = {}
    for t in tasks:
        local_start = to_local(t.planned_start_utc)
        d = local_start.date()
        day_index.setdefault(d, []).append(t.task_id)

    sessions = []
    for t in tasks:
        local_start = to_local(t.planned_start_utc)
        d = local_start.date()

        # session_index_in_day = position of this task within that calendar day
        day_tasks = day_index.get(d, [])
        session_idx = day_tasks.index(t.task_id) if t.task_id in day_tasks else 0

        delta = t.duration_delta_minutes  # may be None for abandoned tasks

        sessions.append({
            "task_id": t.task_id,
            "title": t.title,
            "date": d.isoformat(),
            "planned_duration_minutes": t.planned_duration_minutes,
            "executed_duration_minutes": t.executed_duration_minutes,
            "delta_minutes": delta,
            "pre_task_readiness": t.pre_task_readiness,
            "post_task_reflection": t.post_task_reflection,
            "discrepancy_score": t.discrepancy_score,
            "initiation_status": t.initiation_status,
            "initiation_delay_minutes": t.initiation_delay_minutes,
            "category": t.category,
            "time_of_day": _time_of_day(local_start),
            "session_index_in_day": session_idx,
        })

    # Summary stats (only over sessions that have the relevant field populated)
    initiated = [s for s in sessions if s["initiation_status"] == "initiated"]
    abandoned = [s for s in sessions if s["initiation_status"] == "abandoned"]
    disc_values = [s["discrepancy_score"] for s in sessions if s["discrepancy_score"] is not None]
    delta_values = [s["delta_minutes"] for s in sessions if s["delta_minutes"] is not None]
    delay_values = [s["initiation_delay_minutes"] for s in sessions if s["initiation_delay_minutes"] is not None]

    def _avg(vals: list) -> Optional[float]:
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    summary = {
        "total_sessions": len(sessions),
        "initiated_count": len(initiated),
        "abandoned_count": len(abandoned),
        "avg_discrepancy": _avg(disc_values),
        "avg_delta_minutes": _avg(delta_values),
        "avg_initiation_delay_minutes": _avg(delay_values),
    }

    return {"sessions": sessions, "summary": summary}
