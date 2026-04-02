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


def _avg(vals: list) -> float:
    return round(sum(vals) / len(vals), 2) if vals else 0.0


@router.get("/analytics/discrepancy")
async def get_discrepancy(db: Session = Depends(get_db)) -> dict:
    """
    Return discrepancy measurement data in two separate layers:

    - research_layer: time/behavioral signals (delta, initiation, abandonment)
    - product_layer: cognitive signals (readiness shift, depletion rate)
    """
    tasks = (
        db.query(Task)
        .filter(
            (Task.state == TaskState.EXECUTED) |
            (Task.initiation_status.in_(["initiated", "abandoned"]))
        )
        .order_by(Task.planned_start_utc)
        .all()
    )

    # Build local-date → task_id list for session index calculation
    day_index: dict[date, list[str]] = {}
    for t in tasks:
        local_start = to_local(t.planned_start_utc)
        d = local_start.date()
        day_index.setdefault(d, []).append(t.task_id)

    research_sessions = []
    product_sessions = []

    for t in tasks:
        local_start = to_local(t.planned_start_utc)
        d = local_start.date()
        day_tasks = day_index.get(d, [])
        session_idx = day_tasks.index(t.task_id) if t.task_id in day_tasks else 0

        # Shared identity fields
        common = {
            "task_id": t.task_id,
            "title": t.title,
            "date": d.isoformat(),
            "category": t.category,
            "time_of_day": _time_of_day(local_start),
            "session_index_in_day": session_idx,
        }

        research_sessions.append({
            **common,
            "planned_duration_minutes": t.planned_duration_minutes,
            "executed_duration_minutes": t.executed_duration_minutes,
            "delta_minutes": t.duration_delta_minutes,
            "initiation_status": t.initiation_status,
            "initiation_delay_minutes": t.initiation_delay_minutes,
        })

        product_sessions.append({
            **common,
            "pre_task_readiness": t.pre_task_readiness,
            "post_task_reflection": t.post_task_reflection,
            "discrepancy_score": t.discrepancy_score,      # abs(pre - post): magnitude
            "signed_discrepancy": t.signed_discrepancy,    # post - pre: direction
        })

    # --- Research layer summary ---
    total = len(research_sessions)
    initiated = [s for s in research_sessions if s["initiation_status"] == "initiated"]
    abandoned = [s for s in research_sessions if s["initiation_status"] == "abandoned"]
    delta_vals = [s["delta_minutes"] for s in research_sessions if s["delta_minutes"] is not None]
    delay_vals = [s["initiation_delay_minutes"] for s in research_sessions if s["initiation_delay_minutes"] is not None]

    research_summary = {
        "total_sessions": total,
        "initiated_count": len(initiated),
        "abandoned_count": len(abandoned),
        "abandoned_rate": round(len(abandoned) / total, 3) if total else 0.0,
        "avg_delta_minutes": _avg(delta_vals),
        "avg_initiation_delay_minutes": _avg(delay_vals),
    }

    # --- Product layer summary ---
    disc_vals = [s["discrepancy_score"] for s in product_sessions if s["discrepancy_score"] is not None]
    signed_vals = [s["signed_discrepancy"] for s in product_sessions if s["signed_discrepancy"] is not None]
    depleting = [v for v in signed_vals if v < 0]

    product_summary = {
        "total_sessions_with_scores": len(disc_vals),
        "avg_discrepancy": _avg(disc_vals),
        "avg_signed_discrepancy": _avg(signed_vals),
        "depletion_rate": round(len(depleting) / len(signed_vals), 3) if signed_vals else 0.0,
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
