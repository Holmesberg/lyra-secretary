"""Stopwatch endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import logging

from app.api.deps import get_db
from app.schemas.stopwatch import (
    StopwatchStartRequest,
    StopwatchStartResponse,
    StopwatchStopRequest,
    StopwatchStopResponse,
    StopwatchPauseResponse,
    StopwatchResumeResponse,
    StopwatchStatusResponse,
)
from app.services.stopwatch_manager import (
    StopwatchManager,
    StopwatchAlreadyRunningError,
    StopwatchAlreadyPausedError,
    StopwatchNotPausedError,
    NoActiveStopwatchError,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/start", response_model=StopwatchStartResponse)
async def start_stopwatch(
    request: StopwatchStartRequest,
    db: Session = Depends(get_db),
) -> StopwatchStartResponse:
    """Start stopwatch. Optionally pass pre_task_readiness (1–5) in body."""
    try:
        manager = StopwatchManager(db)
        session, task, is_future_task = manager.start(
            task_id=request.task_id,
            title=request.title,
            pre_task_readiness=request.pre_task_readiness,
        )
        return StopwatchStartResponse(
            session_id=session.session_id,
            task_id=task.task_id,
            start_time=session.start_time_utc,
            is_future_task=is_future_task,
            planned_start=task.planned_start_utc,
            pre_task_readiness=task.pre_task_readiness,
            initiation_delay_minutes=task.initiation_delay_minutes,
        )
    except StopwatchAlreadyRunningError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stopwatch start error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause", response_model=StopwatchPauseResponse)
async def pause_stopwatch(db: Session = Depends(get_db)) -> StopwatchPauseResponse:
    """
    Pause the active stopwatch. Use during prayer, breaks, or interruptions.
    Paused time is excluded from executed_duration and delta on stop.
    """
    try:
        manager = StopwatchManager(db)
        result = manager.pause()
        return StopwatchPauseResponse(**result)
    except NoActiveStopwatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StopwatchAlreadyPausedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stopwatch pause error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume", response_model=StopwatchResumeResponse)
async def resume_stopwatch(db: Session = Depends(get_db)) -> StopwatchResumeResponse:
    """
    Resume a paused stopwatch. Reports how many minutes were paused.
    """
    try:
        manager = StopwatchManager(db)
        result = manager.resume()
        return StopwatchResumeResponse(**result)
    except NoActiveStopwatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StopwatchNotPausedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stopwatch resume error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=StopwatchStopResponse)
async def stop_stopwatch(
    request: StopwatchStopRequest = None,
    confirmed: bool = Query(False, description="Set to true to confirm early stop"),
    db: Session = Depends(get_db),
) -> StopwatchStopResponse:
    """
    Stop active stopwatch. Requires ?confirmed=true if stopping before 50% of planned duration.
    If paused when stop is called, auto-resumes first and counts final pause in deduction.
    """
    if request is None:
        request = StopwatchStopRequest()

    try:
        manager = StopwatchManager(db)

        is_early, elapsed, planned = manager.check_early_stop()
        if is_early and not confirmed:
            return StopwatchStopResponse(
                task_id="",
                session_id="",
                duration_minutes=elapsed,
                planned_duration_minutes=planned,
                delta_minutes=None,
                executed_at=datetime.utcnow(),
                is_early_stop=True,
                requires_confirmation=True,
                confirmation_message=(
                    f"Only {elapsed} min of active work of {planned} planned. "
                    f"Call stop again with ?confirmed=true to confirm completion."
                ),
            )

        session, task, is_early_stop, notion_synced = manager.stop(
            post_task_reflection=request.post_task_reflection,
        )
        return StopwatchStopResponse(
            task_id=task.task_id,
            session_id=session.session_id,
            duration_minutes=task.executed_duration_minutes,
            planned_duration_minutes=task.planned_duration_minutes,
            delta_minutes=task.duration_delta_minutes,
            executed_at=task.executed_end_utc,
            is_early_stop=is_early_stop,
            notion_synced=notion_synced,
            post_task_reflection=task.post_task_reflection,
            discrepancy_score=task.discrepancy_score,
        )

    except NoActiveStopwatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stopwatch stop error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=StopwatchStatusResponse)
async def stopwatch_status(db: Session = Depends(get_db)) -> StopwatchStatusResponse:
    """Get stopwatch status. Includes paused state and total paused minutes."""
    try:
        manager = StopwatchManager(db)
        status = manager.get_status()
        return StopwatchStatusResponse(**status) if status else StopwatchStatusResponse(active=False)
    except Exception as e:
        logger.error(f"Stopwatch status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
