"""Periodic Moodle iCal sync — every 6h per connected user.

Iterates users with `moodle_ics_url IS NOT NULL` and runs
`services.moodle_ics_sync.sync_user()` per user. The service handles
all error paths (4xx → clear URL, transient → retry next cycle, parse
failure → log + skip), so this job is a thin scheduler shim.

Cadence rationale: Moodle docs note new/changed events appear in the
.ics feed within "several hours." 6h is the right granularity — fast
enough that newly-posted assignments show up same-day, slow enough to
be polite to the LMS server. (alembic 041, 2026-04-29.)
"""
import logging

from app.db.models import User
from app.services import moodle_ics_sync
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def run_moodle_ics_sync() -> None:
    """Entry point for the APScheduler job."""
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User) -> None:
    if not user.moodle_ics_url:
        return
    result = moodle_ics_sync.sync_user(user.user_id, db)
    if result.error:
        # sync_user already logged the warning with redacted URL — log
        # only the summary here at info level so the job log isn't noisy.
        logger.info(
            "moodle: user %s sync ended with error=%s",
            user.user_id, result.error,
        )
        # Operator fanout (2026-04-30) on errors only — success is too
        # frequent at 6h cadence to be useful as a Telegram ping.
        if user.is_operator:
            from app.services.operator_notifier import notify_operator
            notify_operator(
                f"Moodle sync failed: `{result.error}`. If 4xx, the auth token rotated — reconnect Moodle in /settings.",
                source="scheduler.moodle",
                severity="error",
            )
        return
    logger.info(
        "moodle: user %s sync ok — fetched=%d created=%d updated=%d unchanged=%d voided=%d unparseable=%d",
        user.user_id,
        result.fetched,
        result.created,
        result.updated,
        result.unchanged,
        result.skipped_voided,
        result.skipped_unparseable,
    )
    # Operator fanout (2026-04-30) on meaningful success — only when
    # something CHANGED (new/updated/voided > 0). Pure no-ops are
    # silent so the operator's Telegram doesn't fill with "moodle: 0
    # changes" every 6 hours.
    if user.is_operator and (result.created or result.updated or result.skipped_voided):
        from app.services.operator_notifier import notify_operator
        notify_operator(
            f"Moodle sync: created *{result.created}*, updated *{result.updated}*, voided *{result.skipped_voided}* deadlines.",
            source="scheduler.moodle",
            severity="info",
        )
