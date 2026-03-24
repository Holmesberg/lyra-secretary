"""Pre-task reminder job."""
from datetime import timedelta
import logging

from app.db.session import SessionLocal
from app.db.models import Task, TaskState
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)

def check_upcoming_tasks():
    """Check for tasks starting in 15 minutes."""
    db = SessionLocal()
    try:
        now = now_utc()
        reminder_time = now + timedelta(minutes=15)
        
        # Query tasks starting in next 15 minutes
        tasks = db.query(Task).filter(
            Task.state == TaskState.PLANNED,
            Task.planned_start_utc >= now,
            Task.planned_start_utc <= reminder_time
        ).all()
        
        for task in tasks:
            logger.info(f"Upcoming task reminder: {task.task_id} - {task.title}")
                
    finally:
        db.close()
