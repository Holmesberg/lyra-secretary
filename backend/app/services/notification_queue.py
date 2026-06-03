"""Shared internal queue for per-user notifications.

Workers should enqueue directly here instead of making self-HTTP calls back
into /v1/notifications/push. That keeps delivery inside the same trust
boundary as the scheduler/user scope contract.
"""
from __future__ import annotations

import json
import logging
import hashlib
import re
from typing import Any

from app.core.config import settings
from app.services.operator_notifier import notify_operator, redacted_user_ref
from app.utils.redis_client import RedisClient

logger = logging.getLogger(__name__)

_SENSITIVE_PAYLOAD_KEYS = {
    "body",
    "description",
    "error_context",
    "message",
    "notes",
    "page_url",
    "task_title",
    "title",
    "url",
    "user_agent",
}

_SAFE_VALUE_KEYS = {
    "type",
    "mechanism",
    "confidence",
    "lead_minutes",
    "paused_for_minutes",
    "p75_pause_minutes",
}

_ID_KEYS = {
    "active_task_id",
    "firing_id",
    "session_id",
    "task_id",
}

_SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,48}$")
_UNSAFE_VALUE_MARKERS = ("@", "http://", "https://", "token", "secret", "bearer")


def _safe_inline(value: Any, limit: int = 80) -> str:
    text = str(value).replace("`", "'").replace("\n", " ").strip()
    return text[:limit] or "unknown"


def _safe_metadata_value(value: Any) -> str:
    if isinstance(value, (int, float, bool)) or value is None:
        return _safe_inline(value, limit=40)

    text = _safe_inline(value, limit=160)
    lowered = text.lower()
    if _SAFE_TOKEN_RE.fullmatch(text) and not any(
        marker in lowered for marker in _UNSAFE_VALUE_MARKERS
    ):
        return text
    return f"#{_short_hash(text)}"


def _short_hash(value: Any) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return digest[:10]


def _payload_operator_summary(user_id: int, payload: dict[str, Any]) -> str:
    payload_type = _safe_metadata_value(payload.get("type", "unknown"))
    fields = sorted(_safe_inline(key, limit=32) for key in payload.keys())
    sensitive = sorted(
        key for key in fields if key.lower() in _SENSITIVE_PAYLOAD_KEYS
    )

    lines = [
        "User notification queued.",
        f"User: {redacted_user_ref(user_id)}",
        f"Type: `{payload_type}`",
    ]

    if fields:
        lines.append("Fields: " + ", ".join(f"`{key}`" for key in fields[:16]))
        if len(fields) > 16:
            lines.append(f"Additional fields: {len(fields) - 16}")

    safe_values: list[str] = []
    for key in sorted(_SAFE_VALUE_KEYS & payload.keys()):
        safe_values.append(f"{key}=`{_safe_metadata_value(payload[key])}`")
    for key in sorted(_ID_KEYS & payload.keys()):
        safe_values.append(f"{key}=#{_short_hash(payload[key])}")
    if safe_values:
        lines.append("Safe metadata: " + ", ".join(safe_values[:12]))

    if sensitive:
        lines.append("Content redacted: " + ", ".join(f"`{key}`" for key in sensitive))

    return "\n".join(lines)


def mirror_user_notification_to_operator(
    user_id: int, payload: dict[str, Any]
) -> bool:
    """Mirror user-notification events to OpenClaw as redacted metadata.

    This is observability, not a second delivery channel. The actual user-facing
    notification remains the per-user Redis queue. OpenClaw receives only enough
    metadata for the operator to notice which notification surfaces are firing.
    """
    if not getattr(settings, "OPENCLAW_MIRROR_USER_NOTIFICATIONS", True):
        return False
    if int(user_id) == int(getattr(settings, "OPENCLAW_OPERATOR_USER_ID", 1)):
        return False
    try:
        return notify_operator(
            _payload_operator_summary(user_id, payload),
            source="user.notification-queue",
            severity="info",
        )
    except Exception as exc:  # noqa: BLE001 - mirror must never block queueing
        logger.warning(
            "notification_queue: operator mirror failed: %s",
            type(exc).__name__,
        )
        return False


def enqueue_user_notification(user_id: int, payload: dict[str, Any]) -> None:
    redis = RedisClient()
    redis.client.rpush(
        f"notifications:pending:{int(user_id)}",
        json.dumps(payload),
    )
    mirror_user_notification_to_operator(int(user_id), payload)


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
