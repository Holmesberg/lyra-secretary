"""Notification polling endpoints - per-user scoped."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, operator_user_from_scope
from app.db.scoping import get_current_user_id
from app.services.notification_queue import (
    drain_user_notifications,
    enqueue_user_notification,
)
from app.services.operator_notifier import notify_operator

router = APIRouter()


def _require_explicit_identity(request: Request) -> int:
    """Notifications must never silently fall back to operator scope."""
    has_bearer = bool(
        (request.headers.get("Authorization") or request.headers.get("authorization"))
    )
    has_x_user = request.headers.get("X-User-Id") is not None
    if not has_bearer and not has_x_user:
        raise HTTPException(status_code=401, detail="explicit identity required")
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return uid


@router.post("/push")
def push_notification(payload: dict, request: Request):
    """Legacy HTTP bridge for per-user notification enqueue."""
    uid = _require_explicit_identity(request)
    enqueue_user_notification(uid, payload)
    return {"queued": True}


@router.get("/pending")
def get_pending(request: Request):
    """OpenClaw polls this to get pending notifications for the current user."""
    uid = _require_explicit_identity(request)
    items = drain_user_notifications(uid)
    return {"notifications": items, "count": len(items)}


# ---------------------------------------------------------------------------
# Operator-only Telegram mirror (2026-04-30)
# ---------------------------------------------------------------------------


class OperatorNotifyRequest(BaseModel):
    """Frontend-driven Telegram mirror payload."""

    message: str = Field(..., min_length=1, max_length=2000)
    severity: Literal["info", "warn", "error", "alert"] = "info"
    source: str = Field("frontend", max_length=64)


@router.post("/operator")
def post_operator_notification(
    payload: OperatorNotifyRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Mirror a frontend signal into the operator's Telegram."""
    operator_user_from_scope(db, request=request)
    sent = notify_operator(
        payload.message,
        source=payload.source,
        severity=payload.severity,
    )
    return {"sent": sent}
