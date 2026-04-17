"""Orphan task recovery — catches tasks stuck in EXECUTING with no session.

Complements stale_session_recovery.py which sweeps orphan SESSIONS.
This job catches the other failure class: a task whose state is EXECUTING
but has no open StopwatchSession row (e.g., Redis cleared by laptop sleep,
session closed by recovery but task state never transitioned).

Observed in production Apr 16-17: "quick building" stuck EXECUTING for
12+ hours with zero open sessions after overnight laptop sleep.
"""
import logging

from app.db.models import StopwatchSession, Task, TaskState, User
from app.utils.time_utils import now_utc
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def run_orphan_task_recovery():
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User):
    executing = db.query(Task).filter(
        Task.state == TaskState.EXECUTING,
        Task.voided_at.is_(None),
    ).all()

    if not executing:
        return

    recovered = 0
    for task in executing:
        has_open_session = db.query(StopwatchSession).filter(
            StopwatchSession.task_id == task.task_id,
            StopwatchSession.end_time_utc.is_(None),
        ).first()

        if has_open_session:
            continue

        task.state = TaskState.SKIPPED
        task.initiation_status = "orphaned_recovery"
        task.last_modified_at = now_utc()
        recovered += 1
        logger.warning(
            f"orphan_task_recovery: {task.task_id} ({task.title!r}) "
            f"EXECUTING with no open session → SKIPPED for user_id={user.user_id}"
        )

    if recovered:
        try:
            db.commit()
            logger.info(
                f"orphan_task_recovery: recovered {recovered} orphan tasks "
                f"for user_id={user.user_id}"
            )
        except Exception as e:
            logger.error(
                f"orphan_task_recovery: commit failed for user_id={user.user_id}: {e}",
                exc_info=True,
            )
            db.rollback()
