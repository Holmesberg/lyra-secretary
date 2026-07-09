"""Durable lifecycle tracking for user-facing notifications.

Redis is the delivery queue. This table-backed service is the measurement
boundary: it records whether a notification was queued, reserved by the web
client, actually rendered, acted on, dismissed, expired, or lost before render.
"""
from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Iterable, Literal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import NotificationLifecycleEvent
from app.services.output_surfaces import render_existing_surface_decision
from app.utils.time_utils import now_utc, strip_tz

NotificationLifecycleStatus = Literal[
    "queued",
    "reserved",
    "rendered",
    "acted",
    "dismissed",
    "expired",
    "lost_unrendered",
]

_STATUS_RANK = {
    "queued": 1,
    "reserved": 2,
    "rendered": 3,
    "acted": 4,
    "dismissed": 4,
    "expired": 4,
    "lost_unrendered": 4,
}

_TIMESTAMP_FIELD = {
    "reserved": "reserved_at",
    "rendered": "rendered_at",
    "acted": "acted_at",
    "dismissed": "dismissed_at",
    "expired": "expired_at",
    "lost_unrendered": "lost_unrendered_at",
}


def payload_hash(payload: dict[str, Any]) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _bounded_lifecycle_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= 36:
        return text
    return f"hash:{sha256(text.encode('utf-8')).hexdigest()[:16]}"


def notification_type(payload: dict[str, Any]) -> str:
    raw = payload.get("type") or "unknown"
    return str(raw)[:80]


def notification_dedupe_key(payload: dict[str, Any]) -> str:
    explicit = payload.get("dedupe_key")
    if explicit:
        return str(explicit)[:200]
    parts = [
        notification_type(payload),
        str(payload.get("task_id") or ""),
        str(payload.get("session_id") or ""),
        str(payload.get("firing_id") or ""),
    ]
    if any(parts[1:]):
        return ":".join(parts)[:200]
    return f"{parts[0]}:{payload_hash(payload)[:16]}"


def notification_content_snapshot(payload: dict[str, Any]) -> str:
    for key in ("message", "body", "title", "description"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return json.dumps(
        {
            "type": payload.get("type"),
            "task_id": payload.get("task_id"),
            "session_id": payload.get("session_id"),
            "firing_id": payload.get("firing_id"),
        },
        sort_keys=True,
        default=str,
    )


def ensure_notification_queued(
    db: Session,
    *,
    user_id: int,
    payload: dict[str, Any],
    channel: str = "web",
    surface_id: str | None = None,
    exposure_id: str | None = None,
    dedupe_key: str | None = None,
    content_snapshot: str | None = None,
    queued_at=None,
) -> NotificationLifecycleEvent:
    queued_at = strip_tz(queued_at or now_utc())
    notification_id = str(payload.get("notification_id") or str(uuid4()))
    payload["notification_id"] = notification_id

    row = (
        db.query(NotificationLifecycleEvent)
        .filter(
            NotificationLifecycleEvent.user_id == int(user_id),
            NotificationLifecycleEvent.notification_id == notification_id,
            NotificationLifecycleEvent.channel == channel,
        )
        .first()
    )
    if row is None:
        row = NotificationLifecycleEvent(
            user_id=int(user_id),
            notification_id=notification_id,
            channel=channel,
            notification_type=notification_type(payload),
            status="queued",
            dedupe_key=dedupe_key or notification_dedupe_key(payload),
            payload_hash=payload_hash(payload),
            content_snapshot=content_snapshot or notification_content_snapshot(payload),
            surface_id=surface_id or payload.get("surface_id"),
            exposure_id=exposure_id or payload.get("exposure_id"),
            task_id=_bounded_lifecycle_id(payload.get("task_id")),
            session_id=_bounded_lifecycle_id(payload.get("session_id")),
            firing_id=_bounded_lifecycle_id(payload.get("firing_id")),
            queued_at=queued_at,
            last_transition_at=queued_at,
            created_at=queued_at,
        )
        db.add(row)
        db.flush()
        return row

    row.notification_type = notification_type(payload)
    row.dedupe_key = row.dedupe_key or dedupe_key or notification_dedupe_key(payload)
    row.payload_hash = payload_hash(payload)
    row.content_snapshot = row.content_snapshot or content_snapshot or notification_content_snapshot(payload)
    row.surface_id = row.surface_id or surface_id or payload.get("surface_id")
    row.exposure_id = row.exposure_id or exposure_id or payload.get("exposure_id")
    row.task_id = row.task_id or _bounded_lifecycle_id(payload.get("task_id"))
    row.session_id = row.session_id or _bounded_lifecycle_id(payload.get("session_id"))
    row.firing_id = row.firing_id or _bounded_lifecycle_id(payload.get("firing_id"))
    db.flush()
    return row


def reserve_notifications(
    db: Session,
    *,
    user_id: int,
    payloads: Iterable[dict[str, Any]],
    channel: str = "web",
) -> int:
    rows = [
        ensure_notification_queued(
            db,
            user_id=user_id,
            payload=payload,
            channel=channel,
        )
        for payload in payloads
    ]
    return _transition_rows(db, rows=rows, status="reserved")


def transition_notifications(
    db: Session,
    *,
    user_id: int,
    notification_ids: Iterable[str],
    status: NotificationLifecycleStatus,
    channel: str = "web",
) -> int:
    ids = [str(notification_id) for notification_id in notification_ids if notification_id]
    if not ids:
        return 0
    rows = (
        db.query(NotificationLifecycleEvent)
        .filter(
            NotificationLifecycleEvent.user_id == int(user_id),
            NotificationLifecycleEvent.channel == channel,
            NotificationLifecycleEvent.notification_id.in_(ids),
        )
        .all()
    )
    return _transition_rows(db, rows=rows, status=status)


def _transition_rows(
    db: Session,
    *,
    rows: Iterable[NotificationLifecycleEvent],
    status: NotificationLifecycleStatus,
) -> int:
    now = strip_tz(now_utc())
    changed = 0
    for row in rows:
        if _STATUS_RANK.get(status, 0) < _STATUS_RANK.get(row.status, 0):
            continue
        timestamp_field = _TIMESTAMP_FIELD.get(status)
        if timestamp_field and getattr(row, timestamp_field) is None:
            setattr(row, timestamp_field, now)
        if status == "rendered":
            _record_render_for_notification(db, row=row, rendered_at=now)
        row.status = status
        row.last_transition_at = now
        changed += 1
    if changed:
        db.flush()
    return changed


def _record_render_for_notification(
    db: Session,
    *,
    row: NotificationLifecycleEvent,
    rendered_at,
) -> None:
    if not row.exposure_id or not row.surface_id:
        return
    render_existing_surface_decision(
        db,
        exposure_id=row.exposure_id,
        user_id=row.user_id,
        surface_id=row.surface_id,
        content_snapshot=row.content_snapshot or row.notification_type,
        rendered_at=strip_tz(rendered_at),
        client_event_id=f"notification:{row.notification_id}",
    )
