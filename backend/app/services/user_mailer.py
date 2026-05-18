"""Transactional user email delivery.

This module is intentionally narrow. Activation emails are account
infrastructure, not behavioral telemetry, lifecycle marketing, or adaptive
intervention. Do not import this service from Cortex, analytics inference,
clean-data profiles, adaptive scheduling, or worker recommendation paths.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

import requests

from app.core.config import settings
from app.db.models import User
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_SUCCESS_STATUSES = {200, 201, 202}


@dataclass(frozen=True)
class ActivationEmailResult:
    status: str
    sent: bool
    error: str | None = None


def activation_email_text(*, frontend_url: str) -> str:
    """Plaintext activation email body with no behavioral content."""
    sign_in_url = frontend_url.rstrip("/") or "https://lyraos.org"
    return "\n".join(
        [
            "Welcome to LyraOS.",
            "",
            "Your account is active. Sign in here:",
            sign_in_url,
            "",
            "From Settings, you can export your account data or delete your account.",
            "",
            "LyraOS",
        ]
    )


def _redacted_request_error(exc: BaseException) -> str:
    if isinstance(exc, requests.Timeout):
        return "timeout"
    return "request_failed"


def send_activation_email(user: User) -> ActivationEmailResult:
    """Send the one-time activation email through Resend.

    Delivery is best-effort. The caller should never let this result weaken or
    block authentication.
    """
    if not getattr(settings, "USER_EMAIL_ENABLED", False):
        return ActivationEmailResult(status="skipped_disabled", sent=False)

    api_key = getattr(settings, "RESEND_API_KEY", "") or ""
    if not api_key:
        return ActivationEmailResult(status="skipped_unconfigured", sent=False)

    sender_email = getattr(settings, "USER_EMAIL_FROM", "") or "hello@lyraos.org"
    frontend_url = getattr(settings, "FRONTEND_URL", "") or "https://lyraos.org"
    payload = {
        "from": f"LyraOS <{sender_email}>",
        "to": [user.email],
        "subject": "Welcome to LyraOS",
        "text": activation_email_text(frontend_url=frontend_url),
    }

    try:
        response = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=8,
        )
    except Exception as exc:  # noqa: BLE001 - mail must never block auth
        error = _redacted_request_error(exc)
        logger.warning("activation email send failed: %s", error)
        return ActivationEmailResult(status="failed", sent=False, error=error)

    if response.status_code in RESEND_SUCCESS_STATUSES:
        return ActivationEmailResult(status="sent", sent=True)

    error = f"http_{response.status_code}"
    logger.warning("activation email provider returned %s", error)
    return ActivationEmailResult(status="failed", sent=False, error=error)


def record_activation_email_result(user_id: int, result: ActivationEmailResult) -> None:
    """Persist activation email status in a separate best-effort transaction."""
    if result.status.startswith("skipped"):
        return

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user is None:
            return
        now = datetime.utcnow()
        if result.sent:
            user.activation_email_sent_at = now
            user.activation_email_last_error = None
        else:
            user.activation_email_failed_at = now
            user.activation_email_last_error = (result.error or "failed")[:80]
        db.commit()
    except Exception as exc:  # noqa: BLE001 - status write must not block auth
        db.rollback()
        logger.warning("activation email status write failed: %s", type(exc).__name__)
    finally:
        db.close()
