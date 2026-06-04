"""Stale session recovery background job.

Sweeps unclosed StopwatchSession rows and resolves them based on whether
the user actually walked away vs. is mid-deep-work. Two distinct branches:

  * Paused-and-abandoned (session.paused_at_utc < now - 48h):
      - executed_so_far ≥ 0.5 * planned → EXECUTED  (honest work, forgot to stop)
      - executed_so_far <  0.5 * planned → SKIPPED  (early-stop gate)
      Session ends at paused_at_utc; pause_event closed with duration=0.

  * Active-and-abandoned (no pause, session.start_time_utc < now - 48h):
      Always → SKIPPED. An unattended always-running timer cannot honestly
      claim executed time; mark abandoned.

48h chosen as the floor where Redis active-stopwatch state and the
multi-tasking swap path start producing edge cases (stale rehydrated
banners, ghost active keys). Higher thresholds were considered but
deferred — paused state can't sit indefinitely without Redis-side risk.

History:
  * 2026-04-11 LYR-103: original 24h sweep landed (CO-block ghost incident).
  * 2026-04-12: lowered to 12h after a 16h paused session went undetected.
  * 2026-04-25: skip-active-session protection + defense-in-depth task-state
    transition to SKIPPED to close the "Stop works but session is gone" window.
  * 2026-05-01: reworked. The blanket 12h trigger killed a real 6h build
    session paused for context-switch (operator incident, restored manually).
    New policy distinguishes paused vs active, raises threshold to 48h on
    both branches (Redis state can't tolerate forever-paused), and applies
    the 50% early-stop gate so honest work resolves to EXECUTED instead of
    SKIPPED. Negative pause_event.duration_minutes bug fixed in same pass.
"""
import logging
import time
from datetime import timedelta

import sqlalchemy as sa
from sqlalchemy.exc import OperationalError

from app.db.models import PauseEvent, StopwatchSession, Task, TaskState, User
from app.db.scoping import set_current_user_id
from app.db.session import SessionLocal
from app.utils.redis_client import RedisClient
from app.utils.time_utils import now_utc
from app.workers.jobs._per_user import for_each_user
from app.workers.jobs._scheduler_contract import (
    JobResult,
    NO_MUTATION_ATTEMPTED,
    degrade_job,
    dispose_engine_pool,
    run_scheduler_job,
)

logger = logging.getLogger(__name__)

STALE_PAUSE_HOURS = 72
STALE_ACTIVE_HOURS = 48
EARLY_STOP_FRACTION = 0.5  # mirrors stopwatch_manager early-stop gate
STALE_BOOTSTRAP_MAX_ATTEMPTS = 2
STALE_BOOTSTRAP_RETRY_DELAY_SECONDS = 1.0

# 2026-06-04 K04 policy: paused sessions that cross STALE_PAUSE_HOURS are
# not auto-resolved. They remain open for explicit user resolution through
# POST /v1/stopwatch/stale-pauses/{session_id}/resolve, which captures focus,
# completion percentage, and scope outcome and flags the session dirty for
# calibration. Only unattended active timers remain auto-abandoned here.


def run_stale_session_recovery() -> JobResult:
    return run_scheduler_job(
        "stale_session_recovery",
        "scheduler.stale-sessions",
        _run_stale_session_recovery,
    )


def _run_stale_session_recovery() -> JobResult:
    return for_each_user(
        _run_for_one_user,
        user_ids=_load_candidate_user_ids(),
        job_name="stale_session_recovery",
    )


def _load_candidate_user_ids() -> list[int]:
    """Load users who have stale open sessions before per-user mutation starts."""
    set_current_user_id(None)
    now = now_utc()
    pause_cutoff = now - timedelta(hours=STALE_PAUSE_HOURS)
    active_cutoff = now - timedelta(hours=STALE_ACTIVE_HOURS)

    for attempt in range(1, STALE_BOOTSTRAP_MAX_ATTEMPTS + 1):
        db = SessionLocal()
        failed_operationally = False
        try:
            rows = (
                db.query(StopwatchSession.user_id)
                .filter(
                    StopwatchSession.end_time_utc.is_(None),
                    sa.or_(
                        sa.and_(
                            StopwatchSession.paused_at_utc.isnot(None),
                            StopwatchSession.paused_at_utc < pause_cutoff,
                        ),
                        sa.and_(
                            StopwatchSession.paused_at_utc.is_(None),
                            StopwatchSession.start_time_utc < active_cutoff,
                        ),
                    ),
                )
                .distinct()
                .all()
            )
            return [int(row[0]) for row in rows if row[0] is not None]
        except OperationalError:
            failed_operationally = True
            try:
                db.rollback()
            except Exception:  # noqa: BLE001 - session may already be broken
                logger.debug(
                    "stale_session_recovery candidate bootstrap rollback failed",
                    exc_info=True,
                )
            logger.warning(
                "stale_session_recovery candidate bootstrap failed with "
                "OperationalError on attempt %s/%s",
                attempt,
                STALE_BOOTSTRAP_MAX_ATTEMPTS,
                exc_info=True,
            )
        finally:
            db.close()

        if failed_operationally:
            dispose_engine_pool(logger)
            if attempt < STALE_BOOTSTRAP_MAX_ATTEMPTS:
                time.sleep(STALE_BOOTSTRAP_RETRY_DELAY_SECONDS)

    degrade_job(
        job_id="stale_session_recovery",
        subsystem="scheduler.stale-sessions / candidate bootstrap",
        message=(
            "Stale session recovery candidate bootstrap failed with "
            "`OperationalError`. Job skipped this tick; check backend logs."
        ),
        affected="scheduler.stale-sessions / candidate bootstrap",
        scope="unknown candidate-user count; bootstrap could not load stale sessions",
        retry=(
            f"Retried {STALE_BOOTSTRAP_MAX_ATTEMPTS} total attempt(s), disposed "
            "the DB engine pool after each failure, then waits for the next "
            "scheduler tick."
        ),
        user_action="No student action. Operator should triage if repeated.",
        data_integrity=NO_MUTATION_ATTEMPTED,
        source="scheduler.stale-sessions",
        severity="error",
        dedupe_key="stale-session-candidates:OperationalError",
        cooldown_seconds=30 * 60,
    )


def _run_for_one_user(db, user: User):
    now = now_utc()
    pause_cutoff = now - timedelta(hours=STALE_PAUSE_HOURS)
    active_cutoff = now - timedelta(hours=STALE_ACTIVE_HOURS)
    redis = RedisClient()

    open_sessions = db.query(StopwatchSession).filter(
        StopwatchSession.end_time_utc.is_(None),
    ).all()
    if not open_sessions:
        return

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
    executed_count = 0
    skipped_count = 0

    for session in open_sessions:
        try:
            # Skip currently-active session — operator deliberately on it.
            if active_session_id and session.session_id == active_session_id:
                logger.info(
                    f"stale_session_recovery: skipping currently-active "
                    f"session_id={session.session_id} user_id={user.user_id}"
                )
                continue

            task = db.query(Task).filter(Task.task_id == session.task_id).first()
            if task and task.voided_at is not None:
                continue

            is_paused_branch = (
                session.paused_at_utc is not None
                and session.paused_at_utc < pause_cutoff
            )
            is_active_branch = (
                session.paused_at_utc is None
                and session.start_time_utc < active_cutoff
            )
            if not (is_paused_branch or is_active_branch):
                continue  # threshold not tripped

            planned = max((task.planned_duration_minutes if task else None) or 60, 1)

            if is_paused_branch:
                logger.info(
                    "stale_session_recovery: paused session_id=%s user_id=%s "
                    "is >%sh stale; leaving open for user reflection resolution",
                    session.session_id,
                    user.user_id,
                    STALE_PAUSE_HOURS,
                )
                continue
            else:
                # Active branch: synthetic end_time = start + planned. SKIPPED
                # regardless, so this is for session-row data integrity only.
                end_time = session.start_time_utc + timedelta(minutes=planned)

            session.end_time_utc = end_time
            session.auto_closed = True
            session.paused_at_utc = None

            # Close any open pause_event rows. Clamp resumed_at >= paused_at and
            # duration >= 0 — fixes Apr 30 bug where blindly setting
            # resumed_at = end_time wrote negative durations when paused_at > end_time.
            open_events = (
                db.query(PauseEvent)
                .filter(
                    PauseEvent.session_id == session.session_id,
                    PauseEvent.resumed_at_utc.is_(None),
                )
                .all()
            )
            for evt in open_events:
                evt.resumed_at_utc = max(evt.paused_at_utc, end_time)
                evt.duration_minutes = max(
                    0.0,
                    (evt.resumed_at_utc - evt.paused_at_utc).total_seconds() / 60.0,
                )
            db.flush()

            total_pause_minutes = float(
                db.query(sa.func.coalesce(sa.func.sum(PauseEvent.duration_minutes), 0))
                .filter(PauseEvent.session_id == session.session_id)
                .scalar()
                or 0
            )
            executed_minutes = max(
                0.0,
                (end_time - session.start_time_utc).total_seconds() / 60.0
                - total_pause_minutes,
            )

            resolution = (
                "EXECUTED"
                if is_paused_branch and executed_minutes >= EARLY_STOP_FRACTION * planned
                else "SKIPPED"
            )

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
                    if resolution == "EXECUTED":
                        task.state = TaskState.EXECUTED
                        task.executed_duration_minutes = int(round(executed_minutes))
                        task.initiation_status = task.initiation_status or "initiated"
                        task.last_modified_at = end_time
                        executed_count += 1
                    else:
                        task.state = TaskState.SKIPPED
                        task.initiation_status = "orphaned_recovery"
                        task.last_modified_at = end_time
                        skipped_count += 1

            closed += 1
            logger.warning(
                f"stale_session_recovery: closed session_id={session.session_id} "
                f"task_id={session.task_id} "
                f"branch={'paused' if is_paused_branch else 'active'} "
                f"resolution={resolution} executed_min={executed_minutes:.1f} "
                f"planned_min={planned} started_at={session.start_time_utc.isoformat()} "
                f"user_id={user.user_id}"
            )
        except OperationalError:
            db.rollback()
            raise
        except Exception as e:
            logger.error(
                f"stale_session_recovery: failed to close session_id={session.session_id} "
                f"user_id={user.user_id}: {e}",
                exc_info=True,
            )

    try:
        db.commit()
        logger.info(
            f"stale_session_recovery: closed {closed}/{len(open_sessions)} stale sessions "
            f"({executed_count} EXECUTED, {skipped_count} SKIPPED) "
            f"for user_id={user.user_id}"
        )
        if closed and user.is_operator:
            from app.services.operator_notifier import notify_operator
            parts = []
            if executed_count:
                parts.append(f"{executed_count} EXECUTED (≥50% planned)")
            if skipped_count:
                parts.append(f"{skipped_count} SKIPPED")
            detail = ", ".join(parts) if parts else "session-only"
            notify_operator(
                f"Auto-closed *{closed}* stale stopwatch session(s) "
                f"(paused>{STALE_PAUSE_HOURS}h or unattended>{STALE_ACTIVE_HOURS}h): {detail}.",
                source="scheduler.stale-sessions",
                severity="warn",
                dedupe_key=f"stale-sessions:{user.user_id}:{closed}:{executed_count}:{skipped_count}",
                cooldown_seconds=30 * 60,
            )
    except OperationalError:
        logger.error(
            f"stale_session_recovery: commit failed with OperationalError "
            f"for user_id={user.user_id}",
            exc_info=True,
        )
        db.rollback()
        raise
    except Exception as e:
        logger.error(
            f"stale_session_recovery: commit failed for user_id={user.user_id}: {e}",
            exc_info=True,
        )
        db.rollback()
