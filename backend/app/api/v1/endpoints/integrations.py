"""Unified per-user integration status.

Thin seam that returns one row per supported integration with its
current connection state for the requesting user. Frontend's
Integrations panel renders from this list — the declarative registry
in `frontend/lib/integrations.ts` decides order and copy, the backend
decides status + availability.

Why this exists (2026-04-22): the original design stored each
integration's state on the `user` row (`google_refresh_token`,
`notion_enabled`). That works for 2 integrations, breaks by 5. This
endpoint introduces the forward-compatible shape today — callers see
a typed list — so when we later move to a generic
`integration_connection` table, only the query inside this function
changes. See docs/integrations_architecture.md §Status Endpoint.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import User
from app.db.scoping import get_current_user_id

router = APIRouter()


def _current_user(db: Session) -> User:
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    user = db.query(User).filter(User.user_id == uid).first()
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    return user


@router.get("/integrations")
def list_integrations(db: Session = Depends(get_db)) -> dict[str, Any]:
    """List every integration the panel might render with per-user state.

    Status values:
      - 'connected'    — credentials on file, integration actively syncing
      - 'disconnected' — available to connect but not currently linked
      - 'coming_soon'  — displayed as a preview; no connect action yet

    Availability decides whether the frontend renders a Connect button
    vs. a dim "Coming soon" tile. The registry on the frontend is the
    source of truth for human-readable name / description / icon; this
    endpoint only speaks to state.
    """
    user = _current_user(db)

    google_calendar_status = (
        "connected" if user.google_refresh_token else "disconnected"
    )

    # Notion write-direction sync is shipped but operator-only. All
    # non-operator users see it as "Coming soon" — we're building user-
    # facing Notion (schema-mapping UI, OAuth) in Phase 7+. When that
    # lands, the `available` branch collapses and this returns real
    # connected/disconnected per user.
    notion_status = "coming_soon"

    # ICS file/URL import is the Phase 7+ Priority 1 integration per
    # docs/import_integrations_capability_map.md. No backend state yet.
    ics_status = "coming_soon"

    return {
        "integrations": [
            {
                "id": "google_calendar",
                "status": google_calendar_status,
                "available": True,
                "scopes": ["https://www.googleapis.com/auth/calendar.readonly"],
            },
            {
                "id": "notion",
                "status": notion_status,
                "available": False,
                "scopes": ["pages:read", "databases:read"],
            },
            {
                "id": "ics",
                "status": ics_status,
                "available": False,
                "scopes": [],
            },
        ]
    }
