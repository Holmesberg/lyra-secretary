"""Operator-facing notification fan-out through OpenClaw.

Lyra does not own a separate Telegram bot. Operator notifications are queued
into the same per-user Redis notification path that OpenClaw already polls,
then OpenClaw relays them through its existing Telegram runtime.
"""
from __future__ import annotations

import hashlib
import json
import logging
from time import monotonic
from typing import Literal

from app.core.config import settings
from app.utils.redis_client import RedisClient
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)

Severity = Literal["info", "warn", "error", "alert"]

_PREFIX = {
    "info": "[info]",
    "warn": "[warn]",
    "error": "[error]",
    "alert": "[alert]",
}

_LAST_SENT_AT: dict[str, float] = {}


def _dedupe_key(fingerprint: str) -> str:
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
    return f"operator_alert:dedupe:{digest}"


def redacted_user_ref(user_id: int | str | None) -> str:
    """Return a stable non-PII user reference for operator alerts."""
    if user_id is None:
        return "user#unknown"
    digest = hashlib.sha256(f"lyra-alert-user:{user_id}".encode()).hexdigest()
    return f"user#{digest[:10]}"


def format_alert_context(
    *,
    affected: str,
    scope: str,
    retry: str,
    user_action: str,
    data_integrity: str,
) -> str:
    """Format the mandatory incident-triage fields for operator alerts."""
    return "\n".join(
        [
            f"Affected provider/subsystem: {affected}",
            f"Affected user scope: {scope}",
            f"Retry behavior: {retry}",
            f"User action needed: {user_action}",
            f"Data integrity risk: {data_integrity}",
        ]
    )


def _operator_queue_key() -> str:
    return f"notifications:pending:{int(settings.OPENCLAW_OPERATOR_USER_ID)}"


def _enqueue_openclaw_operator_alert(
    formatted: str,
    *,
    source: str,
    severity: Severity,
    redis: RedisClient | None = None,
) -> bool:
    """Queue an operator alert for OpenClaw to relay through Telegram."""
    if not getattr(settings, "OPENCLAW_OPERATOR_NOTIFICATIONS_ENABLED", True):
        return False

    payload = {
        "type": "operator_alert",
        "message": formatted,
        "source": source,
        "severity": severity,
        "created_at": now_utc().isoformat(),
    }
    redis = redis or RedisClient()
    redis.client.rpush(_operator_queue_key(), json.dumps(payload, sort_keys=True))
    return True


def notify_operator(
    message: str,
    *,
    source: str = "system",
    severity: Severity = "info",
    dedupe_key: str | None = None,
    cooldown_seconds: int | None = None,
) -> bool:
    """Queue a structured notification for the OpenClaw operator bot.

    Args:
      message: Body text for the operator. Keep user content redacted unless
              the event is operator-owned or intentionally user-submitted
              feedback.
      source: Short tag (e.g., "scheduler.overdue", "frontend.toast",
              "moodle.sync"). Appears in brackets after the severity marker.
      severity: One of info/warn/error/alert.
      dedupe_key: Optional stable fingerprint for repeated failures.
      cooldown_seconds: When set with dedupe_key, suppresses repeated
              notifications for this fingerprint in the current process.

    Returns: True if the OpenClaw queue write succeeded, False otherwise.
    Failures log + return False; notification delivery must never block product
    mutations or research writes.
    """
    if not getattr(settings, "OPENCLAW_OPERATOR_NOTIFICATIONS_ENABLED", True):
        logger.debug(
            "operator_notifier: OpenClaw operator notifications disabled "
            "source=%s",
            source,
        )
        return False

    fingerprint = None
    redis_dedupe_key = None
    redis_dedupe_acquired = False
    redis: RedisClient | None = None
    if dedupe_key and cooldown_seconds and cooldown_seconds > 0:
        fingerprint = f"{source}:{severity}:{dedupe_key}"
        last_sent = _LAST_SENT_AT.get(fingerprint)
        if last_sent is not None and monotonic() - last_sent < cooldown_seconds:
            logger.debug(
                "operator_notifier: suppressed duplicate notification "
                "source=%s dedupe_key=%s",
                source,
                dedupe_key,
            )
            return False

    prefix = _PREFIX.get(severity, _PREFIX["info"])
    formatted = f"{prefix} [{source}] {message}"
    try:
        if fingerprint and cooldown_seconds:
            redis = RedisClient()
            redis_dedupe_key = _dedupe_key(fingerprint)
            redis_dedupe_acquired = bool(
                redis.client.set(
                    redis_dedupe_key,
                    now_utc().isoformat(),
                    ex=cooldown_seconds,
                    nx=True,
                )
            )
            if not redis_dedupe_acquired:
                logger.debug(
                    "operator_notifier: suppressed duplicate notification "
                    "via Redis source=%s dedupe_key=%s",
                    source,
                    dedupe_key,
                )
                return False

        ok = _enqueue_openclaw_operator_alert(
            formatted,
            source=source,
            severity=severity,
            redis=redis,
        )
        if ok and fingerprint:
            _LAST_SENT_AT[fingerprint] = monotonic()
        if not ok and redis_dedupe_acquired and redis and redis_dedupe_key:
            redis.client.delete(redis_dedupe_key)
        return ok
    except Exception as e:  # noqa: BLE001 - non-fatal observation channel
        if redis_dedupe_acquired and redis and redis_dedupe_key:
            try:
                redis.client.delete(redis_dedupe_key)
            except Exception:  # noqa: BLE001 - best-effort cleanup
                pass
        logger.warning(
            "operator_notifier: unexpected error queueing OpenClaw alert: %s "
            "(source=%s)",
            type(e).__name__,
            source,
        )
        return False


def clear_operator_notification_dedupe() -> None:
    """Clear in-memory notification cooldown state for tests."""
    _LAST_SENT_AT.clear()
