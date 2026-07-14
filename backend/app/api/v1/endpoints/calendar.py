"""Google Calendar read-only integration endpoints.

Path B (2026-04-21). Operator's spec: import user's primary Google
Calendar events as ambient scheduling context. Never persisted to the
task table — fetched on demand, Redis-cached 60s. See
`services/calendar_sync.py` for the sync service and
`docs/strategic_decisions_april_21.md` §6 for the research-integrity
note.

Graceful degradation: any user without a stored refresh_token (hasn't
granted calendar scope OR revoked access) gets an empty event list.
This is not an error — the /calendar UI simply shows LyraOS tasks
without external events.

Attendance endpoint (POST /v1/calendar/attendance): the "Did you
attend?" yes/no on /today cards writes to ExternalEventOutcome. Not
a Task row — keeps research integrity (H1 test set stays
LyraOS-native). Same-day GET /v1/calendar/events response joins the
outcome per event so the UI knows which button state to render.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import ExternalEventOutcome, User
from app.db.scoping import get_current_user_id
from app.services.calendar_sync import fetch_google_events
from app.utils.time_utils import now_utc

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

    # Join user-marked attendance outcomes for this window's events. One
    # query, indexed by (user_id, external_source, external_id). For
    # events with no row, the frontend renders the "Did you attend?"
    # buttons; for events with a row, it renders the locked-in state.
    event_ids = [e.id for e in events]
    outcome_rows = (
        db.query(ExternalEventOutcome)
        .filter(ExternalEventOutcome.user_id == uid)
        .filter(ExternalEventOutcome.external_source == "google_calendar")
        .filter(ExternalEventOutcome.external_id.in_(event_ids) if event_ids else False)
        .all()
    ) if event_ids else []
    outcome_by_id = {r.external_id: r.outcome for r in outcome_rows}

    enriched = []
    for e in events:
        payload = e.__dict__.copy()
        payload["outcome"] = outcome_by_id.get(e.id)  # 'attended' | 'skipped' | None
        enriched.append(payload)

    return {
        "events": enriched,
        "source": "google",
        "connected": True,
        "window": {
            "from": start.isoformat(),
            "to": end.isoformat(),
        },
    }


class AttendanceIn(BaseModel):
    external_id: str
    outcome: str  # 'attended' | 'skipped' | 'unknown' (clears row)
    event_title: Optional[str] = None
    event_start_utc: Optional[str] = None  # ISO; snapshot at mark time
    event_end_utc: Optional[str] = None
    external_source: str = "google_calendar"


@router.post("/calendar/attendance")
def post_attendance(body: AttendanceIn, db: Session = Depends(get_db)):
    """Upsert the user's attendance outcome on an external calendar event.

    `outcome='attended' | 'skipped'` sets the row; `outcome='unknown'`
    clears it (user reverts their answer). Snapshots event_title +
    start/end at mark time so the signal stays interpretable even if
    the user later edits the event in Google Calendar.

    Never creates a Task row. The `task` table stays LyraOS-native
    (H1 research-integrity constraint pre-registered in
    docs/strategic_decisions_april_21.md §6 + VT-23).
    """
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    if body.outcome not in ("attended", "skipped", "unknown"):
        raise HTTPException(status_code=400, detail="outcome must be attended|skipped|unknown")

    # Find existing row (unique on user_id + external_source + external_id).
    existing = (
        db.query(ExternalEventOutcome)
        .filter(ExternalEventOutcome.user_id == uid)
        .filter(ExternalEventOutcome.external_source == body.external_source)
        .filter(ExternalEventOutcome.external_id == body.external_id)
        .first()
    )

    if body.outcome == "unknown":
        # Revert — delete any existing row. No-op if none.
        if existing:
            db.delete(existing)
            db.commit()
        return {"ok": True, "outcome": None}

    # Parse snapshot timestamps if supplied. Naive Cairo-local ISO per
    # project timezone contract (matches how fetch_google_events emits
    # them back to the frontend).
    def _parse(s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    if existing:
        existing.outcome = body.outcome
        existing.event_title = body.event_title or existing.event_title
        existing.event_start_utc = _parse(body.event_start_utc) or existing.event_start_utc
        existing.event_end_utc = _parse(body.event_end_utc) or existing.event_end_utc
        existing.marked_at = now_utc()
    else:
        db.add(
            ExternalEventOutcome(
                user_id=uid,
                external_source=body.external_source,
                external_id=body.external_id,
                outcome=body.outcome,
                event_title=body.event_title,
                event_start_utc=_parse(body.event_start_utc),
                event_end_utc=_parse(body.event_end_utc),
                marked_at=now_utc(),
            )
        )
    db.commit()
    return {"ok": True, "outcome": body.outcome}
