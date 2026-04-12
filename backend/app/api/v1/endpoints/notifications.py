"""Notification polling endpoints — per-user scoped."""
import json
from fastapi import APIRouter, Request

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
