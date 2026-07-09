"""Moodle LMS iCal subscription import.

Mirrors the read-only integration pattern of `services/calendar_sync.py`
(Path B Apr 21) but with ONE crucial divergence: imported events are
*persisted* as Barzakh `Deadline` rows (with `external_source='moodle_ics'`
flagged), not held ephemeral in Redis. This is because Moodle assignments
ARE the deadlines a student wants to organize their semester around —
they're the wedge, not ambient context.

Research-integrity contract:
  - Deadlines created here carry `external_source='moodle_ics'`.
  - H2 queries (MANIFESTO Rules 14-16) and the Loop 11 reconciliation
    job MUST filter `WHERE external_source IS NULL` to keep H2's test
    set native-only.
  - Pre-registered as VT-29 (External-deadline contamination) in
    MANIFESTO.md — distinguishing test required at H2 publication time.

Credential discipline:
  - `user.moodle_ics_url` contains a private authtoken; treat as
    credential-equivalent, never log the full URL, redact via
    `_redact_url()` before any logger.warning().
  - On 4xx the URL is cleared and a disconnect_reason is set so the
    frontend can surface "Reconnect needed" rather than silently
    failing. This is the same hardening pattern as
    calendar_sync.py:194 (Google Calendar 401 → clear refresh_token).

Operator's spec 2026-04-29 (LMS-first call):
  - Validate by fetching one event before storing the URL.
  - Sync every 6h (Moodle docs say new/changed events appear within
    "several hours" — 6h is the right granularity).
  - Skip RRULE recurring events (lecture schedules, not deadlines).
  - Skip all-day events (insufficient time precision for a deadline).
  - Cap at MAX_EVENTS_PER_SYNC = 500 (defensive against malformed
    feeds or pranksters).
"""
from __future__ import annotations

import logging
import re
import ipaddress
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, Optional
from urllib.parse import urlparse

import httpx
from icalendar import Calendar
from sqlalchemy.orm import Session

from app.db.models import Deadline, User
from app.db.scoping import get_current_user_id, set_current_user_id
from app.utils.encryption import decrypt_secret, encrypt_secret, is_encrypted_secret
from app.utils.provider_url_safety import ProviderUrlSafetyError, safe_provider_get

logger = logging.getLogger(__name__)


# Course-code prefix pattern. Matches "CSE281", "PHM123", "ABC101", etc.
# Anchored at start; CATEGORIES values like "CSE281 (UG2023) - Intro to AI"
# yield "CSE281".
_COURSE_CODE_RE = re.compile(r"^([A-Z]{2,4}\d{2,4})\b")

# Authtoken redaction pattern — drops the secret substring before any
# log emission. Matches Moodle's `?authtoken=abcdef0123…&...` shape.
_AUTHTOKEN_RE = re.compile(r"(authtoken=)[^&\s]+", re.IGNORECASE)

HTTP_TIMEOUT_SECONDS = 10.0
MAX_EVENTS_PER_SYNC = 500


@dataclass
class ParsedEvent:
    """A VEVENT after format normalization, ready for upsert."""

    external_uid: str  # the iCal UID, used as `external_id` in Deadline
    title: str
    description: Optional[str]
    due_at_utc: datetime  # naive UTC, project timezone contract
    category_hint: Optional[str]  # extracted course code, or None


@dataclass
class SyncResult:
    """Per-user sync summary. Returned by sync_user() and the preview
    endpoint. Counts sum: fetched == created + updated + unchanged +
    skipped_voided + skipped_unparseable + duplicate_existing."""

    fetched: int
    created: int
    updated: int
    unchanged: int
    skipped_voided: int
    skipped_unparseable: int
    error: Optional[str]
    duplicate_existing: int = 0


def _redact_url(url: str) -> str:
    """Return URL with the authtoken value masked. Safe for logging."""
    return _AUTHTOKEN_RE.sub(r"\1•••", url)


def _widen_time_window(url: str) -> str:
    """Override Moodle's preset_time query param to pull EVERYTHING.

    Why: Moodle's calendar exporter defaults to preset_time=recentupcoming
    which clips events to roughly [now-14d, now+60d]. Assignments due
    earlier than 14 days ago drop out of the feed entirely, so any
    overdue work the user wants to triage is silently invisible to Barzakh.

    Operator complaint 2026-05-01 morning: 'overdue tasks were submitted
    yesterday and they weren't synced.' Root cause was this filter, not
    the sync job itself. Per-event date validation already happens
    downstream via _parse_one_event so widening the feed is safe — we
    just stop dropping the past tail.

    Override applied transparently per-fetch (not stored in the user's
    URL) so re-pasting the original URL from Moodle works without
    tedious operator-side editing. preset_what is left alone.
    """
    from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

    parsed = urlparse(url)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    rewritten: list[tuple[str, str]] = []
    seen_preset_time = False
    for k, v in pairs:
        if k == "preset_time":
            rewritten.append((k, "custom"))
            seen_preset_time = True
        else:
            rewritten.append((k, v))
    if not seen_preset_time:
        rewritten.append(("preset_time", "custom"))
    # Moodle's custom preset uses ABSOLUTE Unix timestamp `time` plus
    # `timeduration` in seconds. Window: 365 days back from now → 730
    # days total (1 year past + 1 year forward). Generous bounds —
    # covers historical overdue + a full academic year ahead. Per-event
    # date validation happens downstream so feed bloat is bounded.
    rewritten = [(k, v) for k, v in rewritten if k not in ("time", "timeduration")]
    import time as _time
    now_ts = int(_time.time())
    one_year = 365 * 86400
    rewritten.append(("time", str(now_ts - one_year)))
    rewritten.append(("timeduration", str(2 * one_year)))
    new_query = urlencode(rewritten, doseq=False)
    return urlunparse(parsed._replace(query=new_query))


def fetch_ics(url: str) -> bytes:
    """GET the .ics body. Raises httpx exceptions on transport failure;
    callers wrap for graceful degradation.

    Applies _widen_time_window so the feed includes overdue + far-future
    events instead of Moodle's default narrow window. Operator URL stays
    unchanged in the DB — the rewrite is per-request only.
    """
    response = safe_provider_get(
        _widen_time_window(url),
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.content


def parse_calendar(body: bytes) -> Iterator[ParsedEvent]:
    """Iterate parsed events from an iCal body.

    Skips non-deadline events (RRULE recurring, all-day, missing fields).
    Stops at MAX_EVENTS_PER_SYNC to defend against pathologically large
    feeds.
    """
    cal = Calendar.from_ical(body)
    yielded = 0
    for component in cal.walk("vevent"):
        if yielded >= MAX_EVENTS_PER_SYNC:
            logger.warning(
                "moodle: hit MAX_EVENTS_PER_SYNC=%d; truncating",
                MAX_EVENTS_PER_SYNC,
            )
            break
        event = _parse_one_event(component)
        if event is not None:
            yield event
            yielded += 1


def _parse_one_event(vevent) -> Optional[ParsedEvent]:
    """Normalize one VEVENT. Returns None for events to skip.

    Skip reasons (silent — these are normal in real feeds):
      - has RRULE (recurring; lecture schedule, not a deadline)
      - missing UID, SUMMARY, or DTSTART
      - DTSTART is a date (all-day; no precise deadline time)
    """
    if vevent.get("RRULE") is not None:
        return None

    uid = str(vevent.get("UID", "")).strip()
    if not uid:
        return None

    summary = str(vevent.get("SUMMARY", "")).strip()
    if not summary:
        return None

    dtstart = vevent.get("DTSTART")
    if dtstart is None:
        return None

    dtstart_value = dtstart.dt
    # icalendar returns either datetime (timed) or date (all-day).
    # All-day events lack the time precision a deadline needs — skip.
    if not isinstance(dtstart_value, datetime):
        return None

    # Normalize to naive UTC per project timezone contract. Moodle's
    # default emits Z-suffixed (UTC); guard for tz-aware-non-UTC anyway.
    if dtstart_value.tzinfo is not None:
        due_at_utc = dtstart_value.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        # Naive datetime in iCal is technically allowed; treat as UTC
        # by convention (matches Moodle's behavior when no TZID set).
        due_at_utc = dtstart_value

    description_field = vevent.get("DESCRIPTION")
    description_text = (
        str(description_field).strip() if description_field is not None else ""
    )
    description_normalized = description_text or None

    category_hint = _extract_course_code(vevent.get("CATEGORIES"))

    return ParsedEvent(
        external_uid=uid,
        title=summary,
        description=description_normalized,
        due_at_utc=due_at_utc,
        category_hint=category_hint,
    )


def _extract_course_code(categories_field) -> Optional[str]:
    """Pull the course-code prefix from a CATEGORIES value.

    `icalendar` returns CATEGORIES as a `vCategory` object (a list of
    vText entries), and `str()` on it returns the object repr, not the
    text. Use `.to_ical()` (bytes) to recover the raw value.

    Examples:
      "CSE281 (UG2023) - Introduction to AI (40587)" → "CSE281"
      "PHM123 (UG2023) - Physical Electronics (40412)" → "PHM123"
      "Some Other Category"                            → None
    """
    if categories_field is None:
        return None
    try:
        raw_bytes = categories_field.to_ical()
        raw = raw_bytes.decode("utf-8", errors="replace").strip()
    except AttributeError:
        # Defensive fallback if icalendar ever returns a plain string.
        raw = str(categories_field).strip()
    if not raw:
        return None
    match = _COURSE_CODE_RE.match(raw)
    return match.group(1) if match else None


def preview(url: str) -> tuple[list[ParsedEvent], Optional[str]]:
    """Try-before-buy: fetch + parse, return events without persisting.

    Used by POST /v1/integrations/moodle/preview during the connect
    modal so users see exactly what will be imported before they commit.
    Returns (events, None) on success, ([], error_code) on failure.
    """
    try:
        body = fetch_ics(url)
    except httpx.HTTPStatusError as e:
        return [], f"http_{e.response.status_code}"
    except httpx.RequestError:
        return [], "fetch_failed"
    except ProviderUrlSafetyError as e:
        return [], e.code
    except Exception:
        return [], "fetch_unknown"
    try:
        events = list(parse_calendar(body))
    except Exception:
        return [], "parse_failed"
    return events, None


def sync_user(user_id: int, db: Session) -> SyncResult:
    """Fetch + parse + upsert deadlines for one user with a stored URL.

    Graceful degradation: returns SyncResult with `error` set on any
    failure; never raises. Updates `user.moodle_last_synced_at` on
    success; clears `user.moodle_ics_url` and sets
    `user.moodle_disconnect_reason` on permanent failure (4xx).
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        return SyncResult(0, 0, 0, 0, 0, 0, "user_not_found")
    if not user.moodle_ics_url:
        return SyncResult(0, 0, 0, 0, 0, 0, "no_url_stored")

    url_plain = decrypt_secret(user.moodle_ics_url)
    if not url_plain:
        user.moodle_disconnect_reason = "url_decrypt_failed"
        db.commit()
        return SyncResult(0, 0, 0, 0, 0, 0, "url_decrypt_failed")
    if not is_encrypted_secret(user.moodle_ics_url):
        user.moodle_ics_url = encrypt_secret(url_plain)
        db.commit()

    redacted = _redact_url(url_plain)

    try:
        body = fetch_ics(url_plain)
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if 400 <= status < 500:
            logger.warning(
                "moodle: %d for user %s (%s) — clearing URL, marking disconnected",
                status, user_id, redacted,
            )
            user.moodle_ics_url = None
            user.moodle_disconnect_reason = f"token_invalid_{status}"
            db.commit()
            return SyncResult(0, 0, 0, 0, 0, 0, f"http_{status}")
        logger.warning(
            "moodle: %d for user %s (%s) — transient, will retry next cycle",
            status, user_id, redacted,
        )
        return SyncResult(0, 0, 0, 0, 0, 0, f"http_{status}")
    except httpx.RequestError as e:
        logger.warning(
            "moodle: transport error for user %s (%s): %s",
            user_id, redacted, e.__class__.__name__,
        )
        return SyncResult(0, 0, 0, 0, 0, 0, "fetch_failed")
    except ProviderUrlSafetyError as e:
        logger.warning(
            "moodle: rejected unsafe URL for user %s (%s): %s",
            user_id, redacted, e.code,
        )
        return SyncResult(0, 0, 0, 0, 0, 0, e.code)
    except Exception as e:
        logger.warning(
            "moodle: unexpected fetch error for user %s (%s): %s",
            user_id, redacted, e.__class__.__name__,
        )
        return SyncResult(0, 0, 0, 0, 0, 0, "fetch_unknown")

    try:
        events = list(parse_calendar(body))
    except Exception as e:
        logger.warning(
            "moodle: parse failed for user %s: %s", user_id, e.__class__.__name__
        )
        return SyncResult(0, 0, 0, 0, 0, 0, "parse_failed")

    # Lazy import: deadline_manager imports Deadline from models, which
    # imports back nothing from us — but keeping the dance explicit helps
    # if anyone ever moves things.
    from app.services.deadline_manager import DeadlineManager

    manager = DeadlineManager(db)
    counts = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped_voided": 0,
        "duplicate_existing": 0,
    }
    skipped_unparseable = 0

    # DeadlineManager.upsert_external_deadline reads current_user_id
    # from the ContextVar. The APScheduler job runs outside any HTTP
    # request, so we set it explicitly here and restore the prior value
    # in the finally block (defensive — almost always None in jobs).
    prev_uid = get_current_user_id()
    set_current_user_id(user_id)
    try:
        for event in events:
            try:
                op = manager.upsert_external_deadline(
                    external_source="moodle_ics",
                    external_id=event.external_uid,
                    title=event.title,
                    due_at_utc=event.due_at_utc,
                    description=event.description,
                    category_hint=event.category_hint,
                )
                counts[op] = counts.get(op, 0) + 1
            except Exception as e:
                logger.warning(
                    "moodle: upsert failed for event %s (user %s): %s",
                    event.external_uid, user_id, e.__class__.__name__,
                )
                skipped_unparseable += 1
    finally:
        set_current_user_id(prev_uid)

    user.moodle_last_synced_at = datetime.utcnow()
    # Sync succeeded (regardless of per-event failures) — clear any
    # prior disconnect signal.
    user.moodle_disconnect_reason = None
    db.commit()

    return SyncResult(
        fetched=len(events),
        created=counts["created"],
        updated=counts["updated"],
        unchanged=counts["unchanged"],
        skipped_voided=counts["skipped_voided"],
        skipped_unparseable=skipped_unparseable,
        error=None,
        duplicate_existing=counts["duplicate_existing"],
    )


def validate_url_shape(url: str) -> Optional[str]:
    """Cheap pre-fetch validation — catch obviously-broken pastes early.

    Returns None if the URL passes shape checks; otherwise an error
    code string. Used by POST /v1/integrations/moodle/connect before
    spending an HTTP round-trip on the live fetch.
    """
    if not url or not isinstance(url, str):
        return "url_empty"
    url = url.strip()
    if len(url) > 2000:
        return "url_too_long"
    if not url.startswith(("http://", "https://")):
        return "url_not_http"
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        return "url_userinfo_forbidden"
    if parsed.hostname:
        try:
            ip = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            ip = None
        if ip is not None and (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return "url_private_network"
    if "/calendar/export_execute.php" not in url:
        return "url_not_moodle_export"
    if "authtoken=" not in url:
        return "url_missing_authtoken"
    return None
