"""Timer overflow background job (per-user)."""
import logging
import httpx

from app.db.models import StopwatchSession, Task, User
from app.utils.time_utils import now_utc
from app.utils.redis_client import RedisClient
from app.services.telegram_notifier import send_telegram_message_sync
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def check_timer_overflow():
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User):
    now = now_utc()
    redis = RedisClient()

    sessions = db.query(StopwatchSession).filter(
        StopwatchSession.end_time_utc == None,
        StopwatchSession.auto_closed == False,
    ).all()

    for session in sessions:
        task = db.query(Task).filter(Task.task_id == session.task_id).first()
        if not task or not task.planned_duration_minutes:
            continue

        elapsed_minutes = int((now - session.start_time_utc).total_seconds() / 60)
        elapsed_minutes -= session.total_paused_minutes
        if session.paused_at_utc:
            current_pause = int((now - session.paused_at_utc).total_seconds() / 60)
            elapsed_minutes -= current_pause
        elapsed_minutes = max(0, elapsed_minutes)
        planned = task.planned_duration_minutes

        if elapsed_minutes > (planned + 5):
            notified_key = f"overflow_sent:{user.user_id}:{session.session_id}"
            if redis.client.exists(notified_key):
                continue

            message = (
                f"⏱️ '{task.title}' has been running for {elapsed_minutes} min "
                f"(planned: {planned} min). "
                "Reply with 'done' to stop, or a completion percentage (e.g. 75%)."
            )

            if user.is_operator:
                sent_direct = send_telegram_message_sync(message)
                if sent_direct:
                    logger.info(f"Overflow alert sent via direct Telegram (user {user.user_id})")

                try:
                    httpx.post(
                        "http://localhost:8000/v1/notifications/push",
                        json={"type": "timer_overflow", "message": message},
                        timeout=5.0,
                        headers={"X-User-Id": str(user.user_id)},
                    )
                except Exception as e:
                    logger.warning(f"Redis queue fallback failed for session {session.session_id}: {e}")

            redis.client.setex(notified_key, 86400, "1")
