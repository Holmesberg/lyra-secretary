"""Reconcile pause_prediction_log outcomes against pause_event evidence.

Every 5 minutes, sweep rows where user_response IS NULL and the acceptance
window has closed. Set user_response to:

  * 'pause_now'    — a pause_event landed for this user between fired_at
                     and predicted_at + ACCEPTANCE_WINDOW_MINUTES
  * 'no_response'  — window closed without a matching pause

'dismiss' and 'snooze' outcomes come from explicit user replies to the
Telegram notification (commit 5b) — this job only handles the silent case,
which is the pre-registered denominator driver (MANIFESTO §VT-17: "Window
starts at each user's first pause_prediction_log row").

Design notes:

  * Acceptance window is anchored on predicted_at (not fired_at). A 5-min
    grace captures predictions that were right about the behavior but a
    bit late on timing — important because the predictor's lead window
    (2–3 min) is narrow relative to pause duration.

  * The matching pause_event's session is not required to be the same
    as the prediction's active_task_id. A user who pauses an unplanned
    task after receiving a prediction still counts — the research claim
    is "pauses happen when predicted," not "pauses happen on the task I
    predicted for."

  * We never revisit a closed row. If a later user action would have
    changed the outcome (e.g. a delayed pause 10 min after the window
    closed), that's a deliberate cutoff — the pre-registration froze
    the window formula and changing it retroactively would contaminate
    the acceptance_rate measurement.
"""
import logging
from datetime import timedelta

from app.db.models import PauseEvent, PausePredictionLog, User
from app.utils.time_utils import now_utc
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)

# Grace period after predicted_at during which a pause_event still counts
# as acceptance. See docstring for why the window is anchored here.
ACCEPTANCE_WINDOW_MINUTES = 5


def run_reconcile_responses():
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User):
    now = now_utc()
    cutoff = now - timedelta(minutes=ACCEPTANCE_WINDOW_MINUTES)

    # Rows whose acceptance window has closed and still have no outcome.
    # We filter on predicted_at rather than fired_at so late predictions
    # (edge-of-lead-window fires) get their full grace period.
    unreconciled = (
        db.query(PausePredictionLog)
        .filter(
            PausePredictionLog.user_id == user.user_id,
            PausePredictionLog.user_response.is_(None),
            PausePredictionLog.predicted_at <= cutoff,
        )
        .all()
    )

    if not unreconciled:
        return

    reconciled_count = 0
    accepted_count = 0

    for row in unreconciled:
        window_end = row.predicted_at + timedelta(minutes=ACCEPTANCE_WINDOW_MINUTES)
        matching_pause = (
            db.query(PauseEvent)
            .filter(
                PauseEvent.user_id == user.user_id,
                PauseEvent.paused_at_utc >= row.fired_at,
                PauseEvent.paused_at_utc <= window_end,
            )
            .order_by(PauseEvent.paused_at_utc.asc())
            .first()
        )

        if matching_pause is not None:
            row.user_response = "pause_now"
            row.response_at = matching_pause.paused_at_utc
            accepted_count += 1
        else:
            row.user_response = "no_response"
            row.response_at = now

        reconciled_count += 1

    try:
        db.commit()
    except Exception as e:
        logger.error(
            f"reconcile_responses: commit failed for user_id={user.user_id}: {e}",
            exc_info=True,
        )
        db.rollback()
        return

    logger.info(
        f"reconcile_responses: user_id={user.user_id} "
        f"reconciled={reconciled_count} accepted={accepted_count}"
    )
