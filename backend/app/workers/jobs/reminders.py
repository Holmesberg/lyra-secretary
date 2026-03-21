"""Pre-task reminder job."""
from datetime import timedelta
import logging

from app.db.session import SessionLocal
from app.db.models import Task, TaskState
from app.services.telegram_notifier import TelegramNotifier
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
        
        notifier = TelegramNotifier()
        for task in tasks:
            try:
                notifier.send_reminder(task)
                logger.info(f"Sent reminder for task {task.task_id}")
            except Exception as e:
                logger.error(f"Failed to send reminder for task {task.task_id}: {e}")
                
    finally:
        db.close()
