"""Stale session recovery background job.

Sweeps unclosed StopwatchSession rows whose start_time is more than
24 hours old and auto-closes them. Prevents the class of incident where
a browser crash mid-pause, container restart before resume, or voided
task leaves an orphan session that the banner surfaces forever (the 65h
CO-block ghost, Apr 11 — LYR-103).

Conservative by design:
  * 24h threshold — never touches a legitimate long task
  * end_time_utc = start_time_utc + max(planned_duration, 1) min so the
    row has a defensible duration rather than extending to "now"
  * Redis keys cleared only if they still point at the stale session
  * Per-user iteration via for_each_user so a bad row on one tenant
    doesn't poison the sweep for everyone else
"""
import logging
from datetime import timedelta

from app.db.models import StopwatchSession, Task, User
from app.utils.redis_client import RedisClient
from app.utils.time_utils import now_utc
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)

STALE_THRESHOLD_HOURS = 24


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

    closed = 0
    for session in stale:
        try:
            task = db.query(Task).filter(Task.task_id == session.task_id).first()
            planned = max((task.planned_duration_minutes if task else None) or 60, 1)
            session.end_time_utc = session.start_time_utc + timedelta(minutes=planned)
            session.auto_closed = True
            session.paused_at_utc = None

            active = redis.get_active_stopwatch(user.user_id)
            if active and active.get("session_id") == session.session_id:
                redis.clear_active_stopwatch(user.user_id)
                redis.clear_pause_state(user.user_id)

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
    except Exception as e:
        logger.error(
            f"stale_session_recovery: commit failed for user_id={user.user_id}: {e}",
            exc_info=True,
        )
        db.rollback()
