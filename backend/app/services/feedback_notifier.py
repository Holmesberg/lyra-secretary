"""Feedback notification fan-out - email + OpenClaw operator channel.

Operator gets a notification on every feedback submission. Email via Resend
is the primary channel when configured; OpenClaw operator alerts are secondary.
Either failure is non-fatal - the feedback row commits regardless.

Configuration:
  RESEND_API_KEY       - Resend API key. If absent, email is skipped.
  OPERATOR_EMAIL       - recipient for feedback emails.
  FEEDBACK_FROM_EMAIL  - sender address. Defaults to hello@barzakh.app.
"""
import logging
from typing import Optional

from app.core.config import settings
from app.services.email_delivery import send_resend_email
from app.services.operator_notifier import notify_operator as notify_operator_channel

logger = logging.getLogger(__name__)


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
    subject = f"[Barzakh feedback - {kind}] {body[:60].strip()}"
    if len(body) > 60:
        subject = subject[:75] + "..."

    lines = [
        f"New {kind} from Barzakh alpha:",
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
    lines.append("Triage at: https://api.barzakh.app/v1/admin/feedback")
    return subject, "\n".join(lines)


def _send_email_resend(*, subject: str, text: str, to: str) -> bool:
    """Send via Resend HTTP API. Returns True on success."""
    return send_resend_email(to=to, subject=subject, text=text).sent


def _send_operator_channel(text: str) -> bool:
    """Queue via the centralized OpenClaw operator channel."""
    try:
        return notify_operator_channel(
            text,
            source="feedback.alpha",
            severity="alert",
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "feedback_notifier: OpenClaw operator alert failed: %s",
            type(e).__name__,
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
    """Fan out to email + OpenClaw. Returns delivery status per channel."""
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
    operator_channel_ok = _send_operator_channel(text)
    return {"email": email_ok, "operator_channel": operator_channel_ok}
