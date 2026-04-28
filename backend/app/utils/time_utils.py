"""Timezone conversion utilities.

CRITICAL RULE: All times stored in UTC, displayed in user's local time.

Convention (locked 2026-04-28):
  - Internal Lyra datetime arithmetic uses NAIVE-UTC datetimes.
  - `now_utc()`, `to_utc(...)`, `to_local(...)` all return naive.
  - Datetimes loaded from Postgres/Supabase may be AWARE (when the
    column type is TIMESTAMPTZ — Supabase's default even when the
    SQLAlchemy model says `DateTime`). Subtracting an aware DB field
    from `now_utc()` raises `TypeError: can't subtract offset-naive
    and offset-aware datetimes`.
  - Datetimes parsed from Redis ISO strings (`datetime.fromisoformat`)
    may be aware if the original isoformat included timezone info.
  - **Pattern:** wrap any DB-loaded or fromisoformat-parsed datetime in
    `strip_tz()` BEFORE comparing/subtracting against an internal
    naive datetime.

This is a defensive layer, not a root-cause fix. v2 should switch the
internal convention to AWARE-UTC and update `now_utc()` accordingly.
"""
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core.config import settings


def strip_tz(dt: Optional[datetime]) -> Optional[datetime]:
    """Return `dt` with tzinfo stripped (naive datetime).

    Use anywhere a datetime might come from Postgres/Supabase
    (TIMESTAMPTZ → aware) or `datetime.fromisoformat` of a Redis-stored
    ISO string with offset (→ aware) before subtracting against
    `now_utc()` (always naive).

    Idempotent: naive input → naive output. None → None.
    """
    if dt is not None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt

def to_utc(local_dt: datetime) -> datetime:
    """
    Convert local datetime to UTC.
    
    Args:
        local_dt: Datetime in user's timezone (Africa/Cairo)
        
    Returns:
        Datetime in UTC
    """
    if local_dt.tzinfo is None:
        # Assume user's timezone
        tz = ZoneInfo(settings.USER_TIMEZONE)
        local_dt = local_dt.replace(tzinfo=tz)
    
    return local_dt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

def to_local(utc_dt: datetime) -> datetime:
    """
    Convert UTC datetime to user's local time.
    
    Args:
        utc_dt: Datetime in UTC
        
    Returns:
        Datetime in user's timezone (Africa/Cairo)
    """
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
    
    tz = ZoneInfo(settings.USER_TIMEZONE)
    return utc_dt.astimezone(tz).replace(tzinfo=None)

def now_utc() -> datetime:
    """Get current time in UTC."""
    return datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)

def now_local() -> datetime:
    """Get current time in user's timezone."""
    tz = ZoneInfo(settings.USER_TIMEZONE)
    return datetime.now(tz).replace(tzinfo=None)
