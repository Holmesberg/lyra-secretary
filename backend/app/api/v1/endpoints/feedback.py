"""Feedback widget endpoints (alembic 040, 2026-04-28).

User submission → /v1/feedback (any authenticated user).
Operator triage → /v1/admin/feedback*  (operator-only).

Every submission fans out to email + Telegram (best-effort, non-blocking;
the feedback row commits regardless of notifier failures).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.api.deps import get_db, operator_user_from_scope
from app.db.models import Feedback, User
from app.db.scoping import get_current_user_id, set_current_user_id
from app.schemas.feedback import (
    FeedbackListResponse,
    FeedbackResolveRequest,
    FeedbackRow,
    FeedbackSubmitRequest,
    FeedbackSubmitResponse,
)
from app.services.feedback_notifier import notify_operator
from app.utils.time_utils import now_utc

router = APIRouter()
logger = logging.getLogger(__name__)


def _require_operator(db: Session, request: Request) -> User:
    return operator_user_from_scope(db, request=request)


@router.post("/feedback", response_model=FeedbackSubmitResponse)
def submit_feedback(
    request: FeedbackSubmitRequest,
    db: Session = Depends(get_db),
) -> FeedbackSubmitResponse:
    """Accept user feedback. Stores row + fans out notifications.

    Authenticated users only. Anonymous feedback could be added later
    but for the alpha cohort every user is signed in.
    """
    uid = get_current_user_id()
    user = (
        db.query(User).filter(User.user_id == uid).first() if uid else None
    )

    submitted_at = now_utc()
    row = Feedback(
        user_id=uid,
        submitted_at=submitted_at,
        kind=request.kind,
        body=request.body.strip(),
        page_url=request.page_url,
        user_agent=request.user_agent,
        error_context=request.error_context,
        status="unread",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    # Fan out — best-effort. Failures logged inside notify_operator.
    try:
        notify_operator(
            feedback_id=row.feedback_id,
            kind=row.kind,
            body=row.body,
            user_email=user.email if user else None,
            page_url=row.page_url,
            error_context=row.error_context,
        )
    except Exception as e:  # noqa: BLE001 — defensive, never fail the request
        logger.warning(f"feedback: notify_operator raised: {e}")

    return FeedbackSubmitResponse(
        feedback_id=row.feedback_id,
        submitted_at=row.submitted_at,
    )


@router.get("/admin/feedback", response_model=FeedbackListResponse)
def list_feedback(
    request: Request,
    status: Optional[str] = Query(None, description="unread | read | acted_on | dismissed | all"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> FeedbackListResponse:
    """Operator-only triage queue. Default returns last 50 ordered by
    most recent first, all statuses. Filter via ?status=unread."""
    _require_operator(db, request)
    original_uid = get_current_user_id()
    set_current_user_id(None)
    try:
        q = db.query(Feedback)
        if status and status != "all":
            q = q.filter(Feedback.status == status)
        total = q.count()
        unread_count = (
            db.query(func.count(Feedback.feedback_id))
            .filter(Feedback.status == "unread")
            .scalar()
        ) or 0
        rows = q.order_by(desc(Feedback.submitted_at)).limit(limit).all()

        items: list[FeedbackRow] = []
        for r in rows:
            email: Optional[str] = None
            if r.user_id is not None:
                u = db.query(User).filter(User.user_id == r.user_id).first()
                email = u.email if u else None
            items.append(FeedbackRow(
                feedback_id=r.feedback_id,
                user_id=r.user_id,
                user_email=email,
                submitted_at=r.submitted_at,
                kind=r.kind,
                body=r.body,
                page_url=r.page_url,
                user_agent=r.user_agent,
                error_context=r.error_context,
                status=r.status,
                operator_note=r.operator_note,
                resolved_at=r.resolved_at,
            ))

        return FeedbackListResponse(
            items=items, total=total, unread_count=int(unread_count)
        )
    finally:
        set_current_user_id(original_uid)


@router.post("/admin/feedback/{feedback_id}/resolve")
def resolve_feedback(
    feedback_id: str,
    request: FeedbackResolveRequest,
    fastapi_request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Mark a feedback row read / acted_on / dismissed.

    Disables the user-scoping filter (Feedback has user_id and would
    otherwise be filtered to operator's own rows) so the operator can
    triage rows submitted by any user.
    """
    _require_operator(db, fastapi_request)
    original_uid = get_current_user_id()
    set_current_user_id(None)
    try:
        row = db.query(Feedback).filter(Feedback.feedback_id == feedback_id).first()
        if row is None:
            raise HTTPException(status_code=404, detail="feedback not found")
        row.status = request.status
        row.operator_note = request.operator_note
        if request.status in ("acted_on", "dismissed") and row.resolved_at is None:
            row.resolved_at = now_utc()
        db.commit()
        return {
            "feedback_id": row.feedback_id,
            "status": row.status,
            "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        }
    finally:
        set_current_user_id(original_uid)
