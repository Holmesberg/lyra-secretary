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
import json

from app.db.models import (
    PauseEvent,
    ResumePredictionLog,
    StopwatchSession,
    Task,
    TaskState,
    User,
)
from app.services.notification_queue import enqueue_user_notification
from app.services.output_surfaces import emit_surface_render, emit_surface_suppression
from app.services.resume_predictor import (
    COOLDOWN_MINUTES,
    MAX_FIRES_PER_SESSION,
    ResumePredictor,
)
from app.utils.time_utils import now_utc
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def run_resume_prediction():
    for_each_user(_run_for_one_user, job_name="resume_prediction")


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

    # Cap total fires per session — operator decision 2026-05-01 to
    # stop hourly nagging on sessions the user has clearly abandoned.
    # After MAX_FIRES_PER_SESSION nudges, stay quiet; stale_session_
    # recovery will close the session at 12h regardless.
    fire_count_for_session = (
        db.query(ResumePredictionLog)
        .filter(ResumePredictionLog.session_id == session.session_id)
        .count()
    )
    if fire_count_for_session >= MAX_FIRES_PER_SESSION:
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

    _enqueue_notification(db, user, row, task)
    # Operator fanout (2026-04-30 + 2026-05-01 escalation refinement):
    # message changes with fire-count so the user isn't getting the
    # same "your usual is X" line after they've blown past X by 5×.
    # Fire 1 is the gentle nudge, fire 2 acknowledges the miss, fire 3
    # asks if the session should be abandoned. After fire 3 the
    # MAX_FIRES_PER_SESSION cap above keeps it quiet entirely.
    if user.is_operator:
        from app.services.operator_notifier import notify_operator
        # fire_count_for_session was the count BEFORE this fire landed,
        # so this fire is number (fire_count_for_session + 1).
        fire_n = fire_count_for_session + 1
        paused_min = int(round(row.paused_for_minutes))
        usual_min = int(round(row.p75_pause_minutes))
        if fire_n == 1:
            msg = (
                f"*{task.title}* paused {paused_min} min · usual is "
                f"~{usual_min} min for this kind of session. No rush."
            )
        elif fire_n == 2:
            msg = (
                f"*{task.title}* still paused at {paused_min} min · "
                f"whenever you're ready."
            )
        else:  # fire_n == 3 (final per MAX_FIRES_PER_SESSION cap)
            msg = (
                f"Last check on *{task.title}* — {paused_min} min paused. "
                f"I'll stay quiet on this one now."
            )
        notify_operator(
            msg,
            source="scheduler.resume-prediction",
            severity="alert",
        )


def _enqueue_notification(db, user: User, row: ResumePredictionLog, task: Task) -> None:
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
        enqueue_user_notification(user.user_id, payload)
        emit_surface_render(
            db,
            surface_id="worker.resume_prediction",
            user_id=user.user_id,
            task_id=row.task_id,
            content_snapshot=json.dumps(payload, sort_keys=True),
            content_template_id="resume_prediction",
            initiative="system",
            trigger_source="worker.resume_prediction",
            eligible_at=row.fired_at,
            rendered_at=row.fired_at,
            data_snapshot_hash=str(row.firing_id),
        )
        db.commit()
    except Exception as e:
        db.rollback()
        try:
            emit_surface_suppression(
                db,
                surface_id="worker.resume_prediction",
                user_id=user.user_id,
                task_id=row.task_id,
                suppression_reason="notification_enqueue_failed",
                content_template_id="resume_prediction",
                trigger_source="worker.resume_prediction",
                eligible_at=row.fired_at,
                suppressed_at=row.fired_at,
                generating_confidence=row.confidence,
            )
            db.commit()
        except Exception:
            db.rollback()
        logger.warning(
            f"resume_prediction: notification enqueue failed for "
            f"firing_id={row.firing_id} user_id={user.user_id}: {e}"
        )
