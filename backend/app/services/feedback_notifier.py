"""Feedback notification fan-out — email + Telegram (both best-effort).

Operator gets a notification on every feedback submission. Email via
Resend (if RESEND_API_KEY set) is the primary channel; Telegram via the
existing bot is secondary. Either failure is non-fatal — the feedback
row commits regardless.

Configuration (backend/.env):
  RESEND_API_KEY         — Resend API key. If absent, email is skipped.
  OPERATOR_EMAIL         — recipient for feedback emails. Defaults to
                            the operator email registered in settings.
  FEEDBACK_FROM_EMAIL    — sender address. Defaults to feedback@lyraos.org
                            but Resend will reject if domain not verified;
                            fall back to onboarding@resend.dev for local
                            tests.
"""
import logging
from typing import Optional

import requests

from app.core.config import settings
from app.services.telegram_notifier import (
    _telegram_error_summary,
    send_telegram_message_sync,
)

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def _format_text(
    *,
    feedback_id: str,
    kind: str,
    body: str,
    user_email: Optional[str],
    page_url: Optional[str],
    error_context: Optional[list],
) -> tuple[str, str]:
    """Build (subject, plaintext_body) for the operator notification."""
    subject = f"[Lyra feedback · {kind}] {body[:60].strip()}"
    if len(body) > 60:
        subject = subject[:75] + "…"

    lines = [
        f"New {kind} from Lyra alpha:",
        "",
        body,
        "",
        f"User: {user_email or 'anonymous'}",
        f"Page: {page_url or 'n/a'}",
        f"Feedback ID: {feedback_id}",
    ]
    if error_context:
        lines.append("")
        lines.append("Recent errors:")
        for e in (error_context or [])[:5]:
            lines.append(f"  - {str(e)[:300]}")
    lines.append("")
    lines.append("Triage at: https://api.lyraos.org/v1/admin/feedback")
    return subject, "\n".join(lines)


def _send_email_resend(*, subject: str, text: str, to: str) -> bool:
    """Send via Resend HTTP API. Returns True on success."""
    api_key = getattr(settings, "RESEND_API_KEY", "") or ""
    if not api_key:
        return False
    sender = getattr(settings, "FEEDBACK_FROM_EMAIL", "") or "onboarding@resend.dev"
    try:
        r = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": sender,
                "to": [to],
                "subject": subject,
                "text": text,
            },
            timeout=8,
        )
        if r.status_code in (200, 201, 202):
            return True
        logger.warning(
            f"feedback_notifier: Resend returned {r.status_code}: {r.text[:200]}"
        )
        return False
    except Exception as e:  # noqa: BLE001
        logger.warning(f"feedback_notifier: Resend send failed: {e}")
        return False


def _send_telegram(text: str) -> bool:
    """Send via existing operator Telegram bot. Returns True on success."""
    try:
        send_telegram_message_sync(text)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "feedback_notifier: Telegram send failed: %s",
            _telegram_error_summary(e),
        )
        return False


def notify_operator(
    *,
    feedback_id: str,
    kind: str,
    body: str,
    user_email: Optional[str],
    page_url: Optional[str],
    error_context: Optional[list],
) -> dict[str, bool]:
    """Fan out to email + Telegram. Returns delivery status per channel.
    All failures are logged; never raises."""
    subject, text = _format_text(
        feedback_id=feedback_id,
        kind=kind,
        body=body,
        user_email=user_email,
        page_url=page_url,
        error_context=error_context,
    )
    operator_email = getattr(settings, "OPERATOR_EMAIL", "") or ""
    email_ok = (
        _send_email_resend(subject=subject, text=text, to=operator_email)
        if operator_email else False
    )
    telegram_ok = _send_telegram(text)
    return {"email": email_ok, "telegram": telegram_ok}
