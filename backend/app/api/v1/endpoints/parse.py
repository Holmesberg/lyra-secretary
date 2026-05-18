"""Parse endpoint — scheduled for deprecation. LLMs should call /v1/create directly."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging

from app.api.deps import get_db
from app.db.models import Deadline
from app.db.scoping import get_current_user_id
from app.schemas.task import TaskParseRequest, TaskParseResponse
from app.services.deadline_heuristic import score_deadlines
from app.services.output_surfaces import emit_surface_render
from app.services.parser import TaskParser

router = APIRouter()
logger = logging.getLogger(__name__)


class ParseChainResponse(BaseModel):
    """Response wrapping one or more parsed tasks."""
    tasks: list[TaskParseResponse]
    compound: bool  # True if input was split on "then"


class DeadlinePreviewRequest(BaseModel):
    """Inputs for the read-only Pass 2 deadline-binding preview."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class DeadlinePreviewResponse(BaseModel):
    """Result of Pass 2 inference run without creating a task.

    All four fields are None when no candidate clears the keyword-overlap
    threshold or when the user has no bindable deadlines.
    """

    deadline_id: Optional[str] = None
    deadline_title: Optional[str] = None
    deadline_match_confidence: Optional[float] = None
    deadline_match_source: Optional[str] = None
    surface_id: Optional[str] = None
    truth_class: Optional[str] = None
    signal_targets: Optional[list[str]] = None
    clean_profile: Optional[str] = None
    fallback_mode: Optional[str] = None
    exposure_id: Optional[str] = None
    render_id: Optional[str] = None


@router.post("/parse", response_model=ParseChainResponse)
def parse_input(request: TaskParseRequest) -> ParseChainResponse:
    """
    Parse natural language text into structured task data.

    Supports compound requests joined by "then":
      "Gym at 9am for 1h then shower for 20 min"
    Returns each task in order. Second and later tasks chain start times
    from the end of the previous task when no explicit time is given.

    DEPRECATED: LLMs should extract fields themselves and call /v1/create directly.
    Use this only for genuinely ambiguous time expressions.
    """
    try:
        # Deprecated OpenClaw compatibility path. Keep it pure: no user data
        # reads, no category DB lookup, no raw input logs.
        parser = TaskParser(use_db_categories=False)
        import re
        compound = bool(re.search(r'\s+then\s+', request.text, re.IGNORECASE))
        tasks = parser.parse_chained(request.text)

        logger.info(
            "Parsed task input into %s task(s), compound=%s",
            len(tasks),
            compound,
        )
        return ParseChainResponse(tasks=tasks, compound=compound)

    except Exception as e:
        logger.error("Parse error: %s", type(e).__name__, exc_info=True)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "parse_failed",
                "message": "Unable to parse task input.",
                "confidence": 0.0,
            },
        )


@router.post("/parse/deadline-preview", response_model=DeadlinePreviewResponse)
def deadline_preview(
    request: DeadlinePreviewRequest,
    db: Session = Depends(get_db),
) -> DeadlinePreviewResponse:
    """Read-only deadline suggestion. This endpoint never authorizes a
    canonical bind; it only previews a guarded candidate that the user can
    confirm or override in the NewTaskModal.
    """
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    candidates = (
        db.query(Deadline)
        .filter(
            Deadline.user_id == uid,
            Deadline.voided_at.is_(None),
            Deadline.state.in_(("planned", "active")),
        )
        .all()
    )
    if not candidates:
        return DeadlinePreviewResponse()
    match = score_deadlines(request.title, request.description, candidates)
    if not match.auto_bind or not match.candidates:
        return DeadlinePreviewResponse()
    top = match.candidates[0]
    try:
        emitted = emit_surface_render(
            db,
            surface_id="task.deadline_binding_suggestion",
            user_id=uid,
            content_snapshot={
                "copy": (
                    f"Lyra thinks this binds to {top.title} - "
                    f"{round(top.score * 100)}% match"
                ),
                "deadline_id": top.deadline_id,
                "deadline_title": top.title,
                "deadline_match_confidence": round(top.score, 3),
                "deadline_match_source": top.source,
            },
            content_template_id="deadline_binding_suggestion",
            initiative="system",
            trigger_source="parse.deadline_preview",
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.warning(
            "Suppressed deadline binding suggestion because exposure logging failed",
            exc_info=True,
        )
        return DeadlinePreviewResponse()

    return DeadlinePreviewResponse(
        deadline_id=top.deadline_id,
        deadline_title=top.title,
        deadline_match_confidence=round(top.score, 3),
        deadline_match_source=top.source,
        surface_id=emitted["surface_id"],
        truth_class=emitted["truth_class"],
        signal_targets=emitted["signal_targets"],
        clean_profile=emitted["clean_profile"],
        fallback_mode=emitted["fallback_mode"],
        exposure_id=emitted["exposure_id"],
        render_id=emitted["render_id"],
    )
