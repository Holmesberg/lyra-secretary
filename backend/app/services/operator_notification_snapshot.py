"""Read-only Redis pending-notification snapshot for the operator dashboard."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any, Callable

from app.utils.redis_client import RedisClient

FORBIDDEN_WEB_MARKERS = (
    "[warn]",
    "[alert]",
    "calendar.sync",
    "affected provider/subsystem",
    "reply with",
    "operator",
    "openclaw",
)


def short_hash(value: str | None) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:12]


def redis_notification_snapshot(
    user_ids: list[int],
    *,
    redis_client_factory: Callable[[], RedisClient] = RedisClient,
) -> dict[str, Any]:
    """Best-effort current queue snapshot; Redis is not the lifecycle ledger."""
    counts = {
        "web_queued": 0,
        "operator_pending": 0,
        "duplicate_prompt_count": 0,
        "internal_copy_leak_count": 0,
    }
    duplicate_breakdown: list[dict[str, Any]] = []
    duplicate_type_counts: Counter[str] = Counter()
    errors: list[str] = []

    def duplicate_identity(payload: dict[str, Any]) -> tuple[str, str, str, str, str]:
        """Privacy-safe identity for detecting repeated pending prompts.

        Canonical notifications should carry a dedupe key or stable target id.
        Older Redis payloads sometimes have only type/message/notification_id;
        for those, compare by content fingerprint so distinct legacy reminders
        do not collapse into one false duplicate bucket.
        """
        payload_type = str(payload.get("type") or "unknown")
        dedupe_key = str(payload.get("dedupe_key") or "")
        task_id = str(payload.get("task_id") or "")
        session_id = str(payload.get("session_id") or "")
        firing_id = str(payload.get("firing_id") or "")
        if dedupe_key:
            return (payload_type, "dedupe", dedupe_key, "", "")
        if task_id or session_id or firing_id:
            return (
                payload_type,
                "target",
                task_id,
                session_id,
                firing_id,
            )

        content_basis = {
            "type": payload_type,
            "message": payload.get("message") or "",
            "body": payload.get("body") or "",
            "title": payload.get("title") or "",
            "description": payload.get("description") or "",
        }
        if not any(value for key, value in content_basis.items() if key != "type"):
            content_basis = {
                key: value
                for key, value in payload.items()
                if key not in {"notification_id", "exposure_id"}
            }
        return (
            payload_type,
            "legacy_content",
            short_hash(json.dumps(content_basis, sort_keys=True, default=str)),
            "",
            "",
        )

    try:
        redis = redis_client_factory()
        for user_id in user_ids:
            key = f"notifications:pending:{int(user_id)}"
            seen = Counter()
            examples: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
            for raw in redis.client.lrange(key, 0, -1):
                try:
                    payload = json.loads(raw)
                except Exception:
                    continue
                payload_type = str(payload.get("type") or "unknown")
                body = " ".join(
                    str(payload.get(k) or "")
                    for k in ("message", "body", "title", "description")
                ).lower()
                stable_key = duplicate_identity(payload)
                seen[stable_key] += 1
                if len(examples[stable_key]) < 3:
                    examples[stable_key].append({
                        "notification_id_hash": short_hash(
                            str(payload.get("notification_id") or "")
                        ),
                        "has_message": bool(payload.get("message")),
                        "field_count": len(payload.keys()),
                    })
                if payload_type == "operator_alert":
                    counts["operator_pending"] += 1
                else:
                    counts["web_queued"] += 1
                    if any(marker in body for marker in FORBIDDEN_WEB_MARKERS):
                        counts["internal_copy_leak_count"] += 1
            for stable_key, count in seen.items():
                if count <= 1:
                    continue
                duplicate_count = count - 1
                payload_type, identity_source, identity_value, session_id, firing_id = stable_key
                task_id = identity_value if identity_source == "target" else ""
                duplicate_type_counts[payload_type] += duplicate_count
                duplicate_breakdown.append({
                    "source": "redis_pending",
                    "type": payload_type,
                    "identity_source": identity_source,
                    "user_hash": short_hash(str(user_id)),
                    "task_hash": short_hash(task_id) if task_id else "",
                    "session_hash": short_hash(session_id) if session_id else "",
                    "firing_hash": short_hash(firing_id) if firing_id else "",
                    "count": duplicate_count,
                    "has_stable_target": identity_source in {"dedupe", "target"},
                    "examples": examples[stable_key],
                })
        counts["duplicate_prompt_count"] = sum(duplicate_type_counts.values())
    except Exception as exc:  # noqa: BLE001 - dashboard should degrade.
        errors.append(type(exc).__name__)
    return {
        "counts": counts,
        "errors": errors,
        "duplicate_breakdown": duplicate_breakdown,
        "duplicate_type_counts": dict(sorted(duplicate_type_counts.items())),
    }