"""Stopwatch endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.api.deps import get_db
from app.schemas.stopwatch import (
    StopwatchStartRequest,
    StopwatchStartResponse,
    StopwatchStopResponse,
    StopwatchStatusResponse,
)
from app.services.stopwatch_manager import StopwatchManager, StopwatchAlreadyRunningError, NoActiveStopwatchError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/start", response_model=StopwatchStartResponse)
async def start_stopwatch(
    request: StopwatchStartRequest,
    db: Session = Depends(get_db)
) -> StopwatchStartResponse:
    """Start stopwatch."""
    try:
        manager = StopwatchManager(db)
        
        session, task, is_future_task = manager.start(
            task_id=request.task_id,
            title=request.title
        )
        
        return StopwatchStartResponse(
            session_id=session.session_id,
            task_id=task.task_id,
            start_time=session.start_time_utc,
            is_future_task=is_future_task,
            planned_start=task.planned_start_utc
        )
        
    except StopwatchAlreadyRunningError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stopwatch start error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=StopwatchStopResponse)
async def stop_stopwatch(
    db: Session = Depends(get_db)
) -> StopwatchStopResponse:
    """Stop active stopwatch."""
    try:
        manager = StopwatchManager(db)
        
        session, task, is_early_stop, notion_synced = manager.stop()
        
        return StopwatchStopResponse(
            task_id=task.task_id,
            session_id=session.session_id,
            duration_minutes=task.executed_duration_minutes,
            planned_duration_minutes=task.planned_duration_minutes,
            delta_minutes=task.duration_delta_minutes,
            executed_at=task.executed_end_utc,
            is_early_stop=is_early_stop,
            notion_synced=notion_synced
        )
        
    except NoActiveStopwatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stopwatch stop error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=StopwatchStatusResponse)
async def stopwatch_status(
    db: Session = Depends(get_db)
) -> StopwatchStatusResponse:
    """Get stopwatch status."""
    try:
        manager = StopwatchManager(db)
        status = manager.get_status()
        
        if status:
            return StopwatchStatusResponse(**status)
        else:
            return StopwatchStatusResponse(active=False)
            
    except Exception as e:
        logger.error(f"Stopwatch status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
