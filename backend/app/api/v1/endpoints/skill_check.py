"""Skill health check — cheap session-start connectivity and state probe."""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Task, TaskState
from app.utils.redis_client import RedisClient
from app.utils.time_utils import now_utc, to_local

router = APIRouter()


@router.get("/skill/ping")
async def skill_ping(db: Session = Depends(get_db)) -> dict:
    """
    Lightweight connectivity and state check for session start.

    Haiku calls this on /new or /reset to:
    1. Confirm backend is reachable
    2. Know if a stopwatch is already running
    3. Know how many tasks are planned for today
    """
    redis = RedisClient()
    active = redis.get_active_stopwatch("user_primary")

    now = now_utc()
    today_local = to_local(now).date()

    # Count PLANNED tasks whose planned_start falls on today (Cairo local date)
    planned_tasks = db.query(Task).filter(Task.state == TaskState.PLANNED).all()
    pending_today = sum(
        1 for t in planned_tasks
        if to_local(t.planned_start_utc).date() == today_local
    )

    return {
        "status": "ok",
        "timestamp": now.isoformat(),
        "active_stopwatch": active is not None,
        "pending_tasks_today": pending_today,
    }
