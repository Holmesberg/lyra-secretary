"""Task query endpoint."""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import logging

from app.api.deps import get_db
from app.db.models import Task, TaskState
from app.utils.time_utils import to_utc, to_local
from app.utils.redis_client import RedisClient

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/tasks/query")
async def query_tasks(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    state: Optional[str] = Query("planned", description="Filter by state"),
    initiation_status: Optional[str] = Query(None, description="Filter by initiation_status (e.g. system_error, retroactive)"),
    db: Session = Depends(get_db)
):
    """
    Query tasks with optional filters.
    
    Returns tasks matching filters, ordered by start time.
    """
    try:
        query = db.query(Task)
        
        # Filter by state
        if state:
            try:
                task_state = TaskState(state)
                query = query.filter(Task.state == task_state)
            except ValueError:
                pass  # Invalid state, skip filter
        
        # Filter by date
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
                day_start = to_utc(target_date)  # midnight Cairo → UTC
                day_end = to_utc(target_date + timedelta(days=1))
                query = query.filter(
                    Task.planned_start_utc >= day_start,
                    Task.planned_start_utc < day_end
                )
            except ValueError:
                pass  # Invalid date format, skip filter
        
        # Filter by category
        if category:
            query = query.filter(Task.category == category)

        # Filter by initiation_status
        if initiation_status:
            query = query.filter(Task.initiation_status == initiation_status)

        # Order by start time
        tasks = query.order_by(Task.planned_start_utc).all()

        # Read immutable stored session_index_in_day (alembic 012).
        task_list = [
            {
                "task_id": t.task_id,
                "title": t.title,
                "start": to_local(t.planned_start_utc).isoformat() if t.planned_start_utc else None,
                "end": to_local(t.planned_end_utc).isoformat() if t.planned_end_utc else None,
                "state": t.state.value if hasattr(t.state, 'value') else str(t.state),
                "category": t.category,
                "initiation_status": t.initiation_status,
                "session_index_in_day": t.session_index_in_day if t.session_index_in_day is not None else 0,
                "pre_task_readiness": t.pre_task_readiness,
                "post_task_reflection": t.post_task_reflection,
                "planned_duration_minutes": t.planned_duration_minutes,
                "executed_duration_minutes": t.executed_duration_minutes,
                "duration_delta_minutes": t.duration_delta_minutes,
                "executed_start": to_local(t.executed_start_utc).isoformat() if t.executed_start_utc else None,
                "executed_end": to_local(t.executed_end_utc).isoformat() if t.executed_end_utc else None,
            }
            for t in tasks
        ]
        
        return {"tasks": task_list, "total": len(task_list)}
    
    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        return {"tasks": [], "total": 0}


@router.get("/tasks/last")
async def get_last_task(db: Session = Depends(get_db)):
    """
    Return the most recently created, rescheduled, or completed task (1-hour window).

    Used by the agent to resolve follow-up corrections like "actually make that
    next week" without requiring the user to repeat the task name or ID.
    Returns 404 if no task was operated in the last hour.
    """
    redis = RedisClient()
    last = redis.get_last_task()
    if not last:
        raise HTTPException(
            status_code=404,
            detail="No task operated in the last hour. Please specify the task.",
        )
    # Verify task still exists in DB (could have been deleted)
    task = db.query(Task).filter(Task.task_id == last["task_id"]).first()
    if not task:
        raise HTTPException(status_code=404, detail="Last task no longer exists.")
    return {
        "task_id": task.task_id,
        "title": task.title,
        "state": task.state.value if hasattr(task.state, "value") else str(task.state),
        "start": to_local(task.planned_start_utc).isoformat() if task.planned_start_utc else None,
        "end": to_local(task.planned_end_utc).isoformat() if task.planned_end_utc else None,
    }
