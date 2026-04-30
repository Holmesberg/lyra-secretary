"""Notification polling endpoints — per-user scoped."""
import json
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import User
from app.db.scoping import get_current_user_id
from app.services.operator_notifier import notify_operator
from app.utils.redis_client import RedisClient

router = APIRouter()


def _user_id_from_request(request: Request) -> str:
    """Extract user_id from X-User-Id header, default to '1' (operator)."""
    raw = request.headers.get("X-User-Id")
    if raw is not None:
        try:
            return str(int(raw))
        except ValueError:
            pass
    return "1"


@router.post("/push")
def push_notification(payload: dict, request: Request):
    """Backend scheduler pushes notifications here.

    Notifications are per-user: the key is namespaced to the user_id from
    X-User-Id (set by the scheduler's httpx.post call, which forwards it).
    """
    redis = RedisClient()
    uid = _user_id_from_request(request)
    redis.client.rpush(f"notifications:pending:{uid}", json.dumps(payload))
    return {"queued": True}


@router.get("/pending")
def get_pending(request: Request):
    """OpenClaw polls this to get pending notifications for the current user."""
    redis = RedisClient()
    uid = _user_id_from_request(request)
    key = f"notifications:pending:{uid}"
    items = []
    while True:
        item = redis.client.lpop(key)
        if not item:
            break
        items.append(json.loads(item))
    return {"notifications": items, "count": len(items)}


# ---------------------------------------------------------------------------
# Operator-only Telegram mirror (2026-04-30)
# ---------------------------------------------------------------------------


class OperatorNotifyRequest(BaseModel):
    """Frontend-driven Telegram mirror payload.

    Frontend toasts/errors/critical-state-changes call this endpoint
    (operator-only) so the OpenClaw Telegram chat sees the same signal
    the in-browser UI does. Per operator request 2026-04-30 — "make
    all notifications, toasts, nudges, ALL go through my telegram
    openclaw bot."
    """
    message: str = Field(..., min_length=1, max_length=2000)
    severity: Literal["info", "warn", "error", "alert"] = "info"
    source: str = Field("frontend", max_length=64)


@router.post("/operator")
def post_operator_notification(
    payload: OperatorNotifyRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Mirror a frontend signal into the operator's Telegram.

    Operator-only — 403 to non-operators. The endpoint is deliberately
    non-blocking on telegram delivery failures (notify_operator returns
    False but doesn't raise) so the UI never crashes when telegram is
    down or rate-limited.
    """
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    user = db.query(User).filter(User.user_id == uid).first()
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    if not user.is_operator:
        raise HTTPException(status_code=403, detail="operator only")
    sent = notify_operator(
        payload.message,
        source=payload.source,
        severity=payload.severity,
    )
    return {"sent": sent}
