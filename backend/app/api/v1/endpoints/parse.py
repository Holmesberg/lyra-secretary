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
from app.services.parser import TaskParser, infer_deadline_binding

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
    deadline_match_source: Optional[str] = None  # "parser_auto" when matched


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
        parser = TaskParser()
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
    """Read-only Pass 2 inference. Mirrors what TaskManager.create_task would
    pick if this title+description were submitted, without writing a task.

    Powers the NewTaskModal's deadline-suggestion UX (Loop 11 Phase K). The
    asymmetric token-overlap math + 0.5 threshold + earliest-due tiebreak
    all come from `infer_deadline_binding` so the preview never disagrees
    with what creation would actually bind.
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
    match = infer_deadline_binding(request.title, candidates)
    if match is None:
        return DeadlinePreviewResponse()
    deadline, confidence = match
    return DeadlinePreviewResponse(
        deadline_id=deadline.deadline_id,
        deadline_title=deadline.title,
        deadline_match_confidence=round(confidence, 3),
        deadline_match_source="parser_auto",
    )
