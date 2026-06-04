"""Notification polling endpoints - per-user scoped."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, operator_user_from_scope
from app.db.scoping import get_current_user_id
from app.services.notification_queue import (
    ack_user_notifications,
    drain_user_notifications,
    enqueue_user_notification,
    peek_user_notifications,
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
def get_pending(
    request: Request,
    channel: Literal["openclaw", "web"] | None = None,
):
    """Legacy route; new callers must use explicit web/openclaw endpoints."""
    uid = _require_explicit_identity(request)
    if channel is None:
        raise HTTPException(
            status_code=400,
            detail="notification channel required; use /web/pending or /openclaw/pending",
        )
    if channel == "web":
        items = peek_user_notifications(uid, channel="web")
    else:
        items = drain_user_notifications(uid, channel="openclaw")
    return {"notifications": items, "count": len(items)}


@router.get("/web/pending")
def get_web_pending(request: Request):
    """Peek web-safe notifications without draining operator payloads."""
    uid = _require_explicit_identity(request)
    items = peek_user_notifications(uid, channel="web")
    return {"notifications": items, "count": len(items)}


class WebNotificationAckRequest(BaseModel):
    notification_ids: list[str] = Field(default_factory=list)


@router.post("/web/ack")
def ack_web_pending(payload: WebNotificationAckRequest, request: Request):
    """Acknowledge web notifications after render/dismiss/action."""
    uid = _require_explicit_identity(request)
    removed = ack_user_notifications(uid, payload.notification_ids)
    return {"acknowledged": removed}


@router.get("/openclaw/pending")
def get_openclaw_pending(request: Request):
    """Drain notifications for the OpenClaw/operator delivery channel."""
    uid = _require_explicit_identity(request)
    items = drain_user_notifications(uid, channel="openclaw")
    return {"notifications": items, "count": len(items)}


# ---------------------------------------------------------------------------
# Operator-only OpenClaw channel mirror (2026-04-30)
# ---------------------------------------------------------------------------


class OperatorNotifyRequest(BaseModel):
    """Frontend-driven OpenClaw operator-channel payload."""

    message: str = Field(..., min_length=1, max_length=2000)
    severity: Literal["info", "warn", "error", "alert"] = "info"
    source: str = Field("frontend", max_length=64)


@router.post("/operator")
def post_operator_notification(
    payload: OperatorNotifyRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Mirror a frontend signal into the OpenClaw operator channel."""
    operator_user_from_scope(db, request=request)
    sent = notify_operator(
        payload.message,
        source=payload.source,
        severity=payload.severity,
    )
    return {"sent": sent}
