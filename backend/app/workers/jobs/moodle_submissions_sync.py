"""Moodle Web Services submission-detection job.

Runs every 6h alongside the iCal sync. For each user with a stored
moodle_ws_token, queries Moodle's mod_assign_get_submission_status and records
provider completion candidates when Moodle reports submission/grading. Moodle
does not silently complete Barzakh deadlines; the user remains author of truth.

Cadence rationale: matches the iCal sync 6h cadence so a single
operator-facing telegram thread carries both kinds of Moodle update
in temporal proximity (iCal new-deadlines first, then submission
state second). 6h is also polite to Moodle's WS rate limits.
"""
import logging
import os

from app.db.models import User
from app.services import moodle_submissions_sync
from app.services.operator_notifier import (
    format_alert_context,
    notify_operator,
    redacted_user_ref,
)
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def run_moodle_submissions_sync() -> None:
    """Entry point for APScheduler."""
    for_each_user(_run_for_one_user, job_name="moodle_submissions_sync")


def _operator_error_message(error: str) -> tuple[str, str, str, str, str]:
    if error == "auth":
        return (
            "Moodle Web Services token rejected - likely rotated. "
            "Reconnect from Settings -> Moodle.",
            "warn",
            "Will retry on future cycles, but success requires reconnect.",
            "Yes - reconnect Moodle Web Services in Settings.",
            "No deadline completion is inferred while auth is rejected.",
        )
    if error in {"token_decrypt_failed", "no_token"}:
        return (
            f"Moodle Web Services cannot sync because `{error}`. "
            "Reconnect Moodle Web Services in Settings.",
            "warn",
            "Will retry on future cycles, but success requires reconnect.",
            "Yes - reconnect Moodle Web Services in Settings.",
            "No submission/completion state is changed from this failure.",
        )
    if error == "no_moodle_userid":
        return (
            "Moodle Web Services could not resolve the Moodle user id. "
            "Reconnect Moodle Web Services in Settings.",
            "warn",
            "Will retry on future cycles, but success likely requires reconnect.",
            "Yes - reconnect Moodle Web Services in Settings.",
            "No submission/completion state is changed from this failure.",
        )
    return (
        f"Moodle Web Services sync failed with `{error}`. Barzakh kept the "
        "connection and will retry on the next cycle.",
        "warn",
        "Barzakh kept the connection and will retry on the next cycle.",
        "No user action unless the provider failure persists.",
        "No submission/completion state is changed from this failure.",
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
                "Reconnect Moodle in Settings.\n\n"
                + format_alert_context(
                    affected="Moodle Web Services / submission sync",
                    scope=redacted_user_ref(user.user_id),
                    retry=(
                        "Will retry on future cycles, but success requires "
                        "a base URL from reconnect."
                    ),
                    user_action="Yes - reconnect Moodle in Settings.",
                    data_integrity=(
                        "No submission/completion state is changed from "
                        "this failure."
                    ),
                ),
                source="scheduler.moodle-ws",
                severity="warn",
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
            message, severity, retry, user_action, data_integrity = (
                _operator_error_message(result.error)
            )
            notify_operator(
                message
                + "\n\n"
                + format_alert_context(
                    affected="Moodle Web Services / submission sync",
                    scope=redacted_user_ref(user.user_id),
                    retry=retry,
                    user_action=user_action,
                    data_integrity=data_integrity,
                ),
                source="scheduler.moodle-ws",
                severity=severity,
                dedupe_key=f"moodle-ws-error:{user.user_id}:{result.error}",
                cooldown_seconds=6 * 60 * 60,
            )
        return

    backfilled = (
        result.backfilled_completed
        + result.backfilled_completion_candidates
        + result.backfilled_planned
        + result.backfilled_missed
    )
    logger.info(
        "moodle_ws: user %s sync ok - matched=%d completion_candidates=%d "
        "skipped_no_match=%d skipped_not_submitted=%d backfilled=%d",
        user.user_id,
        result.matched,
        result.completion_candidates,
        result.skipped_no_match,
        result.skipped_not_submitted,
        backfilled,
    )

    if user.is_operator and (result.completion_candidates or backfilled):
        lines = []
        if result.completion_candidates:
            lines.append(
                f"Recorded *{result.completion_candidates}* Moodle completion candidate(s):"
            )
            lines.extend(f"- {t}" for t in result.completion_candidate_titles)
        if backfilled:
            lines.append(
                f"Backfilled *{backfilled}* assignment(s) "
                f"({result.backfilled_completion_candidates} completion candidate, "
                f"{result.backfilled_missed} missed, "
                f"{result.backfilled_planned} planned)."
            )
        notify_operator(
            "Moodle WS sync -\n" + "\n".join(lines),
            source="scheduler.moodle-ws",
            severity="info",
            dedupe_key=f"moodle-ws-summary:{user.user_id}:{result.completion_candidates}:{backfilled}",
            cooldown_seconds=15 * 60,
        )
