"""Shared, deterministic burden gates for shipped prediction delivery."""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


QUIET_HOURS_START = 22
QUIET_HOURS_END = 8


def is_within_prediction_quiet_hours(
    now_utc: datetime,
    timezone_name: str,
) -> bool:
    """Return whether ``now_utc`` falls in 22:00-07:59 user-local time.

    Runtime timestamps are normally naive UTC. Aware values are accepted so
    callers and tests cannot accidentally apply the user's offset twice.
    Invalid or missing IANA timezone names raise ``ValueError``; prediction
    workers treat that as a fail-closed delivery decision.
    """
    if not timezone_name or not timezone_name.strip():
        raise ValueError("prediction delivery requires a user timezone")

    try:
        user_zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"invalid user timezone: {timezone_name!r}") from exc

    utc_zone = ZoneInfo("UTC")
    if now_utc.tzinfo is None:
        aware_utc = now_utc.replace(tzinfo=utc_zone)
    else:
        aware_utc = now_utc.astimezone(utc_zone)

    local_hour = aware_utc.astimezone(user_zone).hour
    return local_hour >= QUIET_HOURS_START or local_hour < QUIET_HOURS_END
