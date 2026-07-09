"""Pause-prediction response endpoints.

Three surfaces:

  1. POST /pause_predictions/{firing_id}/respond — in-the-moment
     response (pause_now | dismiss | snooze). Fires while the
     prediction banner is visible.

  2. POST /pause_predictions/{firing_id}/confirm — retroactive
     confirmation (yes | no). Only valid after reconciliation stamped
     user_response='no_response'. Closes the "operator paused for
     food but forgot to log it in LyraOS" gap. On 'yes', creates a
     pause_event with self_reported_retroactively=true (alembic 030).
     See MANIFESTO v1.9 §VT-17d for the stratified-analysis
     pre-registration.

  3. GET /pause_predictions/pending-confirmation — firings that need
     the retroactive chip. Applies the ±10 min chip-suppression
     gate: if any pause_event exists within [predicted_at − 10,
     predicted_at + 10], the firing is NOT returned (the operator
     paused close enough that asking would be patronizing). This
     UX gate is wider than the VT-17 acceptance window and is
     deliberately separate — VT-17 scoring stays frozen.

Scoping: the before_compile hook auto-filters `db.query(PausePredictionLog)`
by the current user, so a caller cannot respond to another user's firing.
"""
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import PauseEvent, PausePredictionLog
from app.db.scoping import get_current_user_id
from app.utils.time_utils import now_utc


def _utc_iso(dt: datetime) -> str:
    """Serialize a datetime as an unambiguous UTC ISO string.

    DB stores pause_prediction_log timestamps as naive UTC. If we emit
    `.isoformat()` without a timezone marker, browsers parse the string
    as LOCAL time (ECMA-262) and the UTC→user-tz conversion never
    happens — the chip then renders 13:37 UTC as "1:37 PM Cairo" when
    it should be "3:37 PM Cairo". Stamping `+00:00` restores the round-trip.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

router = APIRouter()

# Chip-suppression window. Pauses within ±CHIP_SUPPRESSION_MIN of
# predicted_at hide the chip — see endpoint 3 docstring. This is a
# UX-only setting, not a research threshold.
CHIP_SUPPRESSION_MIN = 10

# Freshness window for showing the chip. 24h captures the "morning
# break → evening check" pattern the operator flagged 2026-04-22.
# Longer risks chip clutter with stale firings; shorter misses the
# operator's realistic re-engagement cadence.
CHIP_FRESHNESS_HOURS = 24


class RespondBody(BaseModel):
    user_response: Literal["pause_now", "dismiss", "snooze"]


@router.post("/pause_predictions/{firing_id}/respond")
def respond_to_firing(
    firing_id: str,
    body: RespondBody,
    db: Session = Depends(get_db),
) -> dict:
    """Record the user's in-the-moment response to a pause_prediction firing.

    Returns 404 if the firing_id does not belong to the caller (the
    scoping hook filters it out) or does not exist.
    Returns 409 if the row is already reconciled — the pre-registration
    forbids revisiting a closed window, so the second call is rejected
    rather than silently overwriting.
    """
    row = (
        db.query(PausePredictionLog)
        .filter(PausePredictionLog.firing_id == firing_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="firing_id not found")
    if row.user_response is not None:
        raise HTTPException(
            status_code=409,
            detail=f"firing already reconciled as '{row.user_response}'",
        )

    row.user_response = body.user_response
    row.response_at = now_utc()
    db.commit()
    db.refresh(row)

    return {
        "firing_id": row.firing_id,
        "user_response": row.user_response,
        "response_at": _utc_iso(row.response_at),
    }


class ConfirmBody(BaseModel):
    outcome: Literal["yes", "no"]


@router.post("/pause_predictions/{firing_id}/confirm")
def confirm_retroactive(
    firing_id: str,
    body: ConfirmBody,
    db: Session = Depends(get_db),
) -> dict:
    """Retroactively confirm whether a no_response firing actually paused.

    Called from the /today retroactive chip. Only valid when the
    firing's reconciliation closed as 'no_response' — in-the-moment
    responses close the row before reconciliation and are immutable.

    On outcome='yes': create a pause_event stamped with
    self_reported_retroactively=true at the predicted time. The new
    row contributes to future clock_anchor training (predictor reads
    pause_event history) and feeds the VT-17d stratified analysis
    per MANIFESTO v1.9.

    On outcome='no': no pause_event created; the firing is re-labeled
    'self_reported_no' which is a true negative in the secondary
    acceptance-rate formula.

    Returns 404 if firing not found / not owned.
    Returns 409 if the firing is not in 'no_response' state.
    Returns 200 on success with the new pause_event id (yes) or null (no).
    """
    row = (
        db.query(PausePredictionLog)
        .filter(PausePredictionLog.firing_id == firing_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="firing_id not found")
    if row.user_response != "no_response":
        raise HTTPException(
            status_code=409,
            detail=f"only no_response firings can be confirmed retroactively (was: '{row.user_response}')",
        )

    uid = get_current_user_id()
    pause_event_id: Optional[str] = None

    if body.outcome == "yes":
        # pause_event.session_id is NOT NULL. Look for a session that
        # overlapped predicted_at. If none exists (operator had no
        # active timer when the break happened), we update the firing
        # log only and skip the pause_event — the log is still the
        # source of truth for VT-17d stratified acceptance_rate.
        # Missing pause_events is strictly better than FK violation or
        # synthetic placeholder sessions contaminating stopwatch_session.
        session_id = _find_session_for_firing(db, row)
        if session_id is not None:
            new_event = PauseEvent(
                pause_event_id=str(uuid4()),
                session_id=session_id,
                user_id=uid,
                paused_at_utc=row.predicted_at,
                resumed_at_utc=None,
                duration_minutes=None,
                # Default to intentional_break — the dominant pattern
                # for retroactive reports (food breaks per 2026-04-22
                # operator dogfood). Can be refined via edit in v2.
                pause_reason="intentional_break",
                pause_initiator="self",
                active_elapsed_at_pause_seconds=None,
                self_reported_retroactively=True,
            )
            db.add(new_event)
            db.flush()
            pause_event_id = new_event.pause_event_id
        row.user_response = "self_reported_yes"
    else:
        row.user_response = "self_reported_no"

    row.response_at = now_utc()
    db.commit()
    db.refresh(row)

    return {
        "firing_id": row.firing_id,
        "user_response": row.user_response,
        "response_at": _utc_iso(row.response_at),
        "pause_event_id": pause_event_id,
    }


def _find_session_for_firing(
    db: Session, row: PausePredictionLog
) -> Optional[str]:
    """Session_id for a retroactive pause_event, or None if no overlap.

    Looks ONLY for a session that overlapped predicted_at. We do NOT
    fall back to the nearest session — attaching a pause to an
    unrelated session contaminates that session's pause_count and
    total_paused_minutes, and produces a paused_at_utc outside the
    session's own time window. Better: return None so the endpoint
    skips pause_event creation entirely and relies on the
    pause_prediction_log row for the signal.
    """
    from app.db.models import StopwatchSession

    candidate = (
        db.query(StopwatchSession)
        .filter(StopwatchSession.user_id == row.user_id)
        .filter(StopwatchSession.start_time_utc <= row.predicted_at)
        .filter(
            (StopwatchSession.end_time_utc.is_(None))
            | (StopwatchSession.end_time_utc >= row.predicted_at)
        )
        .order_by(StopwatchSession.start_time_utc.desc())
        .first()
    )
    return candidate.session_id if candidate else None


@router.get("/pause_predictions/pending-confirmation")
def pending_confirmations(db: Session = Depends(get_db)) -> dict:
    """List firings that need the retroactive confirmation chip.

    Filters applied:
      1. user_response = 'no_response' (reconciliation closed with no
         pause matched)
      2. fired_at within the last CHIP_FRESHNESS_HOURS hours
      3. NO pause_event exists within [predicted_at − CHIP_SUPPRESSION_MIN,
         predicted_at + CHIP_SUPPRESSION_MIN] (UX gate — if the
         operator paused close enough, don't bother them)

    Ordered by fired_at DESC. Response shape is keyed by the task_id
    the firing was associated with so the frontend can locate which
    task row to render the chip on.
    """
    now = now_utc()
    cutoff = now - timedelta(hours=CHIP_FRESHNESS_HOURS)

    candidates = (
        db.query(PausePredictionLog)
        .filter(PausePredictionLog.user_response == "no_response")
        .filter(PausePredictionLog.fired_at >= cutoff)
        .order_by(PausePredictionLog.fired_at.desc())
        .all()
    )

    results = []
    for row in candidates:
        window_start = row.predicted_at - timedelta(minutes=CHIP_SUPPRESSION_MIN)
        window_end = row.predicted_at + timedelta(minutes=CHIP_SUPPRESSION_MIN)
        nearby_pause = (
            db.query(PauseEvent)
            .filter(PauseEvent.user_id == row.user_id)
            .filter(PauseEvent.paused_at_utc >= window_start)
            .filter(PauseEvent.paused_at_utc <= window_end)
            .first()
        )
        if nearby_pause is not None:
            # Chip-suppression gate — the operator paused close enough.
            continue
        results.append(
            {
                "firing_id": row.firing_id,
                "active_task_id": row.active_task_id,
                "fired_at": _utc_iso(row.fired_at),
                "predicted_at": _utc_iso(row.predicted_at),
                "mechanism": row.mechanism,
                "confidence": row.confidence,
            }
        )

    return {"pending": results}
