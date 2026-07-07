"""Email engagement tracking endpoints.

Public open/click endpoints are signed-token only and record operational
campaign telemetry. They do not authenticate as users and do not produce
clean execution evidence.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db, operator_user_from_scope
from app.db.models import EmailEngagementEvent
from app.db.scoping import get_current_user_id, set_current_user_id
from app.db.session import SessionLocal
from app.services.email_engagement import parse_email_tracking_token

router = APIRouter()

_TRANSPARENT_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)
_DEFAULT_REDIRECT = "https://barzakh.app"


def _request_metadata(request: Request) -> dict[str, str | None]:
    forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = forwarded_for.split(",", 1)[0].strip() if forwarded_for else None
    if not client_ip and request.client:
        client_ip = request.client.host
    return {
        "user_agent": request.headers.get("user-agent"),
        "referer": request.headers.get("referer"),
        "ip_prefix": client_ip[:64] if client_ip else None,
    }


def _record_event(token: str, request: Request) -> str | None:
    payload = parse_email_tracking_token(token)
    if payload is None:
        return None

    original_scope = get_current_user_id()
    set_current_user_id(None)
    db = SessionLocal()
    try:
        db.add(
            EmailEngagementEvent(
                user_id=payload.user_id,
                campaign_version=payload.campaign_version,
                event_type=payload.event_type,
                recipient_key=payload.recipient_key,
                target_url=payload.target_url,
                request_metadata=_request_metadata(request),
            )
        )
        db.commit()
    finally:
        db.close()
        set_current_user_id(original_scope)

    return payload.target_url


@router.get("/email-engagement/open.gif")
def record_email_open(request: Request, t: str = Query(default="")) -> Response:
    if t:
        _record_event(t, request)
    return Response(
        content=_TRANSPARENT_GIF,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.get("/email-engagement/click")
def record_email_click(request: Request, t: str = Query(default="")) -> RedirectResponse:
    target_url = _record_event(t, request) if t else None
    return RedirectResponse(target_url or _DEFAULT_REDIRECT, status_code=302)


@router.get("/admin/email-engagement")
def email_engagement_summary(
    request: Request,
    campaign_version: str | None = Query(default=None),
    since_days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Operator-only distinct recipient summary for email campaigns."""
    operator_user_from_scope(db, request=request)

    original_scope = get_current_user_id()
    set_current_user_id(None)
    try:
        since = datetime.utcnow() - timedelta(days=since_days)
        query = db.query(EmailEngagementEvent).filter(
            EmailEngagementEvent.occurred_at >= since
        )
        if campaign_version:
            query = query.filter(
                EmailEngagementEvent.campaign_version == campaign_version
            )

        grouped = (
            query.with_entities(
                EmailEngagementEvent.campaign_version.label("campaign_version"),
                EmailEngagementEvent.event_type.label("event_type"),
                func.count(EmailEngagementEvent.event_id).label("event_count"),
                func.count(func.distinct(EmailEngagementEvent.recipient_key)).label(
                    "recipient_count"
                ),
            )
            .group_by(
                EmailEngagementEvent.campaign_version,
                EmailEngagementEvent.event_type,
            )
            .order_by(
                EmailEngagementEvent.campaign_version.asc(),
                EmailEngagementEvent.event_type.asc(),
            )
            .all()
        )

        campaigns: dict[str, dict[str, Any]] = {}
        for row in grouped:
            campaign = campaigns.setdefault(
                row.campaign_version,
                {
                    "campaign_version": row.campaign_version,
                    "opens": {"events": 0, "distinct_recipients": 0},
                    "clicks": {"events": 0, "distinct_recipients": 0},
                },
            )
            key = "opens" if row.event_type == "open" else "clicks"
            campaign[key] = {
                "events": int(row.event_count or 0),
                "distinct_recipients": int(row.recipient_count or 0),
            }

        return {
            "schema_version": "email_engagement_summary_v1",
            "since_days": since_days,
            "campaign_version": campaign_version,
            "read_note": (
                "Open counts are best-effort image loads, not proof that a "
                "person read the email. Click counts are stronger."
            ),
            "campaigns": list(campaigns.values()),
        }
    finally:
        set_current_user_id(original_scope)
