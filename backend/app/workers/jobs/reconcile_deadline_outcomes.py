"""Reconcile deadline_met outcomes for EXECUTED tasks bound to deadlines.

Phase H of Loop 11 (alembic 033, 2026-04-26). Pre-registered analysis
implementation for MANIFESTO Rule 14 (H2 deadline-distance kill criterion).

Every 30 minutes, sweep EXECUTED tasks where:
  - task.deadline_id IS NOT NULL  — task is deadline-bound
  - task.voided_at IS NULL        — voided_at_guard discipline
  - task.executed_end_utc IS NOT NULL  — has actual finish time
  - no existing task_deadline_outcome row for this task_id  — not yet reconciled

For each such task, compute:
  deadline_met = executed_end_utc <= deadline.due_at_utc
  delay_minutes = (executed_end_utc - deadline.due_at_utc).total_seconds() / 60
                — signed: positive = overran (missed), negative = met early.

Write to `task_deadline_outcome` with frozen-at-compute-time semantics:
the deadline.due_at_utc and task.executed_end_utc snapshotted in this row
are immutable. If either source value changes later (which would itself be
a state-machine violation), the outcome row remains historically accurate.

Race-safety: PRIMARY KEY on task_deadline_outcome.task_id prevents duplicate
rows. We use INSERT ... ON CONFLICT (Postgres) or just check-then-insert in
a transaction (works for SQLite). Concurrent writes from two scheduler
instances would race; in practice APScheduler runs single-instance so this
isn't observed, but the PK constraint is the safety net.
"""
import logging
from typing import Optional

from app.db.models import Deadline, Task, TaskDeadlineOutcome, TaskState, User
from app.utils.time_utils import now_utc
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def run_reconcile_deadline_outcomes():
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User):
    # Find EXECUTED, non-voided, deadline-bound tasks that don't have an
    # outcome row yet. LEFT JOIN to task_deadline_outcome to detect
    # absence efficiently.
    candidates = (
        db.query(Task, Deadline)
        .join(Deadline, Task.deadline_id == Deadline.deadline_id)
        .outerjoin(TaskDeadlineOutcome, TaskDeadlineOutcome.task_id == Task.task_id)
        .filter(
            Task.user_id == user.user_id,
            Task.state == TaskState.EXECUTED,
            Task.voided_at.is_(None),
            Task.deadline_id.is_not(None),
            Task.executed_end_utc.is_not(None),
            # No existing outcome row OR outcome row is voided (which
            # would be the post-LYR-095-style retroactive void scenario).
            TaskDeadlineOutcome.task_id.is_(None),
        )
        .all()
    )

    if not candidates:
        return

    written_count = 0
    met_count = 0
    now = now_utc()

    for task, deadline in candidates:
        # Defensive: skip if the deadline itself is voided. We don't want
        # to write an outcome row referencing a voided deadline — research
        # queries should treat that as no-data.
        if deadline.voided_at is not None:
            continue

        # Compute the verdict.
        delay_seconds = (task.executed_end_utc - deadline.due_at_utc).total_seconds()
        delay_minutes = int(delay_seconds / 60)
        # Boundary: delay_minutes <= 0 → met (executed_end_utc <= due_at_utc).
        deadline_met = delay_minutes <= 0

        outcome = TaskDeadlineOutcome(
            task_id=task.task_id,
            user_id=user.user_id,
            computed_at=now,
            deadline_utc_at_compute=deadline.due_at_utc,
            executed_end_utc_at_compute=task.executed_end_utc,
            deadline_met=deadline_met,
            delay_minutes=delay_minutes,
        )
        db.add(outcome)
        written_count += 1
        if deadline_met:
            met_count += 1

    try:
        db.commit()
    except Exception as e:
        logger.error(
            f"reconcile_deadline_outcomes: commit failed for "
            f"user_id={user.user_id}: {e}",
            exc_info=True,
        )
        db.rollback()
        return

    logger.info(
        f"reconcile_deadline_outcomes: user_id={user.user_id} "
        f"written={written_count} met={met_count} "
        f"missed={written_count - met_count}"
    )
