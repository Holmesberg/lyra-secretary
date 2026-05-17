"""Security/governance audit logging.

SecurityAuditEvent is intentionally narrow. It is not behavioral telemetry and
must not feed productivity inference, execution modeling, Cortex, clean-data
profiles, adaptive scheduling, or user behavior analysis.
"""
from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models import SecurityAuditEvent
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

REDACTED = "[redacted]"

_SENSITIVE_KEY_PARTS = (
    "access_token",
    "auth",
    "authorization",
    "body",
    "content",
    "cookie",
    "email",
    "error_context",
    "ics",
    "moodle",
    "note",
    "oauth",
    "password",
    "payload",
    "refresh",
    "secret",
    "session",
    "title",
    "token",
    "url",
    "uri",
    "user_agent",
    "wstoken",
)

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_TOKEN_PARAM_RE = re.compile(
    r"(?i)(wstoken|token|authtoken|access_token|refresh_token|key|secret)="
)


def hash_client_value(value: str | None) -> str | None:
    """Hash request-origin values so audit rows never store raw IP/UA."""
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _key_is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def _string_is_sensitive(value: str) -> bool:
    return bool(
        _EMAIL_RE.search(value)
        or _URL_RE.search(value)
        or _TOKEN_PARAM_RE.search(value)
    )


def sanitize_metadata(value: Any, *, _key: str = "") -> Any:
    """Return a JSON-safe, redacted copy of security audit metadata."""
    if _key and _key_is_sensitive(_key):
        return REDACTED

    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, str):
        if _string_is_sensitive(value):
            return REDACTED
        return value[:240]

    if isinstance(value, Mapping):
        return {
            str(key)[:80]: sanitize_metadata(item, _key=str(key))
            for key, item in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [sanitize_metadata(item) for item in list(value)[:20]]

    return repr(value)[:240]


def _request_hashes(request: Request | None) -> tuple[str | None, str | None]:
    if request is None:
        return None, None
    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return hash_client_value(client_host), hash_client_value(user_agent)


def write_security_audit_event(
    *,
    event_type: str,
    surface: str,
    status: str,
    actor_user_id: int | None = None,
    user_id: int | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    redacted_metadata: dict[str, Any] | None = None,
    request: Request | None = None,
    db: Session | None = None,
) -> None:
    """Best-effort append-only audit write.

    If a request-scoped session is supplied, the event is committed there so
    test harnesses and runtime code share the same database binding. Otherwise
    a short-lived SessionLocal is used. Failures are logged and never weaken
    authentication, authorization, or user scoping.
    """
    ip_hash, user_agent_hash = _request_hashes(request)
    event = SecurityAuditEvent(
        actor_user_id=actor_user_id,
        user_id=user_id,
        event_type=event_type[:80],
        surface=surface[:160],
        target_type=target_type[:80] if target_type else None,
        target_id=target_id[:160] if target_id else None,
        status=status[:32],
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
        redacted_metadata=sanitize_metadata(redacted_metadata or {}),
    )

    owns_session = db is None
    session = db or SessionLocal()
    try:
        session.add(event)
        session.commit()
    except Exception as exc:  # noqa: BLE001 - audit must never break request flow
        session.rollback()
        logger.warning("security audit write failed: %s", exc)
    finally:
        if owns_session:
            session.close()


def audit_user_target(user_id: int) -> str:
    """Stable non-reversible target id for account governance events."""
    return "user:" + hashlib.sha256(f"lyra-security-audit:{user_id}".encode()).hexdigest()[:16]
