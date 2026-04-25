"""Orphan task recovery — catches tasks stuck in EXECUTING or PAUSED with no session.

Complements stale_session_recovery.py which sweeps orphan SESSIONS.
This job catches the other failure class: a task whose state is EXECUTING
or PAUSED but has no open StopwatchSession row (e.g., Redis cleared by
laptop sleep, session closed by recovery but task state never transitioned).

Observed in production Apr 16-17: "quick building" stuck EXECUTING for
12+ hours with zero open sessions after overnight laptop sleep.

Apr 25 2026: extended to also catch state==PAUSED. Previously a paused task
held >12h would have its session auto-closed by stale_session_recovery, but
Task.state stayed PAUSED forever — a "ghost-paused" row with the Stop button
still visible but no active stopwatch behind it (u5 Altium, u6 "Compilers
Lecs"). The PAUSED-with-no-session class needed the same SKIPPED transition.
"""
import logging

from app.db.models import StopwatchSession, Task, TaskState, User
from app.utils.time_utils import now_utc
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)

# Tasks in either of these states with no open session are ghosts. Both
# recover to SKIPPED with initiation_status='orphaned_recovery'.
ABANDONED_STATES = (TaskState.EXECUTING, TaskState.PAUSED)


def run_orphan_task_recovery():
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User):
    abandoned = db.query(Task).filter(
        Task.state.in_(ABANDONED_STATES),
        Task.voided_at.is_(None),
    ).all()

    if not abandoned:
        return

    recovered = 0
    for task in abandoned:
        has_open_session = db.query(StopwatchSession).filter(
            StopwatchSession.task_id == task.task_id,
            StopwatchSession.end_time_utc.is_(None),
        ).first()

        if has_open_session:
            continue

        # Capture prior state for the log line BEFORE mutating.
        prior_state = task.state
        task.state = TaskState.SKIPPED
        task.initiation_status = "orphaned_recovery"
        task.last_modified_at = now_utc()
        recovered += 1
        prior_label = prior_state.name if hasattr(prior_state, "name") else str(prior_state)
        logger.warning(
            f"orphan_task_recovery: {task.task_id} ({task.title!r}) "
            f"{prior_label} with no open session → SKIPPED for user_id={user.user_id}"
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
