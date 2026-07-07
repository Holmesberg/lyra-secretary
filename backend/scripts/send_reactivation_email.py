"""Schedule the trusted-user reactivation email.

Default behavior is operator-only dry-run. To actually schedule the operator
test email, pass `--send`. To send to the cohort, pass `--scope all --send`
after the operator test is confirmed.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.db.models import User
from app.db.session import SessionLocal
from app.services.email_delivery import BARZAKH_FROM_HEADER, send_resend_email
from app.services.email_engagement import (
    build_click_tracking_url,
    build_open_tracking_url,
)

SUBJECT = "Forgot about Barzakh?"
LANDING_URL = "https://barzakh.app"
LOGO_URL = "https://barzakh.app/barzakh-logo.png"
CAMPAIGN_VERSION = "landing-html-v7"

BODY_TEMPLATE = """Hey {first_name},

Quick one - did Barzakh slip off your radar?

Try this:

Open it and just dump whatever is currently in your head.
Tasks, deadlines, random obligations - no cleaning, no structure.

Barzakh will take that mess and turn it into:
- structured timeblocks
- linked deadlines
- visible workload pressure
- and places where your plan is already drifting without you noticing

That last one is the most important.

It's less about "organizing tasks" and more about seeing what your execution actually looks like.

No setup needed. Just dump and see what happens.

If it feels useful (or broken), reply or use the in-app feedback button - I'm actively improving it during this phase.

Please subscribe to get reminders so Barzakh can nudge you when it slips off your radar.

- Ali
Barzakh

Open Barzakh:
https://barzakh.app
"""

HTML_TEMPLATE = """\
<!doctype html>
<html>
  <body style="margin:0;background:#0d0f14;color:#e8eaf0;font-family:Inter,Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0d0f14;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#13161e;border:1px solid #252836;">
            <tr>
              <td style="padding:28px 28px 8px;">
                <img src="{logo_url}" alt="Barzakh" width="104" style="display:block;border:0;margin-bottom:24px;">
                <p style="margin:0 0 18px;font-size:16px;line-height:1.55;color:#e8eaf0;">Hey {first_name},</p>
                <p style="margin:0 0 18px;font-size:16px;line-height:1.55;color:#e8eaf0;">Quick one - did Barzakh slip off your radar?</p>
                <p style="margin:0 0 10px;font-size:16px;line-height:1.55;color:#e8eaf0;">Try this:</p>
                <p style="margin:0 0 18px;font-size:16px;line-height:1.55;color:#e8eaf0;">Open it and just dump whatever is currently in your head.<br>Tasks, deadlines, random obligations - no cleaning, no structure.</p>
                <p style="margin:0 0 10px;font-size:16px;line-height:1.55;color:#e8eaf0;">Barzakh will take that mess and turn it into:</p>
                <ul style="margin:0 0 20px 20px;padding:0;color:#c8ccda;font-size:15px;line-height:1.7;">
                  <li><strong style="color:#e8eaf0;">structured timeblocks</strong></li>
                  <li><strong style="color:#e8eaf0;">linked deadlines</strong></li>
                  <li><strong style="color:#e8eaf0;">visible workload pressure</strong></li>
                  <li>places where your plan is already <strong style="color:#e8eaf0;">drifting</strong> without you noticing</li>
                </ul>
                <p style="margin:0 0 18px;font-size:16px;line-height:1.55;color:#e8eaf0;">That last one is the most important.</p>
                <p style="margin:0 0 18px;font-size:16px;line-height:1.55;color:#e8eaf0;">It's less about "organizing tasks" and more about seeing what your execution actually looks like.</p>
                <p style="margin:0 0 18px;font-size:15px;line-height:1.55;color:#c8ccda;">No setup needed. Just dump and see what happens.</p>
                <p style="margin:0 0 24px;font-size:15px;line-height:1.55;color:#c8ccda;">If it feels useful (or broken), reply or use the in-app feedback button - I'm actively improving it during this phase.</p>
                <p style="margin:0 0 24px;font-size:15px;line-height:1.55;color:#c8ccda;">Please subscribe to get reminders so Barzakh can nudge you when it slips off your radar.</p>
                <p style="margin:0 0 4px;font-size:15px;line-height:1.55;color:#e8eaf0;">- Ali</p>
                <p style="margin:0 0 24px;font-size:13px;line-height:1.55;color:#6b7280;">Barzakh</p>
                <p style="margin:0 0 14px;">
                  <a href="{click_url}" style="display:inline-block;background:#3bdcff;color:#071013;text-decoration:none;font-weight:700;font-size:14px;padding:12px 18px;border-radius:4px;">Open Barzakh</a>
                </p>
                <p style="margin:0;font-size:13px;line-height:1.55;color:#8b93a7;"><a href="{click_url}" style="color:#8b93a7;text-decoration:underline;">https://barzakh.app</a></p>
                <img src="{open_url}" alt="" width="1" height="1" style="display:none;opacity:0;width:1px;height:1px;border:0;">
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def _redact_email(email: str) -> str:
    if "@" not in email:
        return "<invalid>"
    local, domain = email.split("@", 1)
    prefix = local[:2] if len(local) >= 2 else local[:1]
    return f"{prefix}***@{domain}"


def _recipient_key(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:12]


def _first_name_from_email(email: str) -> str | None:
    if "@" not in email:
        return None
    local = email.split("@", 1)[0]
    token = local.replace("_", ".").replace("-", ".").split(".", 1)[0]
    token = "".join(ch for ch in token if ch.isalpha())
    if len(token) < 2:
        return None
    return token[:1].upper() + token[1:].lower()


def _tracking_user_id(user) -> int | None:
    raw = getattr(user, "user_id", None)
    return raw if isinstance(raw, int) else None


def _render_body(user) -> tuple[str, str]:
    first_name = _recipient_first_name(user)
    safe_first = (first_name or "").strip() or "there"
    recipient_key = _recipient_key(user.email)
    tracking_user_id = _tracking_user_id(user)
    click_url = build_click_tracking_url(
        campaign_version=CAMPAIGN_VERSION,
        recipient_key=recipient_key,
        user_id=tracking_user_id,
        target_url=LANDING_URL,
    )
    open_url = build_open_tracking_url(
        campaign_version=CAMPAIGN_VERSION,
        recipient_key=recipient_key,
        user_id=tracking_user_id,
    )
    return (
        BODY_TEMPLATE.format(first_name=safe_first),
        HTML_TEMPLATE.format(
            first_name=safe_first,
            logo_url=LOGO_URL,
            click_url=click_url,
            open_url=open_url,
        ),
    )


def _recipient_first_name(user) -> str | None:
    """Return explicit first_name when present, else derive from email.

    The one-off `_Recipient` DTO accepts first_name for test sends. Real
    database `User` rows currently do not have a first_name column, so this
    must use getattr instead of assuming schema that does not exist.
    """
    explicit = getattr(user, "first_name", None)
    if explicit:
        return explicit
    return _first_name_from_email(user.email)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run or schedule the Barzakh reactivation email."
    )
    parser.add_argument(
        "--scope",
        choices=("operator", "all"),
        default="operator",
        help="Recipient set. Defaults to operator for first test.",
    )
    parser.add_argument(
        "--scheduled-at",
        default="2026-06-03T17:00:00Z",
        help="Resend scheduled_at timestamp. 2026-06-03T17:00:00Z = 8 PM Cairo.",
    )
    parser.add_argument(
        "--immediate",
        action="store_true",
        help="Send immediately instead of scheduling. Intended for test sends.",
    )
    parser.add_argument(
        "--to",
        default=None,
        help="Explicit one-off recipient email. Overrides --scope.",
    )
    parser.add_argument(
        "--first-name",
        default=None,
        help="Optional first name for explicit test/personalized sends.",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Actually call Resend. Omit for dry-run.",
    )
    return parser.parse_args()


def _recipient_query(db, scope: str):
    query = db.query(User).filter(User.email.is_not(None))
    if scope == "operator":
        query = query.filter(User.is_operator.is_(True))
    return query.order_by(User.user_id.asc()).all()


class _Recipient:
    def __init__(self, user_id: str, email: str, first_name: str | None = None) -> None:
        self.user_id = user_id
        self.email = email
        self.first_name = first_name


def _send_one(
    *,
    user: _Recipient,
    subject: str,
    text: str,
    html: str | None,
    scheduled_at: str | None,
    scope_label: str,
    phase: str,
) -> bool:
    result = send_resend_email(
        to=user.email,
        subject=subject,
        text=text,
        html=html,
        scheduled_at=scheduled_at,
        idempotency_key=(
            f"barzakh-reactivation-{CAMPAIGN_VERSION}-{phase}-"
            f"{scheduled_at or 'immediate'}-{scope_label}-"
            f"{user.user_id}-{_recipient_key(user.email)}"
        ),
    )
    status = "sent" if result.sent else f"failed:{result.status}"
    if result.error:
        status = f"{status}:{result.error}"
    print(
        f"{phase}:{status} user_id={user.user_id} "
        f"email={_redact_email(user.email)}"
    )
    return result.sent


def main() -> int:
    args = _parse_args()
    scheduled_at = None if args.immediate else args.scheduled_at
    # Validate early so typos fail before any send loop.
    if scheduled_at:
        datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))

    if args.to:
        recipients = [_Recipient("explicit-test", args.to, args.first_name)]
        scope_label = "explicit"
    else:
        db = SessionLocal()
        try:
            recipients = _recipient_query(db, args.scope)
        finally:
            db.close()
        scope_label = args.scope

    print(f"from={BARZAKH_FROM_HEADER}")
    print(f"subject={SUBJECT}")
    print(f"campaign_version={CAMPAIGN_VERSION}")
    print(f"url={LANDING_URL}")
    print(f"logo={LOGO_URL}")
    print(f"scheduled_at={scheduled_at or '<immediate>'}")
    print(f"scope={scope_label}")
    print(f"recipient_count={len(recipients)}")
    print(f"email_count={len(recipients)}")
    for user in recipients:
        first_name = _recipient_first_name(user) or "there"
        print(
            f"- user_id={user.user_id} email={_redact_email(user.email)} "
            f"first_name={first_name}"
        )

    if not args.send:
        print("\ndry_run=true; no emails sent.")
        print("\nBody:\n")
        text, _html = _render_body(recipients[0]) if recipients else ("", "")
        print(text)
        return 0

    if not getattr(settings, "RESEND_API_KEY", ""):
        print("send_aborted=missing_RESEND_API_KEY")
        return 2

    sent = 0
    failed = 0
    for user in recipients:
        text, html = _render_body(user)
        if _send_one(
            user=user,
            subject=SUBJECT,
            text=text,
            html=html,
            scheduled_at=scheduled_at,
            scope_label=scope_label,
            phase="main-html",
        ):
            sent += 1
        else:
            failed += 1

    print(f"summary sent={sent} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
