"""Shared, deterministic burden gates for shipped prediction delivery."""

from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.db.models import (
    NotificationLifecycleEvent,
    PausePredictionLog,
    ResumePredictionLog,
    User,
)


QUIET_HOURS_START = 22
QUIET_HOURS_END = 8
PREDICTION_SPACING_MINUTES = 30
PredictionFamily = Literal["pause_prediction", "resume_prediction"]


def _as_aware_utc(value: datetime) -> datetime:
    utc_zone = ZoneInfo("UTC")
    if value.tzinfo is None:
        return value.replace(tzinfo=utc_zone)
    return value.astimezone(utc_zone)


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

    local_hour = _as_aware_utc(now_utc).astimezone(user_zone).hour
    return local_hour >= QUIET_HOURS_START or local_hour < QUIET_HOURS_END


def acquire_prediction_spacing_window(
    db: Session,
    user_id: int,
    now_utc: datetime,
) -> bool:
    """Serialize and check the shared 30-minute prediction firing window.

    The caller must persist any allowed firing in this same transaction. The
    existing user row is the cross-worker lock, so sibling scheduler jobs and
    backend processes cannot both pass the check before either firing commits.
    Firing rows are the conservative reservation boundary: failed or delayed
    browser rendering never permits a second queued prediction burst.
    """
    locked_user_id = (
        db.query(User.user_id)
        .filter(User.user_id == user_id)
        .with_for_update()
        .scalar()
    )
    if locked_user_id is None:
        return False

    normalized_now = _as_aware_utc(now_utc).replace(tzinfo=None)
    cutoff = normalized_now - timedelta(minutes=PREDICTION_SPACING_MINUTES)

    recent_pause = (
        db.query(PausePredictionLog.firing_id)
        .filter(
            PausePredictionLog.user_id == user_id,
            PausePredictionLog.fired_at > cutoff,
        )
        .first()
    )
    if recent_pause is not None:
        return False

    recent_resume = (
        db.query(ResumePredictionLog.firing_id)
        .filter(
            ResumePredictionLog.user_id == user_id,
            ResumePredictionLog.fired_at > cutoff,
        )
        .first()
    )
    return recent_resume is None


def prediction_family_dismissed_for_session(
    db: Session,
    *,
    user_id: int,
    family: PredictionFamily,
    session_id: str,
) -> bool:
    """Return whether the authenticated browser dismissed this session family."""
    if family not in {"pause_prediction", "resume_prediction"}:
        raise ValueError(f"unsupported prediction family: {family!r}")
    if not session_id:
        return False

    return (
        db.query(NotificationLifecycleEvent.event_id)
        .filter(
            NotificationLifecycleEvent.user_id == user_id,
            NotificationLifecycleEvent.channel == "web",
            NotificationLifecycleEvent.notification_type == family,
            NotificationLifecycleEvent.session_id == session_id,
            NotificationLifecycleEvent.dismissed_at.is_not(None),
        )
        .first()
        is not None
    )
