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

from app.core.config import settings
from app.db.models import User
from app.db.session import SessionLocal
from app.services.email_delivery import EmailSendResult, send_resend_email

logger = logging.getLogger(__name__)

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


def send_activation_email(user: User) -> ActivationEmailResult:
    """Send the one-time activation email through Resend.

    Delivery is best-effort. The caller should never let this result weaken or
    block authentication.
    """
    if not getattr(settings, "USER_EMAIL_ENABLED", False):
        return ActivationEmailResult(status="skipped_disabled", sent=False)

    frontend_url = getattr(settings, "FRONTEND_URL", "") or "https://lyraos.org"
    result: EmailSendResult = send_resend_email(
        to=user.email,
        subject="Welcome to LyraOS",
        text=activation_email_text(frontend_url=frontend_url),
    )
    return ActivationEmailResult(
        status=result.status,
        sent=result.sent,
        error=result.error,
    )


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
