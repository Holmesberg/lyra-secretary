"""Shared outbound email delivery.

All LyraOS email must use the same sender identity. This module is the single
Resend HTTP boundary so future emails do not drift back to provider defaults or
test senders.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

LYRAOS_OUTBOUND_EMAIL = "hello@lyraos.org"
LYRAOS_FROM_HEADER = f"LyraOS <{LYRAOS_OUTBOUND_EMAIL}>"
LYRAOS_USER_AGENT = "lyraos-email/1.0"
RESEND_API_URL = "https://api.resend.com/emails"
RESEND_SUCCESS_STATUSES = {200, 201, 202}


@dataclass(frozen=True)
class EmailSendResult:
    status: str
    sent: bool
    error: str | None = None


def _redacted_request_error(exc: BaseException) -> str:
    if isinstance(exc, requests.Timeout):
        return "timeout"
    return "request_failed"


def _redacted_provider_error(response: requests.Response) -> str:
    """Return a short provider error without leaking secrets/tokens."""
    detail = ""
    try:
        data = response.json()
        if isinstance(data, dict):
            for key in ("message", "error", "name"):
                value = data.get(key)
                if value:
                    detail = str(value)
                    break
    except Exception:  # noqa: BLE001 - best-effort diagnostics only
        detail = getattr(response, "text", "") or ""

    detail = " ".join(detail.split())[:180]
    if not detail:
        return f"http_{response.status_code}"
    lowered = detail.lower()
    if any(token in lowered for token in ("secret", "api key", "bearer", "token")):
        return f"http_{response.status_code}:provider_error_redacted"
    return f"http_{response.status_code}:{detail}"


def send_resend_email(
    *,
    to: str,
    subject: str,
    text: str,
    html: Optional[str] = None,
    scheduled_at: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    timeout: float = 8,
) -> EmailSendResult:
    """Send one email through Resend.

    `from` is intentionally not configurable. If the sender ever needs to
    change, change LYRAOS_OUTBOUND_EMAIL here and update the invariant tests.
    """
    api_key = getattr(settings, "RESEND_API_KEY", "") or ""
    if not api_key:
        return EmailSendResult(status="skipped_unconfigured", sent=False)

    payload: dict[str, object] = {
        "from": LYRAOS_FROM_HEADER,
        "to": [to],
        "subject": subject,
        "text": text,
    }
    if html:
        payload["html"] = html
    if scheduled_at:
        payload["scheduled_at"] = scheduled_at

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": LYRAOS_USER_AGENT,
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    try:
        response = requests.post(
            RESEND_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001 - email must never block app flows
        error = _redacted_request_error(exc)
        logger.warning("email send failed: %s", error)
        return EmailSendResult(status="failed", sent=False, error=error)

    if response.status_code in RESEND_SUCCESS_STATUSES:
        return EmailSendResult(status="sent", sent=True)

    error = _redacted_provider_error(response)
    logger.warning("email provider returned %s", error)
    return EmailSendResult(status="failed", sent=False, error=error)
