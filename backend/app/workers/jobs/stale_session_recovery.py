"""Stale session recovery background job.

Sweeps unclosed StopwatchSession rows whose start_time is more than
12 hours old and auto-closes them. Prevents the class of incident where
a browser crash mid-pause, container restart before resume, or voided
task leaves an orphan session that the banner surfaces forever (the 65h
CO-block ghost, Apr 11 — LYR-103).

Conservative by design:
  * 12h threshold — catches forgotten paused sessions before compounding
    while producing near-zero false positives for legitimate long tasks.
    Lowered from 24h after Apr 12 dogfood evidence (16h 41m paused
    session went undetected by auto-cleanup).
  * **Skip currently-active session.** Apr 25 2026: the multi-tasking
    swap fix introduced a path where a paused-with-open-session task gets
    resumed (Redis active reset to it) even though its session.start_time
    is well past the 12h cutoff. The recovery must not close a session the
    user just deliberately resumed. Long deep-work sessions are also
    legitimately old; same skip logic protects them.
  * end_time_utc = start_time_utc + max(planned_duration, 1) min so the
    row has a defensible duration rather than extending to "now".
  * **Defense-in-depth task-state transition.** Apr 25 2026: when closing
    an orphan session, also transition Task.state EXECUTING|PAUSED →
    SKIPPED with initiation_status='orphaned_recovery' if the task has no
    OTHER open session. Previously this transition was deferred to
    orphan_task_recovery (a separate 15-min job), creating a window where
    the task showed "Stop" but the stop endpoint returned "no active
    stopwatch." Single-pass recovery closes the window.
  * Per-user iteration via for_each_user so a bad row on one tenant
    doesn't poison the sweep for everyone else.
"""
import logging
from datetime import timedelta

from app.db.models import PauseEvent, StopwatchSession, Task, TaskState, User
from app.utils.redis_client import RedisClient
from app.utils.time_utils import now_utc
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)

STALE_THRESHOLD_HOURS = 12


def run_stale_session_recovery():
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User):
    cutoff = now_utc() - timedelta(hours=STALE_THRESHOLD_HOURS)
    redis = RedisClient()

    stale = db.query(StopwatchSession).filter(
        StopwatchSession.end_time_utc.is_(None),
        StopwatchSession.start_time_utc < cutoff,
    ).all()

    if not stale:
        return

    # Read Redis active ONCE per user; the recovery loop uses it to skip
    # the currently-active session (Apr 25 multi-tasking swap fix).
    # Defensive: if Redis is unreachable (CI without redis service, network
    # blip), the skip-active optimization is lost but recovery still runs
    # correctly. The previous iteration-level try/except in the for-loop
    # absorbed Redis failures the same way; this preserves that contract.
    try:
        active = redis.get_active_stopwatch(user.user_id)
        active_session_id = active.get("session_id") if active else None
    except Exception as e:
        logger.warning(
            f"stale_session_recovery: redis unavailable, skip-active disabled "
            f"for user_id={user.user_id}: {e}"
        )
        active_session_id = None

    closed = 0
    for session in stale:
        try:
            # Skip currently-active session — operator just resumed it
            # via swap, or is in a long deep-work session. Closing the
            # pointed-to session would clear Redis underneath the user.
            if active_session_id and session.session_id == active_session_id:
                logger.info(
                    f"stale_session_recovery: skipping currently-active "
                    f"session_id={session.session_id} user_id={user.user_id}"
                )
                continue

            task = db.query(Task).filter(Task.task_id == session.task_id).first()
            if task and task.voided_at is not None:
                continue
            planned = max((task.planned_duration_minutes if task else None) or 60, 1)
            end_time = session.start_time_utc + timedelta(minutes=planned)
            session.end_time_utc = end_time
            session.auto_closed = True
            session.paused_at_utc = None

            # Close any open pause_event rows for this session so pause-history
            # analytics don't carry dangling opens. Clean-data filters still key
            # off stopwatch_session.auto_closed (see _close_orphan_session in
            # stopwatch_manager.py for the reasoning).
            open_events = (
                db.query(PauseEvent)
                .filter(
                    PauseEvent.session_id == session.session_id,
                    PauseEvent.resumed_at_utc.is_(None),
                )
                .all()
            )
            for evt in open_events:
                evt.resumed_at_utc = end_time
                evt.duration_minutes = (
                    (end_time - evt.paused_at_utc).total_seconds() / 60.0
                )

            # Defense-in-depth: transition Task.state if it's still abandoned-shaped.
            # Confirms there's no OTHER open session (multi-tasking case where
            # this task somehow has multiple sessions across resume cycles —
            # unlikely but defensive). Only transitions when this is the LAST
            # open session for the task.
            if task and task.voided_at is None and task.state in (TaskState.EXECUTING, TaskState.PAUSED):
                other_open = (
                    db.query(StopwatchSession)
                    .filter(
                        StopwatchSession.task_id == task.task_id,
                        StopwatchSession.end_time_utc.is_(None),
                        StopwatchSession.session_id != session.session_id,
                    )
                    .first()
                )
                if not other_open:
                    task.state = TaskState.SKIPPED
                    task.initiation_status = "orphaned_recovery"
                    task.last_modified_at = end_time

            closed += 1
            logger.warning(
                f"stale_session_recovery: closed session_id={session.session_id} "
                f"task_id={session.task_id} started_at={session.start_time_utc.isoformat()} "
                f"user_id={user.user_id}"
            )
        except Exception as e:
            logger.error(
                f"stale_session_recovery: failed to close session_id={session.session_id} "
                f"user_id={user.user_id}: {e}",
                exc_info=True,
            )

    try:
        db.commit()
        logger.info(
            f"stale_session_recovery: closed {closed}/{len(stale)} stale sessions "
            f"for user_id={user.user_id}"
        )
        # Operator fanout (2026-04-30): stale session recovery means
        # a stopwatch was running for >12h with no stop signal — almost
        # always a browser-crash artifact, but operator should see.
        if closed and user.is_operator:
            from app.services.operator_notifier import notify_operator
            notify_operator(
                f"Auto-closed *{closed}* stale stopwatch session(s) (open >12h).",
                source="scheduler.stale-sessions",
                severity="warn",
            )
    except Exception as e:
        logger.error(
            f"stale_session_recovery: commit failed for user_id={user.user_id}: {e}",
            exc_info=True,
        )
        db.rollback()
