"""Parse endpoint."""
from fastapi import APIRouter, HTTPException
import logging

from app.schemas.parse import ParseRequest, ParseResponse
from app.schemas.task import TaskParseRequest, TaskParseResponse
from app.services.parser import TaskParser

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/parse", response_model=TaskParseResponse)
async def parse_input(request: TaskParseRequest) -> TaskParseResponse:
    """
    Parse natural language text into structured task data.
    
    This is stateless - nothing is persisted.
    OpenClaw calls this to understand intent,
    then calls /tasks/create to commit.
    
    Examples:
        - "Gym at 9am"
        - "Study AI 2-3 hours tonight"
        - "Meeting tomorrow at 2pm"
    """
    try:
        parser = TaskParser()
        result = parser.parse(request.text)
        
        logger.info(
            f"Parsed '{request.text}' -> {result.title} "
            f"(confidence: {result.confidence:.2f})"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Parse error: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "parse_failed",
                "message": str(e),
                "confidence": 0.0
            }
        )
