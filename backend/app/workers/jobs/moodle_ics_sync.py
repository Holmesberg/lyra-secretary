"""Periodic Moodle iCal sync, every 6h per connected user.

Iterates users with `moodle_ics_url IS NOT NULL` and runs
`services.moodle_ics_sync.sync_user()` per user. The service handles all error
paths: 4xx disconnects the URL, transient failures retry next cycle, and parse
failures log and skip.
"""
import logging

from app.db.models import User
from app.services import moodle_ics_sync
from app.services.operator_notifier import format_alert_context, redacted_user_ref
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def _operator_error_message(error: str) -> tuple[str, str, str, str, str]:
    if error.startswith("http_"):
        try:
            status = int(error.split("_", 1)[1])
        except (IndexError, ValueError):
            status = 0
        if 400 <= status < 500:
            return (
                f"Moodle sync failed: `{error}`. Moodle rejected the calendar "
                "URL, so LyraOS disconnected it. Reconnect Moodle in /settings.",
                "warn",
                "No retry until the user reconnects the Moodle calendar.",
                "Yes - reconnect Moodle in Settings.",
                "No imported deadlines were deleted; future Moodle imports are paused.",
            )
        if 500 <= status < 600:
            return (
                f"Moodle sync failed: `{error}`. Moodle is temporarily "
                "unavailable or rate-limiting; LyraOS kept the connection and "
                "will retry on the next cycle.",
                "warn",
                "LyraOS kept the connection and will retry on the next cycle.",
                "No user action unless the outage persists.",
                "No mutation beyond retaining existing imported deadlines.",
            )
    if error in {"fetch_failed", "fetch_unknown"}:
        return (
            f"Moodle sync failed: `{error}`. LyraOS kept the connection and "
            "will retry on the next cycle.",
            "warn",
            "LyraOS kept the connection and will retry on the next cycle.",
            "No user action unless the outage persists.",
            "No mutation beyond retaining existing imported deadlines.",
        )
    return (
        f"Moodle sync failed: `{error}`. LyraOS kept the connection unless "
        "Settings shows reconnect needed.",
        "warn",
        "LyraOS will retry on the next cycle if the connection remains present.",
        "Check Settings only if reconnect is shown.",
        "No completion inference or deadline deletion from this failure.",
    )


def run_moodle_ics_sync() -> None:
    """Entry point for the APScheduler job."""
    for_each_user(_run_for_one_user, job_name="moodle_ics_sync")


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

            message, severity, retry, user_action, data_integrity = (
                _operator_error_message(result.error)
            )
            notify_operator(
                message
                + "\n\n"
                + format_alert_context(
                    affected="Moodle iCal / deadline import",
                    scope=redacted_user_ref(user.user_id),
                    retry=retry,
                    user_action=user_action,
                    data_integrity=data_integrity,
                ),
                source="scheduler.moodle",
                severity=severity,
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
            f"Moodle sync skipped *{result.skipped_unparseable}* "
            "unparseable event(s).\n\n"
            + format_alert_context(
                affected="Moodle iCal / deadline import",
                scope=redacted_user_ref(user.user_id),
                retry=(
                    "Skipped events are not imported; future cycles may "
                    "import them if Moodle changes the event shape."
                ),
                user_action=(
                    "No student action unless expected deadlines are missing."
                ),
                data_integrity=(
                    "Ambiguous events are skipped rather than imported with "
                    "fake precision."
                ),
            ),
            source="scheduler.moodle",
            severity="warn",
            dedupe_key=f"moodle-ics-unparseable:{user.user_id}",
            cooldown_seconds=6 * 60 * 60,
        )
