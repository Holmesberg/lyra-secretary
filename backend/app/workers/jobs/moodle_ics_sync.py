"""Periodic Moodle iCal sync, every 6h per connected user.

Iterates users with `moodle_ics_url IS NOT NULL` and runs
`services.moodle_ics_sync.sync_user()` per user. The service handles all error
paths: 4xx disconnects the URL, transient failures retry next cycle, and parse
failures log and skip.
"""
import logging

from app.db.models import User
from app.services import moodle_ics_sync
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def _operator_error_message(error: str) -> str:
    if error.startswith("http_"):
        try:
            status = int(error.split("_", 1)[1])
        except (IndexError, ValueError):
            status = 0
        if 400 <= status < 500:
            return (
                f"Moodle sync failed: `{error}`. Moodle rejected the calendar "
                "URL, so Lyra disconnected it. Reconnect Moodle in /settings."
            )
        if 500 <= status < 600:
            return (
                f"Moodle sync failed: `{error}`. Moodle is temporarily "
                "unavailable or rate-limiting; Lyra kept the connection and "
                "will retry on the next cycle."
            )
    if error in {"fetch_failed", "fetch_unknown"}:
        return (
            f"Moodle sync failed: `{error}`. Lyra kept the connection and "
            "will retry on the next cycle."
        )
    return (
        f"Moodle sync failed: `{error}`. Lyra kept the connection unless "
        "Settings shows reconnect needed."
    )


def run_moodle_ics_sync() -> None:
    """Entry point for the APScheduler job."""
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User) -> None:
    if not user.moodle_ics_url:
        return
    result = moodle_ics_sync.sync_user(user.user_id, db)
    if result.error:
        logger.info(
            "moodle: user %s sync ended with error=%s",
            user.user_id,
            result.error,
        )
        if user.is_operator:
            from app.services.operator_notifier import notify_operator

            notify_operator(
                _operator_error_message(result.error),
                source="scheduler.moodle",
                severity="error",
                dedupe_key=f"moodle-ics-error:{user.user_id}:{result.error}",
                cooldown_seconds=60 * 60,
            )
        return
    logger.info(
        "moodle: user %s sync ok - fetched=%d created=%d updated=%d unchanged=%d voided=%d unparseable=%d",
        user.user_id,
        result.fetched,
        result.created,
        result.updated,
        result.unchanged,
        result.skipped_voided,
        result.skipped_unparseable,
    )
    if user.is_operator and (
        result.created or result.updated or result.skipped_voided
    ):
        from app.services.operator_notifier import notify_operator

        notify_operator(
            f"Moodle sync: created *{result.created}*, updated *{result.updated}*, voided *{result.skipped_voided}* deadlines.",
            source="scheduler.moodle",
            severity="info",
            dedupe_key=f"moodle-ics-summary:{user.user_id}:{result.created}:{result.updated}:{result.skipped_voided}",
            cooldown_seconds=15 * 60,
        )
    if user.is_operator and result.skipped_unparseable:
        from app.services.operator_notifier import notify_operator

        notify_operator(
            f"Moodle sync skipped *{result.skipped_unparseable}* unparseable event(s).",
            source="scheduler.moodle",
            severity="warn",
            dedupe_key=f"moodle-ics-unparseable:{user.user_id}",
            cooldown_seconds=6 * 60 * 60,
        )
