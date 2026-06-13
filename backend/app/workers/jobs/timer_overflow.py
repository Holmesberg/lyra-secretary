"""Timer overflow background job (per-user)."""
import logging

from app.db.models import NotificationLifecycleEvent, StopwatchSession, Task, User
from app.services.notification_queue import enqueue_user_notification
from app.services.operator_notifier import notify_operator
from app.services.output_surfaces import create_output_surface_decision
from app.utils.time_utils import now_utc
from app.utils.redis_client import RedisClient
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def check_timer_overflow():
    for_each_user(_run_for_one_user, job_name="timer_overflow")


def _run_for_one_user(db, user: User):
    now = now_utc()
    redis = RedisClient()

    sessions = db.query(StopwatchSession).filter(
        StopwatchSession.end_time_utc == None,
        StopwatchSession.auto_closed == False,
    ).all()

    for session in sessions:
        task = db.query(Task).filter(Task.task_id == session.task_id).first()
        if not task or not task.planned_duration_minutes or task.voided_at is not None:
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
            durable_sent = (
                db.query(NotificationLifecycleEvent)
                .filter(
                    NotificationLifecycleEvent.user_id == user.user_id,
                    NotificationLifecycleEvent.notification_type == "timer_overflow",
                    NotificationLifecycleEvent.session_id == session.session_id,
                )
                .first()
                is not None
            )
            if durable_sent or redis.client.exists(notified_key):
                continue

            message = (
                f"⏱️ '{task.title}' has been running for {elapsed_minutes} min "
                f"(planned: {planned} min). "
                "Reply with 'done' to stop, or a completion percentage (e.g. 75%)."
            )

            operator_message = message
            web_message = (
                f"'{task.title}' is past its planned window "
                f"({elapsed_minutes} min active; planned {planned} min). "
                "Open the task to stop or correct the timer."
            )

            delivered = False
            try:
                decision = create_output_surface_decision(
                    db,
                    surface_id="worker.timer_overflow",
                    user_id=user.user_id,
                    task_id=task.task_id,
                    decision_status="queued",
                    eligible_at=now,
                    content_template_id="timer_overflow",
                    trigger_source="worker.timer_overflow",
                    delivered_at=None,
                )
                enqueue_user_notification(
                    user.user_id,
                    {
                        "type": "timer_overflow",
                        "message": web_message,
                        "task_id": task.task_id,
                        "session_id": session.session_id,
                        "elapsed_minutes": elapsed_minutes,
                        "planned_minutes": planned,
                        "surface_id": "worker.timer_overflow",
                        "exposure_id": decision.exposure_id,
                    },
                    db=db,
                    surface_id="worker.timer_overflow",
                    exposure_id=decision.exposure_id,
                    dedupe_key=f"timer_overflow:{session.session_id}",
                    content_snapshot=web_message,
                )
                db.commit()
                delivered = True
            except Exception as e:
                db.rollback()
                logger.warning(f"Redis queue fallback failed for session {session.session_id}: {e}")

            # OpenClaw owns Telegram delivery. Operator-owned timer events may
            # also get an operator_alert envelope.
            if user.is_operator:
                sent_direct = notify_operator(
                    operator_message,
                    source="scheduler.timer-overflow",
                    severity="alert",
                    dedupe_key=f"timer-overflow:{user.user_id}:{session.session_id}",
                    cooldown_seconds=86400,
                )
                delivered = delivered or sent_direct
                if sent_direct:
                    logger.info(f"Overflow alert queued for OpenClaw operator channel (user {user.user_id})")

            if delivered:
                redis.client.setex(notified_key, 86400, "1")
