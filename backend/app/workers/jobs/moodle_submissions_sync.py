"""Moodle Web Services submission-detection job.

Runs every 6h alongside the iCal sync. For each user with a stored
moodle_ws_token, queries Moodle's mod_assign_get_submission_status
for each task-bound active deadline and auto-marks completed when
Moodle confirms submission/grading. Operator-Telegram fanout fires
once per sync (aggregate summary, no per-mark spam).

Cadence rationale: matches the iCal sync 6h cadence so a single
operator-facing telegram thread carries both kinds of Moodle update
in temporal proximity (iCal new-deadlines first, then submission
state second). 6h is also polite to Moodle's WS rate limits.
"""
import logging
import os

from app.db.models import User
from app.services import moodle_submissions_sync
from app.services.operator_notifier import notify_operator
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def run_moodle_submissions_sync() -> None:
    """Entry point for APScheduler."""
    for_each_user(_run_for_one_user)


def _operator_error_message(error: str) -> tuple[str, str]:
    if error == "auth":
        return (
            "Moodle Web Services token rejected - likely rotated. "
            "Reconnect from Settings -> Moodle.",
            "error",
        )
    if error in {"token_decrypt_failed", "no_token"}:
        return (
            f"Moodle Web Services cannot sync because `{error}`. "
            "Reconnect Moodle Web Services in Settings.",
            "error",
        )
    if error == "no_moodle_userid":
        return (
            "Moodle Web Services could not resolve the Moodle user id. "
            "Reconnect Moodle Web Services in Settings.",
            "error",
        )
    return (
        f"Moodle Web Services sync failed with `{error}`. Lyra kept the "
        "connection and will retry on the next cycle.",
        "warn",
    )


def _run_for_one_user(db, user: User) -> None:
    if not user.moodle_ws_token:
        return
    # Per-user base URL (alembic 044), iCal-origin derivation for legacy
    # rows, then env fallback for the oldest operator setup.
    base_url = moodle_submissions_sync.resolve_base_url(
        user,
        os.environ.get("MOODLE_WS_BASE_URL", ""),
    )
    if not base_url:
        logger.warning(
            "moodle_ws: no base URL for user %s (column NULL + env unset)",
            user.user_id,
        )
        if user.is_operator:
            notify_operator(
                "Moodle Web Services has a token but no base URL. "
                "Reconnect Moodle in Settings.",
                source="scheduler.moodle-ws",
                severity="error",
                dedupe_key=f"moodle-ws-no-base-url:{user.user_id}",
                cooldown_seconds=6 * 60 * 60,
            )
        return
    result = moodle_submissions_sync.sync_user(user, base_url, db)
    db.commit()

    if result.error:
        logger.info(
            "moodle_ws: user %s sync ended with error=%s",
            user.user_id, result.error,
        )
        # Surface both auth and non-auth WS failures; payload contains no
        # Moodle token, URL, course title, or assignment title.
        if user.is_operator:
            message, severity = _operator_error_message(result.error)
            notify_operator(
                message,
                source="scheduler.moodle-ws",
                severity=severity,
                dedupe_key=f"moodle-ws-error:{user.user_id}:{result.error}",
                cooldown_seconds=6 * 60 * 60,
            )
        return

    backfilled = (
        result.backfilled_completed
        + result.backfilled_planned
        + result.backfilled_missed
    )
    logger.info(
        "moodle_ws: user %s sync ok — matched=%d marked_complete=%d "
        "skipped_no_match=%d skipped_not_submitted=%d backfilled=%d",
        user.user_id,
        result.matched,
        result.marked_complete,
        result.skipped_no_match,
        result.skipped_not_submitted,
        backfilled,
    )

    if user.is_operator and (result.marked_complete or backfilled):
        lines = []
        if result.marked_complete:
            lines.append(
                f"Auto-marked *{result.marked_complete}* deadline(s) complete:"
            )
            lines.extend(f"• {t}" for t in result.marked_titles)
        if backfilled:
            lines.append(
                f"Backfilled *{backfilled}* assignment(s) "
                f"({result.backfilled_completed} done, "
                f"{result.backfilled_missed} missed, "
                f"{result.backfilled_planned} planned)."
            )
        notify_operator(
            "Moodle WS sync —\n" + "\n".join(lines),
            source="scheduler.moodle-ws",
            severity="info",
            dedupe_key=f"moodle-ws-summary:{user.user_id}:{result.marked_complete}:{backfilled}",
            cooldown_seconds=15 * 60,
        )
