"""Pause-prediction response endpoint.

Records the user's reply to a pause_prediction firing so the acceptance
window closes early and the reconcile_responses job leaves the row
alone. Valid replies: `pause_now` | `dismiss` | `snooze` (MANIFESTO
§VT-17 pre-registered).

Scoping: the before_compile hook auto-filters `db.query(PausePredictionLog)`
by the current user, so a caller cannot respond to another user's firing
— the lookup simply 404s.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import PausePredictionLog
from app.utils.time_utils import now_utc

router = APIRouter()


class RespondBody(BaseModel):
    user_response: Literal["pause_now", "dismiss", "snooze"]


@router.post("/pause_predictions/{firing_id}/respond")
def respond_to_firing(
    firing_id: str,
    body: RespondBody,
    db: Session = Depends(get_db),
) -> dict:
    """Record the user's response to a pause_prediction firing.

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
        "response_at": row.response_at.isoformat(),
    }
