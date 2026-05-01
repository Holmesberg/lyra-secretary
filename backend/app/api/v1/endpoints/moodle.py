"""Moodle LMS integration endpoints.

Wire-up for the .ics subscription flow (alembic 041, 2026-04-29). The
sync service lives in `services/moodle_ics_sync.py`; these endpoints
are thin transport adapters: validate, store, kick a sync, return
counts.

Endpoints:
  POST /v1/integrations/moodle/preview     — try-before-buy parse
  POST /v1/integrations/moodle/connect     — store URL + immediate sync
  POST /v1/integrations/moodle/sync-now    — manual refresh
  DELETE /v1/integrations/moodle/disconnect — clear URL (+ optional void)

Credential discipline: never echo `moodle_ics_url` in any API response
(redacted "url_on_file: true/false" only). Errors include status codes
but never the URL.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Deadline, User
from app.db.scoping import get_current_user_id
from app.services import moodle_ics_sync, moodle_submissions_sync
from app.utils.time_utils import now_utc

router = APIRouter()


def _current_user(db: Session) -> User:
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    user = db.query(User).filter(User.user_id == uid).first()
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    return user


class MoodleConnectIn(BaseModel):
    ics_url: str


class MoodlePreviewIn(BaseModel):
    ics_url: str


class MoodleDisconnectIn(BaseModel):
    # If True, also void all currently-imported deadlines for this user.
    # Default False — user keeps the imported deadlines as Lyra-owned
    # rows; only the URL link is severed. This matches "I'm done with
    # auto-sync but I want to keep the deadlines I already have."
    void_imported: bool = False


def _serialize_event(event: moodle_ics_sync.ParsedEvent) -> dict[str, Any]:
    """Compact frontend-safe shape for preview rendering."""
    return {
        "external_id": event.external_uid,
        "title": event.title,
        "due_at_utc": event.due_at_utc.isoformat(),
        "category_hint": event.category_hint,
    }


@router.post("/integrations/moodle/preview")
def post_moodle_preview(body: MoodlePreviewIn) -> dict[str, Any]:
    """Parse an iCal URL without persisting. Used by the connect modal
    so users see what will be imported before they commit."""
    if get_current_user_id() is None:
        raise HTTPException(status_code=401, detail="not authenticated")

    shape_error = moodle_ics_sync.validate_url_shape(body.ics_url)
    if shape_error is not None:
        raise HTTPException(status_code=400, detail=shape_error)

    events, error = moodle_ics_sync.preview(body.ics_url)
    if error is not None:
        return {
            "ok": False,
            "error": error,
            "count": 0,
            "sample": [],
        }
    # Frontend renders a sample of up to 5 — full count returned for
    # the "found N items" copy.
    return {
        "ok": True,
        "error": None,
        "count": len(events),
        "sample": [_serialize_event(e) for e in events[:5]],
    }


@router.post("/integrations/moodle/connect")
def post_moodle_connect(
    body: MoodleConnectIn, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Store the URL + run an immediate sync. Idempotent — re-connecting
    with the same URL is a no-op fetch + upsert pass."""
    user = _current_user(db)

    shape_error = moodle_ics_sync.validate_url_shape(body.ics_url)
    if shape_error is not None:
        raise HTTPException(status_code=400, detail=shape_error)

    # Validate the URL with one live fetch BEFORE persisting.
    events, fetch_error = moodle_ics_sync.preview(body.ics_url)
    if fetch_error is not None:
        raise HTTPException(
            status_code=400, detail=f"connect_failed: {fetch_error}"
        )

    user.moodle_ics_url = body.ics_url.strip()
    user.moodle_disconnect_reason = None
    db.commit()

    # Run the real sync now so deadlines are visible immediately.
    result = moodle_ics_sync.sync_user(user.user_id, db)

    return {
        "ok": True,
        "preview_count": len(events),
        "sync": {
            "fetched": result.fetched,
            "created": result.created,
            "updated": result.updated,
            "unchanged": result.unchanged,
            "skipped_voided": result.skipped_voided,
            "skipped_unparseable": result.skipped_unparseable,
            "error": result.error,
        },
    }


@router.post("/integrations/moodle/sync-now")
def post_moodle_sync_now(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Manual refresh — same as the scheduled job, on demand."""
    user = _current_user(db)
    if not user.moodle_ics_url:
        raise HTTPException(
            status_code=400, detail="moodle_not_connected"
        )
    result = moodle_ics_sync.sync_user(user.user_id, db)
    return {
        "ok": result.error is None,
        "fetched": result.fetched,
        "created": result.created,
        "updated": result.updated,
        "unchanged": result.unchanged,
        "skipped_voided": result.skipped_voided,
        "skipped_unparseable": result.skipped_unparseable,
        "error": result.error,
    }


@router.delete("/integrations/moodle/disconnect")
def delete_moodle_disconnect(
    body: Optional[MoodleDisconnectIn] = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Clear the stored URL. Optionally void all imported deadlines."""
    user = _current_user(db)
    void_imported = bool(body and body.void_imported)

    user.moodle_ics_url = None
    user.moodle_disconnect_reason = None
    user.moodle_last_synced_at = None

    voided_count = 0
    if void_imported:
        # Void every imported (non-voided) deadline. State stays as-is;
        # voided_at is the soft-delete signal per voided_at_guard memory.
        rows = (
            db.query(Deadline)
            .filter(
                Deadline.user_id == user.user_id,
                Deadline.external_source == "moodle_ics",
                Deadline.voided_at.is_(None),
            )
            .all()
        )
        ts = now_utc()
        for row in rows:
            row.voided_at = ts
            voided_count += 1

    db.commit()
    return {
        "ok": True,
        "voided_imported_count": voided_count,
    }


# ---------------------------------------------------------------------------
# Web Services token endpoints (Phase B 2026-05-01)
# ---------------------------------------------------------------------------


class MoodleWSConnectIn(BaseModel):
    """Operator-supplied Moodle Web Services token. 32-char hex
    (Moodle's standard length); stored plaintext per existing trust
    class for moodle_ics_url + google_refresh_token."""
    ws_token: str
    base_url: Optional[str] = None  # falls back to env MOODLE_WS_BASE_URL


@router.post("/integrations/moodle/ws-connect")
def post_moodle_ws_connect(
    body: MoodleWSConnectIn, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Store the Moodle Web Services token. Validates by hitting
    `core_webservice_get_site_info` once before persisting — bad
    tokens fail with 400 and never reach the DB."""
    user = _current_user(db)
    token = body.ws_token.strip()
    if len(token) < 16:  # Moodle tokens are 32 chars; sanity floor
        raise HTTPException(status_code=400, detail="ws_token_too_short")

    # Resolve base URL: explicit body param wins, else env, else
    # require operator to have it set somewhere.
    import os
    base_url = (body.base_url or os.environ.get("MOODLE_WS_BASE_URL", "")).strip()
    if not base_url:
        raise HTTPException(
            status_code=400,
            detail="moodle_ws_base_url_missing — set MOODLE_WS_BASE_URL env or pass base_url in request",
        )

    # Validate the token live before persisting.
    import httpx
    try:
        r = httpx.get(
            f"{base_url.rstrip('/')}/webservice/rest/server.php",
            params={
                "wstoken": token,
                "wsfunction": "core_webservice_get_site_info",
                "moodlewsrestformat": "json",
            },
            timeout=10.0, follow_redirects=True,
        )
        r.raise_for_status()
        body_json = r.json()
        if isinstance(body_json, dict) and body_json.get("exception"):
            raise HTTPException(
                status_code=400,
                detail=f"ws_token_rejected: {body_json.get('errorcode', '?')}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"ws_validation_failed: {type(e).__name__}",
        )

    user.moodle_ws_token = token
    user.moodle_ws_disconnect_reason = None
    db.commit()
    return {"ok": True}


@router.post("/integrations/moodle/ws-sync-now")
def post_moodle_ws_sync_now(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Manual one-shot run of the submission detection sync.

    Same code path the APScheduler job uses, just on-demand. Returns
    a summary of marks applied; mirrors to operator-Telegram if any
    deadlines flipped to completed.
    """
    user = _current_user(db)
    if not user.moodle_ws_token:
        raise HTTPException(status_code=400, detail="moodle_ws_not_connected")

    import os
    base_url = os.environ.get("MOODLE_WS_BASE_URL", "")
    if not base_url:
        raise HTTPException(
            status_code=500, detail="moodle_ws_base_url_missing"
        )

    result = moodle_submissions_sync.sync_user(user, base_url, db)
    db.commit()

    # Telegram fanout if anything changed (operator-only — mirrors
    # the existing scheduler.moodle pattern, prevents non-operator
    # noise post-multi-user expansion).
    if user.is_operator and result.marked_complete:
        from app.services.operator_notifier import notify_operator
        notify_operator(
            f"Moodle submissions sync — auto-marked *{result.marked_complete}* deadline(s) complete:\n"
            + "\n".join(f"• {t}" for t in result.marked_titles),
            source="moodle.ws-sync",
            severity="info",
        )

    return {
        "ok": result.error is None,
        "matched": result.matched,
        "marked_complete": result.marked_complete,
        "skipped_no_match": result.skipped_no_match,
        "skipped_not_submitted": result.skipped_not_submitted,
        "marked_titles": result.marked_titles,
        "error": result.error,
    }


@router.delete("/integrations/moodle/ws-disconnect")
def delete_moodle_ws_disconnect(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Clear the WS token. Does NOT void any deadlines — that's the
    iCal disconnect's job; WS is purely a submission-detection layer."""
    user = _current_user(db)
    user.moodle_ws_token = None
    user.moodle_ws_last_synced_at = None
    user.moodle_ws_disconnect_reason = None
    db.commit()
    return {"ok": True}
