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
    StopwatchPauseRequest,
    StopwatchPauseResponse,
    StopwatchResumeResponse,
    StopwatchStatusResponse,
    ReadinessCorrectionRequest,
    ReadinessCorrectionResponse,
    RetroactiveRequest,
    RetroactiveResponse,
    PAUSE_REASONS,
    PAUSE_INITIATORS,
)
from app.services.stopwatch_manager import (
    StopwatchManager,
    StopwatchAlreadyRunningError,
    StopwatchAlreadyPausedError,
    StopwatchNotPausedError,
    NoActiveStopwatchError,
)
from app.services.task_manager import TaskManager
from app.utils.time_utils import to_local

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
            start_time=to_local(session.start_time_utc),
            is_future_task=is_future_task,
            planned_start=to_local(task.planned_start_utc),
            pre_task_readiness=task.pre_task_readiness,
            initiation_delay_minutes=task.initiation_delay_minutes,
        )
    except StopwatchAlreadyRunningError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stopwatch start error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause", response_model=StopwatchPauseResponse)
async def pause_stopwatch(
    request: StopwatchPauseRequest = None,
    db: Session = Depends(get_db),
) -> StopwatchPauseResponse:
    """
    Pause the active stopwatch. Use during prayer, breaks, or interruptions.
    Paused time is excluded from executed_duration and delta on stop.

    Optional body: pause_reason (mental_fatigue|distraction|task_difficulty|
    external_interruption|intentional_break|prayer), pause_initiator (self|external).
    """
    if request is None:
        request = StopwatchPauseRequest()

    # Validate enums if provided
    if request.pause_reason and request.pause_reason not in PAUSE_REASONS:
        raise HTTPException(status_code=400, detail=f"Invalid pause_reason. Must be one of: {', '.join(sorted(PAUSE_REASONS))}")
    if request.pause_initiator and request.pause_initiator not in PAUSE_INITIATORS:
        raise HTTPException(status_code=400, detail=f"Invalid pause_initiator. Must be one of: {', '.join(sorted(PAUSE_INITIATORS))}")

    try:
        manager = StopwatchManager(db)
        result = manager.pause(
            pause_reason=request.pause_reason,
            pause_initiator=request.pause_initiator,
        )
        result["paused_at"] = to_local(result["paused_at"])
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
                executed_at=to_local(datetime.utcnow()),
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
            executed_at=to_local(task.executed_end_utc),
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
        if status and status.get("start_time"):
            status["start_time"] = to_local(status["start_time"])
        return StopwatchStatusResponse(**status) if status else StopwatchStatusResponse(active=False)
    except Exception as e:
        logger.error(f"Stopwatch status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/correct-readiness", response_model=ReadinessCorrectionResponse)
async def correct_readiness(
    request: ReadinessCorrectionRequest,
    db: Session = Depends(get_db),
) -> ReadinessCorrectionResponse:
    """
    Correct pre_task_readiness on the active session. No time limit —
    works any time while the stopwatch is running. Logs original value.
    """
    try:
        manager = StopwatchManager(db)
        result = manager.correct_readiness(
            pre_task_readiness=request.pre_task_readiness,
        )
        return ReadinessCorrectionResponse(**result)
    except NoActiveStopwatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Readiness correction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retroactive", response_model=RetroactiveResponse)
async def retroactive_log(
    request: RetroactiveRequest,
    db: Session = Depends(get_db),
) -> RetroactiveResponse:
    """
    Log a completed session after the fact with full timestamp control.
    Creates task directly in EXECUTED state with initiation_status='retroactive'.
    Delta is 0 by definition (planned = executed for retroactive sessions).
    """
    try:
        manager = TaskManager(db)
        task, notion_synced = manager.create_retroactive_task(
            title=request.title,
            start_time=request.start_time,
            end_time=request.end_time,
            category=request.category,
            pre_task_readiness=request.pre_task_readiness,
            post_task_reflection=request.post_task_reflection,
        )
        return RetroactiveResponse(
            task_id=task.task_id,
            title=task.title,
            start_time=to_local(task.executed_start_utc),
            end_time=to_local(task.executed_end_utc),
            duration_minutes=task.executed_duration_minutes,
            delta_minutes=0,
            initiation_status="retroactive",
            pre_task_readiness=task.pre_task_readiness,
            post_task_reflection=task.post_task_reflection,
            discrepancy_score=task.discrepancy_score,
            notion_synced=notion_synced,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Retroactive log error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
