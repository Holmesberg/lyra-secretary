"""Overdue task detection job (per-user)."""
import logging

from app.db.models import Task, TaskState, User
from app.services.task_manager import TaskManager
from app.utils.time_utils import now_utc
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def detect_and_skip_overdue_tasks():
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User):
    """
    Per-user: transition PLANNED tasks to SKIPPED if their window passed
    without a timer start. State machine path: PLANNED → SKIPPED.
    """
    now = now_utc()
    tasks = db.query(Task).filter(
        Task.state == TaskState.PLANNED,
        Task.voided_at.is_(None),
        Task.planned_end_utc < now,
        Task.initiation_status == "not_started",
    ).all()

    if not tasks:
        return

    manager = TaskManager(db)
    count = 0
    for task in tasks:
        try:
            task = manager.skip_task(
                task.task_id,
                reason="auto-abandoned: task window passed without timer start",
            )
            task.initiation_status = "abandoned"
            db.commit()
            count += 1
        except Exception as e:
            logger.error(f"Failed to abandon task {task.task_id} (user {user.user_id}): {e}", exc_info=True)
            db.rollback()

    if count:
        logger.info(f"Transitioned {count} task(s) to SKIPPED for user {user.user_id}")
        # Operator-only fanout (2026-04-30): silently auto-skipped tasks
        # are exactly the kind of state change the operator wants to see
        # without having to refresh /today.
        if user.is_operator:
            from app.services.operator_notifier import notify_operator
            notify_operator(
                f"Auto-skipped *{count}* overdue task(s) — they passed their planned start without a timer.",
                source="scheduler.overdue",
                severity="warn",
            )
