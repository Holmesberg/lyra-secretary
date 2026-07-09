"""Signed email engagement links for operational campaign telemetry."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from urllib.parse import quote, urlparse

from app.core.config import settings

TRACKING_TOKEN_VERSION = 1
ALLOWED_EVENT_TYPES = {"open", "click"}


@dataclass(frozen=True)
class EmailTrackingPayload:
    campaign_version: str
    event_type: str
    recipient_key: str
    user_id: int | None
    target_url: str | None = None


def _urlsafe_b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _sign(payload_b64: str) -> str:
    secret = settings.SECRET_KEY.encode("utf-8")
    digest = hmac.new(secret, payload_b64.encode("ascii"), hashlib.sha256).digest()
    return _urlsafe_b64encode(digest)


def _tracking_base_url() -> str:
    return settings.EMAIL_TRACKING_BASE_URL.rstrip("/")


def _safe_target_url(target_url: str | None) -> str | None:
    if not target_url:
        return None
    parsed = urlparse(target_url)
    if parsed.scheme != "https":
        return None
    allowed_hosts = {"lyraos.org", "www.lyraos.org", "lyraos.org", "www.lyraos.org"}
    frontend_host = urlparse(settings.FRONTEND_URL).hostname
    if frontend_host:
        allowed_hosts.add(frontend_host)
    if parsed.hostname not in allowed_hosts:
        return None
    return target_url


def build_email_tracking_token(
    *,
    campaign_version: str,
    event_type: str,
    recipient_key: str,
    user_id: int | None,
    target_url: str | None = None,
) -> str:
    """Build a signed token without embedding raw email addresses."""
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"unsupported email event type: {event_type}")
    payload = {
        "v": TRACKING_TOKEN_VERSION,
        "campaign_version": campaign_version,
        "event_type": event_type,
        "recipient_key": recipient_key,
        "user_id": user_id,
        "target_url": _safe_target_url(target_url),
    }
    payload_b64 = _urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    return f"{payload_b64}.{_sign(payload_b64)}"


def parse_email_tracking_token(token: str) -> EmailTrackingPayload | None:
    """Return the token payload only when signature and fields are valid."""
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError:
        return None
    expected = _sign(payload_b64)
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        data = json.loads(_urlsafe_b64decode(payload_b64).decode("utf-8"))
    except Exception:  # noqa: BLE001 - invalid public token
        return None

    if data.get("v") != TRACKING_TOKEN_VERSION:
        return None
    event_type = data.get("event_type")
    campaign_version = data.get("campaign_version")
    recipient_key = data.get("recipient_key")
    if event_type not in ALLOWED_EVENT_TYPES:
        return None
    if not isinstance(campaign_version, str) or not campaign_version:
        return None
    if not isinstance(recipient_key, str) or not recipient_key:
        return None

    raw_user_id = data.get("user_id")
    user_id = raw_user_id if isinstance(raw_user_id, int) else None
    target_url = _safe_target_url(data.get("target_url"))
    return EmailTrackingPayload(
        campaign_version=campaign_version,
        event_type=event_type,
        recipient_key=recipient_key,
        user_id=user_id,
        target_url=target_url,
    )


def build_open_tracking_url(
    *, campaign_version: str, recipient_key: str, user_id: int | None
) -> str:
    token = build_email_tracking_token(
        campaign_version=campaign_version,
        event_type="open",
        recipient_key=recipient_key,
        user_id=user_id,
    )
    return f"{_tracking_base_url()}/v1/email-engagement/open.gif?t={quote(token)}"


def build_click_tracking_url(
    *,
    campaign_version: str,
    recipient_key: str,
    user_id: int | None,
    target_url: str,
) -> str:
    token = build_email_tracking_token(
        campaign_version=campaign_version,
        event_type="click",
        recipient_key=recipient_key,
        user_id=user_id,
        target_url=target_url,
    )
    return f"{_tracking_base_url()}/v1/email-engagement/click?t={quote(token)}"
