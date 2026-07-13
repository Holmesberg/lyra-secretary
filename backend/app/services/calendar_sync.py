"""Google Calendar read-only sync.

Path B read-only integration — imports the user's primary Google
Calendar events as ambient scheduling context. Events are NEVER
persisted to the `task` table; they're fetched on demand via Redis
cache. The /calendar UI renders them as read-only grey background
blocks alongside LyraOS tasks.

Research-integrity note: imported events must NOT enter the H1 test
set. The separation is natural-by-design: events live only in the
Redis cache, never in `task`, so any SELECT FROM task automatically
excludes them. If we later decide to persist them for longitudinal
research, the rows will need an explicit `external_source` marker
and H1 queries will need a `WHERE external_source IS NULL` filter.
Pre-registered in docs/strategic_decisions_april_21.md §6.

Operator's spec 2026-04-21:
  - Primary calendar only (no multi-calendar UX in v1)
  - Skip all-day events and declined events
  - Redis cache with short TTL (60s — frames as "instant")
  - Graceful degradation: missing refresh_token or revoked access
    returns empty event list, never raises to the UI
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Optional

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.db.models import User
from app.db.session import SessionLocal
from app.services.operator_notifier import (
    format_alert_context,
    notify_operator,
    redacted_user_ref,
)
from app.utils.encryption import decrypt_secret, encrypt_secret, is_encrypted_secret
from app.utils.redis_client import RedisClient

logger = logging.getLogger(__name__)

# How long the Redis-cached event list stays fresh per (user, window).
# Operator's spec framed GCal as "instant" — 60s is the practical
# compromise: the user doesn't hit Google's API on every /calendar
# mount, but a new event added to GCal appears in LyraOS within a minute.
CACHE_TTL_SECONDS = 60
# How long a refreshed Google access_token stays cached in Redis. Google
# tokens expire at 60 min; we cache for 45 to avoid the expiry edge.
ACCESS_TOKEN_TTL_SECONDS = 45 * 60


@dataclass
class ExternalEvent:
    """Normalized Google Calendar event for frontend consumption.

    Not a SQLAlchemy model — never persisted. Serialized directly to
    JSON in the /v1/calendar/events response.
    """

    id: str
    title: str
    start: str  # Cairo-local ISO "YYYY-MM-DDTHH:MM:SS" (project timezone contract)
    end: str
    calendar_id: str
    source: str = "google"


@dataclass
class ExternalEventFetchResult:
    """Events plus read availability without claiming provider completeness."""

    events: list[ExternalEvent]
    status: Literal["available", "unavailable", "not_connected"]
    reason: str | None = None


def _access_token_cache_key(user_id: int) -> str:
    return f"gcal:access_token:{user_id}"


def _events_cache_key(user_id: int, date_from: str, date_to: str) -> str:
    return f"gcal:events:{user_id}:{date_from}:{date_to}"


def _cairo_local_iso(dt: datetime) -> str:
    """Format a tz-aware datetime as a Cairo-local naive ISO string.

    Project timezone contract: all timestamps travel as naive strings
    treated as Africa/Cairo wall-clock. Google returns tz-aware
    datetimes; we strip tz after shifting.
    """
    try:
        from zoneinfo import ZoneInfo
    except ImportError:  # py<3.9 fallback path — not expected in prod
        import pytz  # type: ignore

        tz = pytz.timezone("Africa/Cairo")
        return dt.astimezone(tz).replace(tzinfo=None).isoformat()
    tz = ZoneInfo("Africa/Cairo")
    return dt.astimezone(tz).replace(tzinfo=None).isoformat(timespec="seconds")


def _get_credentials(user: User, db=None) -> Optional[Credentials]:
    """Build google.oauth2.credentials.Credentials from the user's row.

    Returns None if the user has no refresh_token (hasn't granted
    calendar scope yet, or revoked access). Caller must handle None
    gracefully — missing calendar is not an error condition.
    """
    if not user.google_refresh_token:
        return None
    refresh_token = decrypt_secret(user.google_refresh_token)
    if not refresh_token:
        return None
    if db is not None and not is_encrypted_secret(user.google_refresh_token):
        user.google_refresh_token = encrypt_secret(refresh_token)
        db.commit()

    # Try cached access_token first to avoid a refresh round-trip on
    # every /calendar/events call.
    redis = RedisClient().client
    cached = redis.get(_access_token_cache_key(user.user_id))
    access_token = cached.decode() if isinstance(cached, bytes) else cached

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )

    # Refresh if we have no cached access token or if google-auth
    # reports the current token invalid/expired.
    if not creds.token or not creds.valid:
        try:
            creds.refresh(GoogleRequest())
        except Exception as e:
            logger.warning(
                "gcal: access token refresh failed for user %s: %s",
                user.user_id,
                e,
            )
            if user.is_operator:
                notify_operator(
                    "Google Calendar token refresh failed. Reconnect Calendar "
                    "from Settings if this persists.\n\n"
                    + format_alert_context(
                        affected="Google Calendar / availability read",
                        scope=redacted_user_ref(user.user_id),
                        retry=(
                            "Calendar context returns empty for this request; "
                            "LyraOS retries when calendar context is requested again."
                        ),
                        user_action=(
                            "Reconnect Calendar only if the failure persists."
                        ),
                        data_integrity=(
                            "No tasks, deadlines, or calendar events are "
                            "written by this read-only path."
                        ),
                    ),
                    source="calendar.sync",
                    severity="warn",
                    dedupe_key=f"gcal-refresh-failed:{user.user_id}:{type(e).__name__}",
                    cooldown_seconds=24 * 60 * 60,
                )
            return None
        redis.setex(
            _access_token_cache_key(user.user_id),
            ACCESS_TOKEN_TTL_SECONDS,
            creds.token,
        )

    return creds


def fetch_google_events_with_status(
    user_id: int, date_from: datetime, date_to: datetime
) -> ExternalEventFetchResult:
    """Return events and whether the requested window was readable.

    Cached in Redis for CACHE_TTL_SECONDS. On cache miss, calls
    events.list against the user's primary calendar with
    singleEvents=true (recurring events expanded to instances).
    """
    date_from_key = date_from.date().isoformat()
    date_to_key = date_to.date().isoformat()
    redis = RedisClient().client
    cached = redis.get(_events_cache_key(user_id, date_from_key, date_to_key))
    if cached:
        try:
            payload = json.loads(cached)
            return ExternalEventFetchResult(
                events=[ExternalEvent(**e) for e in payload],
                status="available",
            )
        except Exception as e:
            # Cache poisoning shouldn't bubble up — log and re-fetch.
            logger.warning("gcal: cache parse failed, re-fetching: %s", e)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user is None:
            return ExternalEventFetchResult(
                events=[], status="unavailable", reason="user_not_found"
            )
        was_connected = bool(user.google_refresh_token)
        creds = _get_credentials(user, db)
        if creds is None:
            return ExternalEventFetchResult(
                events=[],
                status="unavailable" if was_connected else "not_connected",
                reason=(
                    "credentials_unavailable"
                    if was_connected
                    else "not_connected"
                ),
            )

        try:
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            # events.list with singleEvents=true expands recurring
            # events to their individual instances — we don't handle
            # RRULE ourselves. orderBy=startTime is only valid with
            # singleEvents=true, so keep both together.
            response = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=date_from.isoformat() + "Z",
                    timeMax=date_to.isoformat() + "Z",
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=250,
                )
                .execute()
            )
        except HttpError as e:
            # 401 → refresh token revoked or invalid. Clear it so the
            # frontend can prompt re-consent instead of erroring every
            # time /calendar loads.
            if e.resp.status == 401:
                logger.warning(
                    "gcal: 401 for user %s — clearing refresh_token", user_id
                )
                user.google_refresh_token = None
                db.commit()
                if user.is_operator:
                    notify_operator(
                        "Google Calendar returned 401, so LyraOS cleared the "
                        "stored refresh token. Reconnect Calendar in Settings.\n\n"
                        + format_alert_context(
                            affected="Google Calendar / availability read",
                            scope=redacted_user_ref(user_id),
                            retry=(
                                "No retry will succeed until Calendar is "
                                "reconnected."
                            ),
                            user_action="Yes - reconnect Calendar in Settings.",
                            data_integrity=(
                                "Stored refresh token was cleared; no tasks, "
                                "deadlines, or calendar events were written."
                            ),
                        ),
                        source="calendar.sync",
                        severity="warn",
                        dedupe_key=f"gcal-401:{user_id}",
                        cooldown_seconds=24 * 60 * 60,
                    )
            else:
                logger.warning("gcal: events.list HttpError for user %s: %s", user_id, e)
                if user.is_operator:
                    notify_operator(
                        f"Google Calendar events.list failed with HTTP {e.resp.status}. "
                        "Calendar context is temporarily unavailable.\n\n"
                        + format_alert_context(
                            affected="Google Calendar / availability read",
                            scope=redacted_user_ref(user_id),
                            retry=(
                                "Calendar context returns empty for this "
                                "request; LyraOS retries when calendar context "
                                "is requested again."
                            ),
                            user_action=(
                                "No user action unless the provider failure "
                                "persists."
                            ),
                            data_integrity=(
                                "No tasks, deadlines, or calendar events are "
                                "written by this read-only path."
                            ),
                        ),
                        source="calendar.sync",
                        severity="warn",
                        dedupe_key=f"gcal-http:{user_id}:{e.resp.status}",
                        cooldown_seconds=60 * 60,
                    )
            return ExternalEventFetchResult(
                events=[],
                status="unavailable",
                reason=f"provider_http_{e.resp.status}",
            )
        except Exception as e:
            logger.warning("gcal: events.list failed for user %s: %s", user_id, e)
            if user.is_operator:
                notify_operator(
                    f"Google Calendar events.list failed with `{type(e).__name__}`. "
                    "Calendar context is temporarily unavailable.\n\n"
                    + format_alert_context(
                        affected="Google Calendar / availability read",
                        scope=redacted_user_ref(user_id),
                        retry=(
                            "Calendar context returns empty for this request; "
                            "LyraOS retries when calendar context is requested again."
                        ),
                        user_action=(
                            "No user action unless the provider failure persists."
                        ),
                        data_integrity=(
                            "No tasks, deadlines, or calendar events are "
                            "written by this read-only path."
                        ),
                    ),
                    source="calendar.sync",
                    severity="warn",
                    dedupe_key=f"gcal-events-failed:{user_id}:{type(e).__name__}",
                    cooldown_seconds=60 * 60,
                )
            return ExternalEventFetchResult(
                events=[],
                status="unavailable",
                reason=f"provider_{type(e).__name__}",
            )

        events: list[ExternalEvent] = []
        for item in response.get("items", []):
            # Skip all-day events (no time data — can't place on a
            # scheduled view).
            start = item.get("start", {})
            end = item.get("end", {})
            if "dateTime" not in start or "dateTime" not in end:
                continue

            # Skip events the user has declined. Self-organized events
            # don't have attendee entries — include them unconditionally.
            attendees = item.get("attendees", [])
            self_attendee = next(
                (a for a in attendees if a.get("self")), None
            )
            if self_attendee and self_attendee.get("responseStatus") == "declined":
                continue

            try:
                start_dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end["dateTime"].replace("Z", "+00:00"))
            except ValueError:
                logger.warning("gcal: could not parse event times: %s", item.get("id"))
                continue

            events.append(
                ExternalEvent(
                    id=str(item.get("id", "")),
                    title=item.get("summary", "(no title)"),
                    start=_cairo_local_iso(start_dt),
                    end=_cairo_local_iso(end_dt),
                    calendar_id="primary",
                )
            )

        # Cache the serialized list.
        redis.setex(
            _events_cache_key(user_id, date_from_key, date_to_key),
            CACHE_TTL_SECONDS,
            json.dumps([e.__dict__ for e in events]),
        )
        return ExternalEventFetchResult(events=events, status="available")
    finally:
        db.close()


def fetch_google_events(
    user_id: int, date_from: datetime, date_to: datetime
) -> list[ExternalEvent]:
    """Compatibility reader for existing Calendar consumers."""

    return fetch_google_events_with_status(user_id, date_from, date_to).events


def store_refresh_token(user_id: int, refresh_token: str) -> None:
    """Persist a newly-acquired refresh token to the user row.

    Called by POST /v1/users/me/google-refresh-token (the NextAuth
    server-side API route forwards the token on first sign-in with
    calendar scope). Credential-class storage is Fernet-prefixed; legacy
    plaintext rows are rewritten by _get_credentials().
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user is None:
            raise ValueError(f"user {user_id} not found")
        user.google_refresh_token = encrypt_secret(refresh_token)
        db.commit()
        # Invalidate any stale cached access_token from a previous
        # refresh_token — next fetch will refresh cleanly.
        RedisClient().client.delete(_access_token_cache_key(user_id))
    finally:
        db.close()
