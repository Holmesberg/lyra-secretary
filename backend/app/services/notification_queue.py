"""Shared internal queue for per-user notifications.

Workers should enqueue directly here instead of making self-HTTP calls back
into /v1/notifications/push. That keeps delivery inside the same trust
boundary as the scheduler/user scope contract.
"""
from __future__ import annotations

import json
from typing import Any

from app.utils.redis_client import RedisClient


def enqueue_user_notification(user_id: int, payload: dict[str, Any]) -> None:
    redis = RedisClient()
    redis.client.rpush(
        f"notifications:pending:{int(user_id)}",
        json.dumps(payload),
    )


def drain_user_notifications(user_id: int) -> list[dict[str, Any]]:
    redis = RedisClient()
    key = f"notifications:pending:{int(user_id)}"
    items: list[dict[str, Any]] = []
    while True:
        item = redis.client.lpop(key)
        if not item:
            break
        items.append(json.loads(item))
    return items
