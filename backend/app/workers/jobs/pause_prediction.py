"""Pause prediction background job (per-user, every 1 minute).

Runs PausePredictor for each user on each tick. If a prediction passes all
gates, writes one row to pause_prediction_log (the pre-registered research
artifact) and enqueues a notification payload onto the per-user Redis
queue. A firing cooldown prevents re-firing for the same user within
FIRING_COOLDOWN_MINUTES.

No Telegram delivery here — that is commit 5b. The queued payload is a
structured dict with firing_id + mechanism + predicted_at + lead_minutes;
5b will shape the text template and route via telegram_notifier.

Determining the active task:
  * Prefer the Redis active_stopwatch key — it is the source of truth
    during a live session and distinguishes EXECUTING from PAUSED without
    a Task.state roundtrip.
  * Fall back to a direct Task.state == EXECUTING query (auto-scoped via
    the ContextVar) so a Redis-loss edge case still produces predictions.
  * If neither produces a task, active_task is None and the predictor
    runs with clock_anchor only.

Mutations are committed on successful prediction; on exception we swallow
and log — one user's failure must not poison the job for others
(_per_user.for_each_user already enforces this, but we also catch locally
so a partial write does not leak into the next user's scope).
"""
import json
import logging

from app.db.models import PausePredictionLog, Task, TaskState, User
from app.services.notification_queue import enqueue_user_notification
from app.services.pause_predictor import PausePredictor
from app.services.telegram_notifier import send_telegram_message_sync
from app.utils.redis_client import RedisClient
from app.utils.time_utils import now_utc
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)

# Don't re-fire for the same user within this window. Predictor already
# enforces a lead window of 2-3 min, but the job runs every minute — without
# a cooldown, a user with a rock-solid 10:48 clock_anchor bucket would get
# three firings across 10:45, 10:46, 10:47. 10 min cooldown means the window
# between 10:45 and the natural cooldown expiry (10:55) cleanly contains the
# single predicted pause at ~10:48.
FIRING_COOLDOWN_MINUTES = 10


def run_pause_prediction():
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User):
    now = now_utc()

    # Cooldown: skip if we already fired recently for this user.
    recent = (
        db.query(PausePredictionLog)
        .filter(PausePredictionLog.user_id == user.user_id)
        .order_by(PausePredictionLog.fired_at.desc())
        .first()
    )
    if recent is not None:
        cooldown_elapsed = (now - recent.fired_at).total_seconds() / 60.0
        if cooldown_elapsed < FIRING_COOLDOWN_MINUTES:
            return

    active_task = _resolve_active_task(db, user)

    # Product gate (Apr 25): pause predictions only fire when the user
    # currently has an active stopwatch (Task.state == EXECUTING with an
    # open StopwatchSession). The clock-anchor-only mechanism — which
    # could fire without an active task — was producing predictions that
    # could never be confirmed by an actual pause event (no session = no
    # pause), so every such firing was a guaranteed VT-17 miss and noise
    # in the user's UI. Killing it cleans both UX and measurement.
    if active_task is None:
        return

    try:
        prediction = PausePredictor(db).predict(
            user_id=user.user_id,
            active_task=active_task,
            now=now,
        )
    except Exception as e:
        logger.error(
            f"pause_prediction: predictor raised for user_id={user.user_id}: {e}",
            exc_info=True,
        )
        return

    if prediction is None:
        return

    # Persist the firing. user_response + response_at remain NULL until the
    # reconcile job closes the acceptance window.
    row = PausePredictionLog(
        user_id=prediction.user_id,
        fired_at=prediction.fired_at,
        predicted_at=prediction.predicted_at,
        mechanism=prediction.mechanism,
        confidence=prediction.confidence,
        lead_minutes=prediction.lead_minutes,
        sample_size=prediction.sample_size,
        active_task_id=prediction.active_task_id,
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except Exception as e:
        logger.error(
            f"pause_prediction: DB commit failed for user_id={user.user_id}: {e}",
            exc_info=True,
        )
        db.rollback()
        return

    logger.info(
        f"pause_prediction: fired firing_id={row.firing_id} "
        f"user_id={user.user_id} mechanism={prediction.mechanism} "
        f"lead_minutes={prediction.lead_minutes} confidence={prediction.confidence}"
    )

    # Queue a structured payload for the OpenClaw agent polling loop
    # (/v1/notifications/pending) AND send the operator-facing text via
    # Telegram. Both are best-effort — neither failure rolls back the
    # already-committed research row.
    _enqueue_notification(user, row)
    _deliver_telegram(row)


def _resolve_active_task(db, user: User):
    """Return the user's currently EXECUTING Task, or None.

    Prefer the Redis active_stopwatch key as source of truth (it matches
    the StopwatchManager invariant). Fall back to a Task.state query scoped
    via the ContextVar when Redis is unavailable or empty.
    """
    try:
        redis = RedisClient()
        active = redis.get_active_stopwatch(str(user.user_id))
        if active:
            task = (
                db.query(Task)
                .filter(Task.task_id == active.get("task_id"))
                .first()
            )
            if task is not None and task.voided_at is None:
                # Only feed EXECUTING tasks to work_rhythm — a PAUSED task
                # already shipped its first pause and shouldn't generate a
                # second prediction in the same session.
                if task.state == TaskState.EXECUTING:
                    return task
                return None
    except Exception as e:
        logger.warning(
            f"pause_prediction: redis lookup failed for user_id={user.user_id}: {e}"
        )

    return (
        db.query(Task)
        .filter(
            Task.state == TaskState.EXECUTING,
            Task.voided_at.is_(None),
        )
        .first()
    )


def _enqueue_notification(user: User, row: PausePredictionLog) -> None:
    """Push a pause_prediction notification onto the per-user Redis queue.

    Non-fatal: if the push endpoint is unreachable we log and continue —
    the research row is already committed, which is what VT-17 measurement
    depends on. The delivered-to-user path is ancillary in 5a.
    """
    payload = {
        "type": "pause_prediction",
        "firing_id": row.firing_id,
        "mechanism": row.mechanism,
        "predicted_at": row.predicted_at.isoformat(),
        "lead_minutes": row.lead_minutes,
        "confidence": row.confidence,
        "active_task_id": row.active_task_id,
    }
    try:
        enqueue_user_notification(user.user_id, payload)
    except Exception as e:
        logger.warning(
            f"pause_prediction: notification enqueue failed for "
            f"firing_id={row.firing_id} user_id={user.user_id}: {e}"
        )


def _format_telegram_text(row: PausePredictionLog) -> str:
    """Short operator-facing text — tuned for a Telegram push.

    Lead-minutes first so the attention-grab is up top. `firing_id` is
    truncated to 8 chars in the visible text because the full UUID is
    noisy to read; the full id is what the agent uses to call
    /v1/pause_predictions/{firing_id}/respond from the queued payload.
    """
    mechanism_label = row.mechanism.replace("_", " ")
    return (
        f"*Pause predicted in ~{row.lead_minutes} min* "
        f"({mechanism_label}, {int(row.confidence * 100)}% confidence)\n\n"
        f"Reply: `pause`, `dismiss`, or `snooze`."
    )


def _deliver_telegram(row: PausePredictionLog) -> None:
    """Send the pause-prediction text via the Telegram bot.

    Non-fatal: a missing TELEGRAM_BOT_TOKEN / network glitch logs a
    warning and returns. The research row + agent-queue payload are
    already committed, so research integrity is preserved even when
    direct delivery fails.
    """
    try:
        send_telegram_message_sync(_format_telegram_text(row))
    except Exception as e:
        logger.warning(
            f"pause_prediction: telegram delivery failed for "
            f"firing_id={row.firing_id}: {e}"
        )
