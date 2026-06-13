"""Deadline CRUD endpoints (Phase F of Loop 11, 2026-04-26).

Routes:
    POST   /v1/deadlines              — create
    GET    /v1/deadlines               — list (optional ?state filter)
    GET    /v1/deadlines/{id}          — get one
    PUT    /v1/deadlines/{id}          — update fields and/or state
    DELETE /v1/deadlines/{id}          — soft-delete (voided_at)

All endpoints scoped to current_user_id via ContextVar (set by auth
middleware). Cross-user access returns 404 (not 403) to avoid leaking
existence signal.

ValueError from DeadlineManager → HTTP 400 (or 404 for not-found).
RuntimeError (no current_user_id) → HTTP 401 via the standard catch-all.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.deadline import (
    DeadlineCreateRequest,
    DeadlineListResponse,
    DeadlineResponse,
    DeadlineUpdateRequest,
)
from app.services.deadline_manager import DeadlineDuplicateError, DeadlineManager

logger = logging.getLogger(__name__)

router = APIRouter()


def _value_error_to_http(e: ValueError) -> HTTPException:
    """Map DeadlineManager ValueError variants to appropriate HTTP codes."""
    if isinstance(e, DeadlineDuplicateError):
        existing = e.existing
        return HTTPException(
            status_code=409,
            detail={
                "error": "deadline_duplicate_title_same_day",
                "message": (
                    f"A deadline named '{existing.title}' already exists on "
                    "that due date. Review it or create anyway."
                ),
                "existing_deadline_id": existing.deadline_id,
                "existing_title": existing.title,
                "existing_due_at_utc": existing.due_at_utc.isoformat()
                if existing.due_at_utc
                else None,
            },
        )
    msg = str(e)
    if "deadline_not_found" in msg:
        return HTTPException(status_code=404, detail={"error": "deadline_not_found", "message": msg})
    return HTTPException(status_code=400, detail={"error": msg.split(":", 1)[0], "message": msg})


@router.post("/deadlines", response_model=DeadlineResponse, status_code=201)
def create_deadline(
    request: DeadlineCreateRequest,
    db: Session = Depends(get_db),
) -> DeadlineResponse:
    """Create a new deadline. Initial state is 'planned'."""
    manager = DeadlineManager(db)
    try:
        deadline = manager.create_deadline(
            title=request.title,
            description=request.description,
            due_at_utc=request.due_at_utc,
            category_hint=request.category_hint,
            force_duplicate=request.force_duplicate,
        )
        return DeadlineResponse.from_orm(deadline)
    except ValueError as e:
        raise _value_error_to_http(e)
    except RuntimeError as e:
        # No current_user_id → not authenticated
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/deadlines", response_model=DeadlineListResponse)
def list_deadlines(
    state: Optional[str] = Query(None, description="Filter by state"),
    include_voided: bool = Query(False, description="Include soft-deleted deadlines"),
    db: Session = Depends(get_db),
) -> DeadlineListResponse:
    """List the current user's deadlines, ordered by due_at_utc ascending."""
    manager = DeadlineManager(db)
    try:
        deadlines = manager.list_deadlines(state=state, include_voided=include_voided)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return DeadlineListResponse(
        deadlines=[DeadlineResponse.from_orm(d) for d in deadlines],
        total=len(deadlines),
    )


@router.get("/deadlines/{deadline_id}", response_model=DeadlineResponse)
def get_deadline(
    deadline_id: str,
    db: Session = Depends(get_db),
) -> DeadlineResponse:
    """Get one deadline by id (scoped to current user)."""
    manager = DeadlineManager(db)
    try:
        deadline = manager.get_deadline(deadline_id)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    if deadline is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "deadline_not_found", "message": f"deadline_not_found: {deadline_id}"},
        )
    return DeadlineResponse.from_orm(deadline)


@router.put("/deadlines/{deadline_id}", response_model=DeadlineResponse)
def update_deadline(
    deadline_id: str,
    request: DeadlineUpdateRequest,
    db: Session = Depends(get_db),
) -> DeadlineResponse:
    """Update editable fields and/or trigger a state transition.

    Allowed user-driven transitions:
        planned → active | completed | skipped
        active  → completed | skipped
        missed  → completed | planned

    Completed/skipped can reopen to planned for self-service correction.
    Use DELETE /v1/deadlines/{id} to soft-delete instead.
    """
    manager = DeadlineManager(db)
    try:
        deadline = manager.update_deadline(
            deadline_id=deadline_id,
            title=request.title,
            description=request.description,
            due_at_utc=request.due_at_utc,
            category_hint=request.category_hint,
            state=request.state,
        )
        return DeadlineResponse.from_orm(deadline)
    except ValueError as e:
        raise _value_error_to_http(e)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.delete("/deadlines/{deadline_id}", status_code=204)
def void_deadline(
    deadline_id: str,
    db: Session = Depends(get_db),
):
    """Soft-delete a deadline by setting voided_at.

    Idempotent: voiding an already-voided deadline returns 204 silently.
    Bound tasks keep their deadline_id (FK is nullable; no cascade).
    """
    manager = DeadlineManager(db)
    try:
        manager.void_deadline(deadline_id)
    except ValueError as e:
        raise _value_error_to_http(e)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return None
