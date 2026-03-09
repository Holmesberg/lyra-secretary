"""Timezone conversion utilities.

CRITICAL RULE: All times stored in UTC, displayed in user's local time.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core.config import settings

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
