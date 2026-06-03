"""Pre-task reminder job (per-user)."""
from datetime import timedelta
import logging
import time

from sqlalchemy.exc import OperationalError

from app.db.scoping import set_current_user_id
from app.db.session import SessionLocal, engine
from app.db.models import Task, TaskState, User
from app.services.notification_queue import enqueue_user_notification
from app.services.operator_notifier import notify_operator
from app.services.output_surfaces import emit_surface_render, emit_surface_suppression
from app.utils.time_utils import now_utc, to_local
from app.utils.redis_client import RedisClient
from app.workers.jobs._per_user import for_each_user
from app.workers.jobs._scheduler_contract import (
    JobResult,
    NO_MUTATION_ATTEMPTED,
    degrade_job,
    run_scheduler_job,
)

logger = logging.getLogger(__name__)

REMINDER_BOOTSTRAP_MAX_ATTEMPTS = 2
REMINDER_BOOTSTRAP_RETRY_DELAY_SECONDS = 1.0


def check_upcoming_tasks() -> JobResult:
    return run_scheduler_job(
        "reminders",
        "scheduler.reminders",
        _check_upcoming_tasks,
    )


def _check_upcoming_tasks() -> JobResult:
    return for_each_user(
        _run_for_one_user,
        user_ids=_load_candidate_user_ids(),
        job_name="reminders",
    )


def _dispose_engine_pool() -> None:
    try:
        engine.dispose()
    except Exception:  # noqa: BLE001 - diagnostics only; keep worker alive
        logger.warning(
            "reminder bootstrap could not dispose DB engine pool",
            exc_info=True,
        )


def _load_candidate_user_ids() -> list[int]:
    """Load only users who have reminder-eligible tasks this tick.

    Reminder delivery should degrade during DB outages. A failed candidate
    bootstrap means no per-user mutation has started, so the job can skip
    this tick cleanly and let APScheduler try again on the next interval.
    """
    set_current_user_id(None)
    now = now_utc()
    reminder_time = now + timedelta(minutes=15)

    for attempt in range(1, REMINDER_BOOTSTRAP_MAX_ATTEMPTS + 1):
        db = SessionLocal()
        failed_operationally = False
        try:
            rows = (
                db.query(Task.user_id)
                .filter(
                    Task.state == TaskState.PLANNED,
                    Task.voided_at.is_(None),
                    Task.planned_start_utc >= now,
                    Task.planned_start_utc <= reminder_time,
                )
                .distinct()
                .all()
            )
            return [row[0] for row in rows if row[0] is not None]
        except OperationalError:
            failed_operationally = True
            try:
                db.rollback()
            except Exception:  # noqa: BLE001 - session may already be broken
                logger.debug(
                    "reminder bootstrap rollback failed after OperationalError",
                    exc_info=True,
                )
            logger.warning(
                "reminder candidate bootstrap failed with OperationalError "
                "on attempt %s/%s",
                attempt,
                REMINDER_BOOTSTRAP_MAX_ATTEMPTS,
                exc_info=True,
            )
        finally:
            db.close()

        if failed_operationally:
            _dispose_engine_pool()
            if attempt < REMINDER_BOOTSTRAP_MAX_ATTEMPTS:
                time.sleep(REMINDER_BOOTSTRAP_RETRY_DELAY_SECONDS)

    degrade_job(
        job_id="reminders",
        subsystem="scheduler.reminders / candidate bootstrap",
        message=(
            "Reminder candidate bootstrap failed with `OperationalError`. "
            "Job skipped this tick; check backend logs."
        ),
        affected="scheduler.reminders / candidate bootstrap",
        scope=(
            "unknown candidate-user count; bootstrap could not load "
            "planned tasks in the reminder window"
        ),
        retry=(
            f"Retried {REMINDER_BOOTSTRAP_MAX_ATTEMPTS} total attempt(s), "
            "disposed the DB engine pool after each failure, then waits "
            "for the next scheduler tick. Reminder notifications may be delayed "
            "until DB access recovers."
        ),
        user_action=(
            "No student action. Operator should triage if this repeats."
        ),
        data_integrity=NO_MUTATION_ATTEMPTED,
        source="scheduler.reminders",
        severity="error",
        dedupe_key="reminder-candidates:OperationalError",
        cooldown_seconds=30 * 60,
        notifier=notify_operator,
    )


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

        # OpenClaw owns Telegram delivery. Operator-owned reminders may also
        # get an operator_alert envelope; other users receive only their
        # authenticated queue payload.
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
                    logger.info(f"Reminder for task {task.task_id} queued for OpenClaw operator channel (user {user.user_id})")

        # Mark notified per-user only after at least one delivery path succeeds.
        if delivered:
            redis.client.setex(notified_key, 7200, "1")
