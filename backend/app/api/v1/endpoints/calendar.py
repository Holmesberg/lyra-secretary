"""Google Calendar read-only integration endpoints.

Path B (2026-04-21). Operator's spec: import user's primary Google
Calendar events as ambient scheduling context. Never persisted to the
task table — fetched on demand, Redis-cached 60s. See
`services/calendar_sync.py` for the sync service and
`docs/strategic_decisions_april_21.md` §6 for the research-integrity
note.

Graceful degradation: any user without a stored refresh_token (hasn't
granted calendar scope OR revoked access) gets an empty event list.
This is not an error — the /calendar UI simply shows Lyra tasks
without external events.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import User
from app.db.scoping import get_current_user_id
from app.services.calendar_sync import fetch_google_events

router = APIRouter()


def _parse_iso_date(s: Optional[str]) -> Optional[datetime]:
    if s is None:
        return None
    try:
        # Accept both "YYYY-MM-DD" and full ISO
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None


@router.get("/calendar/events")
def get_calendar_events(
    db: Session = Depends(get_db),
    date_from: Optional[str] = Query(None, description="ISO date or datetime"),
    date_to: Optional[str] = Query(None, description="ISO date or datetime"),
):
    """Return Google Calendar events for the current user.

    Window defaults: now - 1 day to now + 30 days (covers Spring School
    + next sprint). Short horizon keeps single events.list call within
    pagination limits and matches the typical /calendar view zoom.
    """
    uid = get_current_user_id()
    if uid is None:
        return {"events": [], "source": "google", "connected": False}

    user = db.query(User).filter(User.user_id == uid).first()
    if user is None or not user.google_refresh_token:
        return {"events": [], "source": "google", "connected": False}

    now = datetime.utcnow()
    start = _parse_iso_date(date_from) or (now - timedelta(days=1))
    end = _parse_iso_date(date_to) or (now + timedelta(days=30))
    # Defensive: if caller inverted the range, swap rather than call
    # Google with a bogus window (returns a 400).
    if start > end:
        start, end = end, start

    events = fetch_google_events(uid, start, end)
    return {
        "events": [e.__dict__ for e in events],
        "source": "google",
        "connected": True,
        "window": {
            "from": start.isoformat(),
            "to": end.isoformat(),
        },
    }
