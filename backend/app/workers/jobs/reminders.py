"""Pre-task reminder job."""
from datetime import timedelta
import logging
import httpx

from app.db.session import SessionLocal
from app.db.models import Task, TaskState
from app.utils.time_utils import now_utc
from app.utils.redis_client import RedisClient

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
        
        redis = RedisClient()
        
        for task in tasks:
            # Ensure we only send one reminder
            notified_key = f"reminder_sent:{task.task_id}"
            if redis.client.exists(notified_key):
                continue
                
            try:
                import httpx, json
                # Notify OpenClaw via backend queue
                minutes_left = max(0, int((task.planned_start_utc - now).total_seconds() / 60))
                httpx.post(
                    "http://localhost:8000/v1/notifications/push", 
                    json={"type": "reminder", "message": f"⏰ {task.title} starts in {minutes_left} minutes"},
                    timeout=5.0
                )
                logger.info(f"Queued reminder for task {task.task_id} via backend queue")
                
            except Exception as e:
                logger.error(f"Failed to queue reminder notification: {e}")
            
            # Always mark as notified to avoid spamming every minute
            redis.client.setex(notified_key, 7200, "1")
                
    except Exception as e:
        logger.error(f"Error in reminders job: {e}", exc_info=True)
    finally:
        db.close()
