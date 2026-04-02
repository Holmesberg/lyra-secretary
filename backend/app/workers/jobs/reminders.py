"""Pre-task reminder job."""
from datetime import timedelta
import logging
import httpx

from app.db.session import SessionLocal
from app.db.models import Task, TaskState
from app.utils.time_utils import now_utc, to_local
from app.utils.redis_client import RedisClient
from app.services.telegram_notifier import send_telegram_message_sync

logger = logging.getLogger(__name__)


def check_upcoming_tasks():
    """Check for tasks starting in 15 minutes."""
    db = SessionLocal()
    try:
        now = now_utc()
        reminder_time = now + timedelta(minutes=15)

        tasks = db.query(Task).filter(
            Task.state == TaskState.PLANNED,
            Task.planned_start_utc >= now,
            Task.planned_start_utc <= reminder_time
        ).all()

        redis = RedisClient()

        for task in tasks:
            notified_key = f"reminder_sent:{task.task_id}"
            if redis.client.exists(notified_key):
                continue

            minutes_left = max(0, int((task.planned_start_utc - now).total_seconds() / 60))
            start_local = to_local(task.planned_start_utc).strftime("%H:%M")
            planned_duration = task.planned_duration_minutes or 0

            message = (
                f"⏰ *Reminder: {task.title}*\n"
                f"Starting in {minutes_left} minutes ({start_local} Cairo)\n"
                f"Planned duration: {planned_duration} min"
            )

            # 1. Try direct Telegram delivery
            sent_direct = send_telegram_message_sync(message)
            if sent_direct:
                logger.info(f"Reminder for task {task.task_id} sent via direct Telegram")

            # 2. Also push to Redis queue as fallback for OpenClaw
            try:
                httpx.post(
                    "http://localhost:8000/v1/notifications/push",
                    json={"type": "reminder", "message": message},
                    timeout=5.0
                )
                logger.info(f"Reminder for task {task.task_id} also queued in Redis (fallback)")
            except Exception as e:
                logger.warning(f"Redis queue fallback failed for task {task.task_id}: {e}")

            # Mark as notified regardless of delivery path to avoid repeat spam
            redis.client.setex(notified_key, 7200, "1")

    except Exception as e:
        logger.error(f"Error in reminders job: {e}", exc_info=True)
    finally:
        db.close()
