"""Notification polling endpoints."""
from fastapi import APIRouter
from app.utils.redis_client import RedisClient
import json

router = APIRouter()

@router.post("/push")
def push_notification(payload: dict):
    """Backend scheduler pushes notifications here."""
    redis = RedisClient()
    # Assuming redis.client is a strictly synchronous minimal wrapper or redis.Redis instance
    redis.client.rpush("notifications:pending", json.dumps(payload))
    return {"queued": True}

@router.get("/pending")
def get_pending():
    """OpenClaw polls this to get pending notifications."""
    redis = RedisClient()
    items = []
    while True:
        item = redis.client.lpop("notifications:pending")
        if not item:
            break
        items.append(json.loads(item))
    return {"notifications": items, "count": len(items)}
