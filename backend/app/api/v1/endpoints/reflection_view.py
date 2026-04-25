"""reflection_view_log dwell-tracking callbacks (LYR-098 Commit 2b).

Two endpoints let the frontend stamp when the user actually saw a
surface and when they dismissed it. Both lookups flow through the
scoping hook (`app.db.scoping.install_scoping`), which auto-filters by
the current user's id — user 98 cannot stamp user 99's row even if the
view_id leaks, because the scoping hook injects
`WHERE user_id = <current>` into every ORM query against
ReflectionViewLog. That protection is covered by
`tests/test_multiuser_isolation_adversarial.py`.

Both endpoints are idempotent: re-POST after the first stamp is a
no-op (first-wins). That matches toast/modal dismissal semantics where
a flaky network retry shouldn't corrupt the dwell window.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import ReflectionViewLog
from app.utils.time_utils import now_utc

router = APIRouter()


@router.post("/reflection_view/{view_id}/viewed")
def mark_viewed(view_id: str, db: Session = Depends(get_db)) -> dict:
    """Stamp viewed_at. First-view wins (idempotent)."""
    row = (
        db.query(ReflectionViewLog)
        .filter(ReflectionViewLog.view_id == view_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="view_id not found")
    if row.viewed_at is None:
        row.viewed_at = now_utc()
        db.commit()
    return {
        "viewed": True,
        "view_id": view_id,
        "viewed_at": row.viewed_at,
    }


@router.post("/reflection_view/{view_id}/dismissed")
def mark_dismissed(view_id: str, db: Session = Depends(get_db)) -> dict:
    """Stamp dismissed_at; if viewed_at is set, compute dwell_seconds.
    First-dismiss wins (idempotent)."""
    row = (
        db.query(ReflectionViewLog)
        .filter(ReflectionViewLog.view_id == view_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="view_id not found")
    if row.dismissed_at is None:
        row.dismissed_at = now_utc()
        if row.viewed_at is not None:
            row.dwell_seconds = int(
                (row.dismissed_at - row.viewed_at).total_seconds()
            )
        db.commit()
    return {
        "dismissed": True,
        "view_id": view_id,
        "dismissed_at": row.dismissed_at,
        "dwell_seconds": row.dwell_seconds,
    }
