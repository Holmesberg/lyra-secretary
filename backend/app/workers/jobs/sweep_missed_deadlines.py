"""Sweep deadlines whose due_at_utc has passed without completion.

Phase H of Loop 11 (alembic 033, 2026-04-26). Companion to
reconcile_deadline_outcomes.py.

Every hour, find Deadline rows where:
  - state = 'active' (NOT 'planned' — see note below)
  - voided_at IS NULL
  - due_at_utc < now_utc()

Transition each to state='missed'. The transition is a *passive* state
change (deadline went unhandled past its time), distinct from 'skipped'
(active user abandonment) and 'voided' (soft-delete).

Why ONLY active, not planned: a deadline in 'planned' state means the
user created it but never bound a task. Transitioning planned → missed
on date passage would conflate "user never engaged" (planned) with
"user engaged but ran out of time" (active → missed). Keep the
distinction; treat planned + due_passed as still planned (the user can
still abandon explicitly via PUT to 'skipped').

Idempotent: a deadline already in 'missed' state will not be matched
on the next sweep (the filter is state='active'). No race-safety
concerns at single-instance APScheduler scale; if multi-instance ever
ships, add SELECT ... FOR UPDATE.
"""
import logging

from app.db.models import Deadline, User
from app.utils.time_utils import now_utc
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def run_sweep_missed_deadlines():
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User):
    now = now_utc()

    candidates = (
        db.query(Deadline)
        .filter(
            Deadline.user_id == user.user_id,
            Deadline.state == "active",
            Deadline.voided_at.is_(None),
            Deadline.due_at_utc < now,
        )
        .all()
    )

    if not candidates:
        return

    swept_count = 0
    for deadline in candidates:
        deadline.state = "missed"
        if deadline.missed_at is None:
            deadline.missed_at = now
        swept_count += 1

    try:
        db.commit()
    except Exception as e:
        logger.error(
            f"sweep_missed_deadlines: commit failed for "
            f"user_id={user.user_id}: {e}",
            exc_info=True,
        )
        db.rollback()
        return

    logger.info(
        f"sweep_missed_deadlines: user_id={user.user_id} "
        f"swept={swept_count}"
    )
    # Operator-only fanout (2026-04-30): deadlines transitioning
    # active → missed is a load-bearing event the operator wants
    # to see in the unified Telegram inbox.
    if swept_count and user.is_operator:
        from app.services.operator_notifier import notify_operator
        notify_operator(
            f"*{swept_count}* deadline(s) just transitioned to missed — past due_at without completion.",
            source="scheduler.missed-deadlines",
            severity="warn",
        )
