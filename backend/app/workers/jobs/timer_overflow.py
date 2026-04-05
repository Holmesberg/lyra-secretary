"""Timer overflow background job."""
import logging
import httpx

from app.db.session import SessionLocal
from app.db.models import StopwatchSession, Task
from app.utils.time_utils import now_utc
from app.utils.redis_client import RedisClient
from app.services.telegram_notifier import send_telegram_message_sync

logger = logging.getLogger(__name__)


def check_timer_overflow():
    """Detect stopwatch sessions running longer than planned + buffer."""
    db = SessionLocal()
    try:
        now = now_utc()
        redis = RedisClient()

        sessions = db.query(StopwatchSession).filter(
            StopwatchSession.end_time_utc == None,
            StopwatchSession.auto_closed == False
        ).all()

        for session in sessions:
            task = db.query(Task).filter(Task.task_id == session.task_id).first()
            if not task or not task.planned_duration_minutes:
                continue

            elapsed_minutes = int((now - session.start_time_utc).total_seconds() / 60)
            # Subtract accumulated paused time
            elapsed_minutes -= session.total_paused_minutes
            # If currently paused, subtract ongoing pause too
            if session.paused_at_utc:
                current_pause = int((now - session.paused_at_utc).total_seconds() / 60)
                elapsed_minutes -= current_pause
            elapsed_minutes = max(0, elapsed_minutes)
            planned = task.planned_duration_minutes

            if elapsed_minutes > (planned + 5):
                notified_key = f"overflow_sent:{session.session_id}"
                if redis.client.exists(notified_key):
                    continue

                message = (
                    f"⏱️ '{task.title}' has been running for {elapsed_minutes} min "
                    f"(planned: {planned} min). "
                    "Reply with 'done' to stop, or a completion percentage (e.g. 75%)."
                )

                # 1. Try direct Telegram delivery
                sent_direct = send_telegram_message_sync(message)
                if sent_direct:
                    logger.info(f"Overflow alert for session {session.session_id} sent via direct Telegram")

                # 2. Also push to Redis queue as fallback for OpenClaw
                try:
                    httpx.post(
                        "http://localhost:8000/v1/notifications/push",
                        json={"type": "timer_overflow", "message": message},
                        timeout=5.0
                    )
                    logger.info(f"Overflow alert for session {session.session_id} also queued in Redis (fallback)")
                except Exception as e:
                    logger.warning(f"Redis queue fallback failed for session {session.session_id}: {e}")

                # Mark notified regardless of delivery path
                redis.client.setex(notified_key, 86400, "1")  # 24hr TTL

    except Exception as e:
        logger.error(f"Error in timer_overflow job: {e}", exc_info=True)
    finally:
        db.close()
