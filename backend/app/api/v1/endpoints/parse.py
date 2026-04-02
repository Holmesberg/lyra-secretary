"""Parse endpoint — scheduled for deprecation. LLMs should call /v1/create directly."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

from app.schemas.task import TaskParseRequest, TaskParseResponse
from app.services.parser import TaskParser

router = APIRouter()
logger = logging.getLogger(__name__)


class ParseChainResponse(BaseModel):
    """Response wrapping one or more parsed tasks."""
    tasks: list[TaskParseResponse]
    compound: bool  # True if input was split on "then"


@router.post("/parse", response_model=ParseChainResponse)
async def parse_input(request: TaskParseRequest) -> ParseChainResponse:
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
            f"Parsed '{request.text}' -> {len(tasks)} task(s), compound={compound}"
        )
        return ParseChainResponse(tasks=tasks, compound=compound)

    except Exception as e:
        logger.error(f"Parse error: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail={"error": "parse_failed", "message": str(e), "confidence": 0.0}
        )
