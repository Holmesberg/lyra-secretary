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
                # Notify OpenClaw
                # Calculate exactly how many minutes are left
                minutes_left = max(0, int((task.planned_start_utc - now).total_seconds() / 60))
                message = f"⏰ Reminder: '{task.title}' starts in {minutes_left} minutes!"
                
                # Using httpx synchronously as the job is a normal function
                response = httpx.post(
                    "http://openclaw-gateway:18789/api/notify",
                    json={"message": message},
                    timeout=5.0
                )
                response.raise_for_status()
                logger.info(f"Sent reminder for task {task.task_id} via OpenClaw")
                
            except Exception as e:
                logger.warning(f"Failed to send reminder via OpenClaw (endpoint might not exist yet): {e}")
                # TODO: OpenClaw notification endpoint may not exist yet
                logger.info(f"Logged Reminder: {task.title} starts soon.")
            
            # Always mark as notified to avoid spamming every minute
            redis.client.setex(notified_key, 7200, "1")
                
    except Exception as e:
        logger.error(f"Error in reminders job: {e}", exc_info=True)
    finally:
        db.close()
