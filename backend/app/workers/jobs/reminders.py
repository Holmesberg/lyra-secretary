"""Pre-task reminder job (per-user)."""
from datetime import timedelta
import logging

from app.db.models import Task, TaskState, User
from app.services.notification_queue import enqueue_user_notification
from app.services.operator_notifier import notify_operator
from app.services.output_surfaces import emit_surface_render, emit_surface_suppression
from app.utils.time_utils import now_utc, to_local
from app.utils.redis_client import RedisClient
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def check_upcoming_tasks():
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User):
    """Per-user reminder check. Auto-scoped by the before_compile hook."""
    now = now_utc()
    reminder_time = now + timedelta(minutes=15)

    tasks = db.query(Task).filter(
        Task.state == TaskState.PLANNED,
        Task.voided_at.is_(None),
        Task.planned_start_utc >= now,
        Task.planned_start_utc <= reminder_time,
    ).all()

    redis = RedisClient()

    for task in tasks:
        notified_key = f"reminder_sent:{user.user_id}:{task.task_id}"
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

        delivered = False
        queued = False
        try:
            enqueue_user_notification(
                user.user_id,
                {"type": "reminder", "message": message},
            )
            queued = True
            emit_surface_render(
                db,
                surface_id="worker.reminder",
                user_id=user.user_id,
                task_id=task.task_id,
                content_snapshot=message,
                content_template_id="pre_task_reminder",
                initiative="system",
                trigger_source="worker.reminder",
                eligible_at=now,
                rendered_at=now,
            )
            db.commit()
            delivered = True
        except Exception as e:
            delivered = queued
            db.rollback()
            try:
                emit_surface_suppression(
                    db,
                    surface_id="worker.reminder",
                    user_id=user.user_id,
                    task_id=task.task_id,
                    suppression_reason="notification_enqueue_failed",
                    content_template_id="pre_task_reminder",
                    trigger_source="worker.reminder",
                    eligible_at=now,
                    suppressed_at=now,
                )
                db.commit()
            except Exception:
                db.rollback()
            logger.warning(f"Redis queue fallback failed for task {task.task_id}: {e}")

        # The Telegram bot is a shared operator channel, so only mirror
        # operator-owned reminders there. Other users receive the queued
        # notification through their authenticated poller.
        if user.is_operator:
            sent_direct = notify_operator(
                message,
                source="scheduler.reminders",
                severity="alert",
                dedupe_key=f"reminder:{user.user_id}:{task.task_id}",
                cooldown_seconds=7200,
            )
            delivered = delivered or sent_direct
            if sent_direct:
                logger.info(f"Reminder for task {task.task_id} sent via operator Telegram (user {user.user_id})")

        # Mark notified per-user only after at least one delivery path succeeds.
        if delivered:
            redis.client.setex(notified_key, 7200, "1")
