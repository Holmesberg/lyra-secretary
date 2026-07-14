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
from uuid import uuid4
from typing import Any

from app.core.config import settings
from app.services.notification_lifecycle import (
    ensure_notification_queued,
    non_deliverable_notification_ids,
    reserve_notifications,
    transition_notifications,
)
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


def enqueue_user_notification(
    user_id: int,
    payload: dict[str, Any],
    *,
    db=None,
    channel: str = "web",
    surface_id: str | None = None,
    exposure_id: str | None = None,
    dedupe_key: str | None = None,
    content_snapshot: str | None = None,
) -> None:
    payload = dict(payload)
    payload.setdefault("notification_id", str(uuid4()))
    if surface_id:
        payload.setdefault("surface_id", surface_id)
    if exposure_id:
        payload.setdefault("exposure_id", exposure_id)
    if db is not None:
        ensure_notification_queued(
            db,
            user_id=int(user_id),
            payload=payload,
            channel=channel,
            surface_id=surface_id,
            exposure_id=exposure_id,
            dedupe_key=dedupe_key,
            content_snapshot=content_snapshot,
        )
    redis = RedisClient()
    redis.client.rpush(
        f"notifications:pending:{int(user_id)}",
        json.dumps(payload, sort_keys=True),
    )
    mirror_user_notification_to_operator(int(user_id), payload)


def _queue_key(user_id: int) -> str:
    return f"notifications:pending:{int(user_id)}"


def _web_visible(payload: dict[str, Any]) -> bool:
    return payload.get("type") != "operator_alert"


def _payload_id(payload: dict[str, Any]) -> str:
    explicit = payload.get("notification_id")
    if explicit:
        return str(explicit)
    stable = json.dumps(payload, sort_keys=True, default=str)
    return f"legacy:{_short_hash(stable)}"


def remove_user_notifications(user_id: int, notification_ids: list[str]) -> int:
    """Atomically remove matching web-visible payloads from the Redis list."""
    wanted = {str(notification_id) for notification_id in notification_ids if notification_id}
    if not wanted:
        return 0
    redis = RedisClient()
    key = _queue_key(int(user_id))
    removed = 0
    for raw in list(redis.client.lrange(key, 0, -1)):
        payload = json.loads(raw)
        if _payload_id(payload) in wanted and _web_visible(payload):
            removed += int(redis.client.lrem(key, 0, raw) or 0)
    return removed


def peek_user_notifications(
    user_id: int,
    *,
    channel: str = "web",
    db=None,
) -> list[dict[str, Any]]:
    """Return pending notifications without removing them from Redis.

    Web delivery is reserve/ack shaped: the frontend fetches, renders, then
    acknowledges by notification_id. This prevents resume/pause recovery
    prompts from vanishing just because a background poll fired.
    """
    redis = RedisClient()
    items: list[dict[str, Any]] = []
    for raw in redis.client.lrange(_queue_key(int(user_id)), 0, -1):
        payload = json.loads(raw)
        if channel == "web" and not _web_visible(payload):
            continue
        payload = dict(payload)
        payload.setdefault("notification_id", _payload_id(payload))
        items.append(payload)
    if db is not None and items:
        terminal_ids = non_deliverable_notification_ids(
            db,
            user_id=int(user_id),
            notification_ids=[item["notification_id"] for item in items],
            channel=channel,
        )
        if terminal_ids:
            items = [
                item for item in items
                if str(item["notification_id"]) not in terminal_ids
            ]
            try:
                remove_user_notifications(int(user_id), list(terminal_ids))
            except Exception as exc:  # noqa: BLE001 - DB lifecycle fails closed
                logger.warning(
                    "notification_queue: terminal Redis prune failed for user %s: %s",
                    user_id,
                    type(exc).__name__,
                )
    if db is not None and items:
        reserve_notifications(
            db,
            user_id=int(user_id),
            payloads=items,
            channel=channel,
        )
    return items


def ack_user_notifications(
    user_id: int,
    notification_ids: list[str],
    *,
    db=None,
    event_type: str = "rendered",
) -> int:
    """Mark web notification lifecycle and remove terminal queue items.

    ``event_type=rendered`` means the item mounted visibly in the browser.
    ``lost_unrendered`` removes unsupported/duplicate items without claiming
    exposure. Later ``dismissed`` / ``acted`` / ``expired`` calls update the
    lifecycle row even when the Redis item was already removed at render time.
    """
    wanted = {str(nid) for nid in notification_ids if nid}
    if not wanted:
        return 0
    terminal_remove = event_type in {"rendered", "lost_unrendered", "expired"}
    if db is not None:
        transition_notifications(
            db,
            user_id=int(user_id),
            notification_ids=list(wanted),
            status=event_type,
            channel="web",
        )
    removed = 0
    if terminal_remove:
        # LREM is atomic for each payload. Rewriting the whole list lets
        # concurrent render/lost ACKs restore each other's stale copy.
        removed = remove_user_notifications(int(user_id), list(wanted))
    return removed
