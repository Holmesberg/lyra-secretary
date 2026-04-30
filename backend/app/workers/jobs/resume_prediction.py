"""Resume prediction background job (W2 magic-for-alpha 2026-04-28).

Sibling of pause_prediction. Runs every 2 minutes, iterates over each
PAUSED stopwatch session, and fires a "you usually resume by now"
banner when paused-for duration approaches the user's historical p75
for the (category, time_of_day) cell. Cold-start fallback at 30min flat
cap with synthetic mechanism.

Per-session 5min cooldown — the predictor is meant to nudge once, not
nag. If user ignores, they ignore.

Best-effort delivery: research row commits first; notification enqueue
is best-effort (failure logged, row stays committed).
"""
import logging

import httpx

from app.db.models import (
    PauseEvent,
    ResumePredictionLog,
    StopwatchSession,
    Task,
    TaskState,
    User,
)
from app.services.resume_predictor import COOLDOWN_MINUTES, ResumePredictor
from app.utils.time_utils import now_utc
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def run_resume_prediction():
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User):
    now = now_utc()

    # Find any active PAUSED tasks for the user.
    paused_tasks = (
        db.query(Task)
        .filter(
            Task.state == TaskState.PAUSED,
            Task.voided_at.is_(None),
        )
        .all()
    )
    if not paused_tasks:
        return

    for task in paused_tasks:
        try:
            _maybe_fire_for_task(db, user, task, now)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"resume_prediction: per-task error user_id={user.user_id} "
                f"task_id={task.task_id}: {e}"
            )


def _maybe_fire_for_task(db, user: User, task: Task, now) -> None:
    """Single-task evaluation. Idempotent — cooldown gate prevents spam."""
    # Latest open StopwatchSession for this task (PAUSED → there's an
    # unclosed session and an unresolved pause_event).
    session = (
        db.query(StopwatchSession)
        .filter(
            StopwatchSession.task_id == task.task_id,
            StopwatchSession.end_time_utc.is_(None),
        )
        .order_by(StopwatchSession.start_time_utc.desc())
        .first()
    )
    if session is None:
        return  # Defensive — PAUSED state without open session is a recovery edge

    # Latest unresolved pause for this session
    pause = (
        db.query(PauseEvent)
        .filter(
            PauseEvent.session_id == session.session_id,
            PauseEvent.resumed_at_utc.is_(None),
        )
        .order_by(PauseEvent.paused_at_utc.desc())
        .first()
    )
    if pause is None:
        return

    # Cooldown: skip if we already fired for this session recently.
    recent = (
        db.query(ResumePredictionLog)
        .filter(ResumePredictionLog.session_id == session.session_id)
        .order_by(ResumePredictionLog.fired_at.desc())
        .first()
    )
    if recent is not None:
        elapsed = (now - recent.fired_at).total_seconds() / 60.0
        if elapsed < COOLDOWN_MINUTES:
            return

    prediction = ResumePredictor(db).predict(
        user_id=user.user_id,
        session=session,
        task=task,
        paused_at_utc=pause.paused_at_utc,
        now=now,
    )
    if prediction is None:
        return

    row = ResumePredictionLog(
        user_id=prediction.user_id,
        session_id=prediction.session_id,
        task_id=prediction.task_id,
        fired_at=prediction.fired_at,
        paused_for_minutes=prediction.paused_for_minutes,
        p75_pause_minutes=prediction.p75_pause_minutes,
        mechanism=prediction.mechanism,
        confidence=prediction.confidence,
        sample_size=prediction.sample_size,
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except Exception as e:
        logger.error(
            f"resume_prediction: DB commit failed user_id={user.user_id}: {e}",
            exc_info=True,
        )
        db.rollback()
        return

    logger.info(
        f"resume_prediction: fired firing_id={row.firing_id} "
        f"user_id={user.user_id} mechanism={prediction.mechanism} "
        f"paused_for={prediction.paused_for_minutes}min "
        f"p75={prediction.p75_pause_minutes}"
    )

    _enqueue_notification(user, row, task)
    # Operator fanout (2026-04-30): mirror to telegram. Sibling of
    # pause_prediction's existing telegram fire — operator wanted
    # consistent coverage across both predictors.
    if user.is_operator:
        from app.services.operator_notifier import notify_operator
        notify_operator(
            f"Resume nudge — *{task.title}* paused {row.paused_for_minutes:.0f} min "
            f"(your usual is ~{row.p75_pause_minutes:.0f} min for this kind of session).",
            source="scheduler.resume-prediction",
            severity="alert",
        )


def _enqueue_notification(user: User, row: ResumePredictionLog, task: Task) -> None:
    payload = {
        "type": "resume_prediction",
        "firing_id": row.firing_id,
        "session_id": row.session_id,
        "task_id": row.task_id,
        "task_title": task.title,
        "category": task.category,
        "paused_for_minutes": row.paused_for_minutes,
        "p75_pause_minutes": row.p75_pause_minutes,
        "mechanism": row.mechanism,
        "confidence": row.confidence,
    }
    try:
        httpx.post(
            "http://localhost:8000/v1/notifications/push",
            json=payload,
            timeout=5.0,
            headers={"X-User-Id": str(user.user_id)},
        )
    except Exception as e:
        logger.warning(
            f"resume_prediction: notification enqueue failed for "
            f"firing_id={row.firing_id} user_id={user.user_id}: {e}"
        )
