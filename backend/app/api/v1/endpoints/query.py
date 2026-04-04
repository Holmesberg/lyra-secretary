"""Task query endpoint."""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import logging

from app.api.deps import get_db
from app.db.models import Task, TaskState
from app.utils.time_utils import to_utc, to_local

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/tasks/query")
async def query_tasks(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    state: Optional[str] = Query("planned", description="Filter by state"),
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
        
        # Order by start time
        tasks = query.order_by(Task.planned_start_utc).all()
        
        task_list = [
            {
                "task_id": t.task_id,
                "title": t.title,
                "start": to_local(t.planned_start_utc).isoformat() if t.planned_start_utc else None,
                "end": to_local(t.planned_end_utc).isoformat() if t.planned_end_utc else None,
                "state": t.state.value if hasattr(t.state, 'value') else str(t.state),
                "category": t.category,
            }
            for t in tasks
        ]
        
        return {"tasks": task_list, "total": len(task_list)}
    
    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        return {"tasks": [], "total": 0}
