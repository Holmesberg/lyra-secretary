"""Stopwatch endpoints."""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
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
    StopwatchSwitchResponse,
    ReadinessCorrectionRequest,
    ReadinessCorrectionResponse,
    UpdateCompletionRequest,
    UpdateCompletionResponse,
    StalePauseResolveRequest,
    StalePauseResolveResponse,
    RetroactiveRequest,
    RetroactiveResponse,
    PAUSE_REASONS,
    PAUSE_INITIATORS,
)
from app.db.models import TaskState
from app.db.scoping import get_current_user_id
from app.services.output_surfaces import (
    RULE11_SUPPRESSION_REASON,
    emit_surface_render,
    emit_surface_suppression,
    rule11_no_nudge_control_active,
    rule11_randomization_fields,
)
from app.services.stopwatch_manager import (
    StopwatchManager,
    StopwatchAlreadyRunningError,
    StopwatchAlreadyPausedError,
    StopwatchNotPausedError,
    NoActiveStopwatchError,
)
from app.services.task_manager import TaskManager
from app.core.exceptions import InvalidStateTransitionError
from app.utils.time_utils import now_utc, to_local

router = APIRouter()
logger = logging.getLogger(__name__)


def _current_user_id_or_401() -> int:
    user_id = get_current_user_id()
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id


def _cached_response(*, redis, key: str, user_id: int, response_model):
    cached = redis.check_idempotency(key, user_id=user_id)
    if not cached:
        return None
    return response_model(**json.loads(cached))


def _cache_response(*, redis, key: str, user_id: int, response) -> None:
    redis.set_idempotency(
        key,
        response.model_dump_json(),
        ttl_seconds=30,
        user_id=user_id,
    )


@router.post("/start", response_model=StopwatchStartResponse)
def start_stopwatch(
    request: StopwatchStartRequest,
    db: Session = Depends(get_db),
    x_idempotency_key: Optional[str] = Header(None),
) -> StopwatchStartResponse:
    """Start stopwatch. Optionally pass pre_task_readiness (1–5) in body."""
    current_user_id = _current_user_id_or_401()
    try:
        manager = StopwatchManager(db)
        cache_key = None
        if x_idempotency_key:
            cache_key = f"stopwatch:start:{request.task_id or request.title}:{x_idempotency_key}"
            cached = _cached_response(
                redis=manager.redis,
                key=cache_key,
                user_id=current_user_id,
                response_model=StopwatchStartResponse,
            )
            if cached:
                return cached

        session, task, is_future_task = manager.start(
            task_id=request.task_id,
            title=request.title,
            pre_task_readiness=request.pre_task_readiness,
            interruption_type=request.interruption_type,
        )
        response = StopwatchStartResponse(
            session_id=session.session_id,
            task_id=task.task_id,
            start_time=to_local(session.start_time_utc),
            is_future_task=is_future_task,
            planned_start=to_local(task.planned_start_utc),
            pre_task_readiness=task.pre_task_readiness,
            initiation_delay_minutes=task.initiation_delay_minutes,
            parent_task_id=task.parent_task_id,
            interruption_type=task.interruption_type,
        )
        if cache_key:
            _cache_response(
                redis=manager.redis,
                key=cache_key,
                user_id=current_user_id,
                response=response,
            )
        return response
    except StopwatchAlreadyRunningError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_state_transition",
                "message": (
                    "This task is no longer startable. It may have been "
                    "auto-skipped, completed, or cancelled. Create a new "
                    "task with the same title to continue."
                ),
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stopwatch start error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/pause", response_model=StopwatchPauseResponse)
def pause_stopwatch(
    request: StopwatchPauseRequest,
    db: Session = Depends(get_db),
    x_idempotency_key: Optional[str] = Header(None),
) -> StopwatchPauseResponse:
    """
    Pause the active stopwatch. Use during prayer, breaks, or interruptions.
    Paused time is excluded from executed_duration and delta on stop.

    Required body: pause_reason (mental_fatigue|distraction|task_difficulty|
    external_interruption|intentional_break|prayer), pause_initiator (self|external).
    Both are required — silent defaults were removed in migration 020's commit
    to prevent pre-registered research fields from being filled without user input.
    """
    # Enum validation — request fields are required by schema, so both are present here.
    if request.pause_reason not in PAUSE_REASONS:
        raise HTTPException(status_code=400, detail=f"Invalid pause_reason. Must be one of: {', '.join(sorted(PAUSE_REASONS))}")
    if request.pause_initiator not in PAUSE_INITIATORS:
        raise HTTPException(status_code=400, detail=f"Invalid pause_initiator. Must be one of: {', '.join(sorted(PAUSE_INITIATORS))}")

    current_user_id = _current_user_id_or_401()
    try:
        manager = StopwatchManager(db)
        cache_key = None
        if x_idempotency_key:
            cache_key = f"stopwatch:pause:{x_idempotency_key}"
            cached = _cached_response(
                redis=manager.redis,
                key=cache_key,
                user_id=current_user_id,
                response_model=StopwatchPauseResponse,
            )
            if cached:
                return cached

        result = manager.pause(
            pause_reason=request.pause_reason,
            pause_initiator=request.pause_initiator,
        )
        result["paused_at"] = to_local(result["paused_at"])
        response = StopwatchPauseResponse(**result)
        if cache_key:
            _cache_response(
                redis=manager.redis,
                key=cache_key,
                user_id=current_user_id,
                response=response,
            )
        return response
    except NoActiveStopwatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StopwatchAlreadyPausedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stopwatch pause error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/resume", response_model=StopwatchResumeResponse)
def resume_stopwatch(
    db: Session = Depends(get_db),
    x_idempotency_key: Optional[str] = Header(None),
) -> StopwatchResumeResponse:
    """
    Resume a paused stopwatch. Reports how many minutes were paused.
    """
    current_user_id = _current_user_id_or_401()
    try:
        manager = StopwatchManager(db)
        cache_key = None
        if x_idempotency_key:
            cache_key = f"stopwatch:resume:{x_idempotency_key}"
            cached = _cached_response(
                redis=manager.redis,
                key=cache_key,
                user_id=current_user_id,
                response_model=StopwatchResumeResponse,
            )
            if cached:
                return cached

        result = manager.resume()
        response = StopwatchResumeResponse(**result)
        if cache_key:
            _cache_response(
                redis=manager.redis,
                key=cache_key,
                user_id=current_user_id,
                response=response,
            )
        return response
    except NoActiveStopwatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StopwatchNotPausedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stopwatch resume error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/stop", response_model=StopwatchStopResponse)
def stop_stopwatch(
    request: StopwatchStopRequest = None,
    confirmed: bool = Query(False, description="Set to true to confirm early stop"),
    db: Session = Depends(get_db),
    x_idempotency_key: Optional[str] = Header(None),
) -> StopwatchStopResponse:
    """
    Stop active stopwatch. Requires ?confirmed=true if stopping before 50% of planned duration.
    If paused when stop is called, auto-resumes first and counts final pause in deduction.
    """
    if request is None:
        request = StopwatchStopRequest()

    current_user_id = _current_user_id_or_401()
    try:
        manager = StopwatchManager(db)
        cache_key = None
        if x_idempotency_key:
            cache_key = f"stopwatch:stop:{confirmed}:{x_idempotency_key}"
            cached = _cached_response(
                redis=manager.redis,
                key=cache_key,
                user_id=current_user_id,
                response_model=StopwatchStopResponse,
            )
            if cached:
                return cached

        is_early, elapsed, planned = manager.check_early_stop()
        if is_early and not confirmed:
            response = StopwatchStopResponse(
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
            if cache_key:
                _cache_response(
                    redis=manager.redis,
                    key=cache_key,
                    user_id=current_user_id,
                    response=response,
                )
            return response

        session, task, is_early_stop, _legacy_external_sync, paused_parent, micro_mirror, calibration_nudge, pre_existing_pct = manager.stop(
            post_task_reflection=request.post_task_reflection,
            task_completion_percentage=request.task_completion_percentage,
            scope_outcome=request.scope_outcome,
        )
        zero_duration_skip = task.state == TaskState.SKIPPED and task.executed_duration_minutes in (None, 0)

        # LYR-098 Commit 2b: write-on-fire to reflection_view_log so the
        # client can stamp viewed/dismissed (notification_patterns.md
        # §Saved-to-history). user_id is set by the scoping hook for the
        # request — guaranteed non-None once manager.stop() has returned
        # (stop() would have raised otherwise).
        user_id = get_current_user_id()
        micro_mirror_view_id = None
        micro_mirror_exposure_id = None
        calibration_nudge_view_id = None
        calibration_nudge_exposure_id = None
        fired_at = now_utc()
        surface_decision_recorded = False
        if micro_mirror:
            surface_id = "stopwatch.micro_mirror"
            arm, policy = rule11_randomization_fields(
                db, user_id=user_id, surface_id=surface_id, eligible_at=fired_at
            )
            if rule11_no_nudge_control_active(
                db, user_id=user_id, surface_id=surface_id, eligible_at=fired_at
            ):
                emit_surface_suppression(
                    db,
                    surface_id=surface_id,
                    user_id=user_id,
                    task_id=task.task_id,
                    suppression_reason=RULE11_SUPPRESSION_REASON,
                    eligible_at=fired_at,
                    suppressed_at=fired_at,
                    content_template_id="micro_mirror",
                    initiative="system",
                    trigger_source="stopwatch.stop",
                    randomization_arm=arm,
                    randomization_policy_version=policy,
                )
                micro_mirror = None
                surface_decision_recorded = True
            else:
                emitted = emit_surface_render(
                    db,
                    surface_id=surface_id,
                    user_id=user_id,
                    task_id=task.task_id,
                    content_snapshot=micro_mirror,
                    content_template_id="micro_mirror",
                    initiative="system",
                    trigger_source="stopwatch.stop",
                    eligible_at=fired_at,
                    rendered_at=fired_at,
                    create_legacy_view=True,
                    legacy_payload=micro_mirror,
                    randomization_arm=arm,
                    randomization_policy_version=policy,
                )
                micro_mirror_view_id = emitted["legacy_view_id"]
                micro_mirror_exposure_id = emitted["exposure_id"]
                surface_decision_recorded = True
        if calibration_nudge:
            surface_id = "stopwatch.calibration_nudge"
            arm, policy = rule11_randomization_fields(
                db, user_id=user_id, surface_id=surface_id, eligible_at=fired_at
            )
            if rule11_no_nudge_control_active(
                db, user_id=user_id, surface_id=surface_id, eligible_at=fired_at
            ):
                emit_surface_suppression(
                    db,
                    surface_id=surface_id,
                    user_id=user_id,
                    task_id=task.task_id,
                    suppression_reason=RULE11_SUPPRESSION_REASON,
                    eligible_at=fired_at,
                    suppressed_at=fired_at,
                    content_template_id="calibration_nudge",
                    initiative="system",
                    trigger_source="stopwatch.stop",
                    randomization_arm=arm,
                    randomization_policy_version=policy,
                )
                calibration_nudge = None
                surface_decision_recorded = True
            else:
                emitted = emit_surface_render(
                    db,
                    surface_id=surface_id,
                    user_id=user_id,
                    task_id=task.task_id,
                    content_snapshot=calibration_nudge,
                    content_template_id="calibration_nudge",
                    initiative="system",
                    trigger_source="stopwatch.stop",
                    eligible_at=fired_at,
                    rendered_at=fired_at,
                    create_legacy_view=True,
                    legacy_payload=calibration_nudge,
                    randomization_arm=arm,
                    randomization_policy_version=policy,
                )
                calibration_nudge_view_id = emitted["legacy_view_id"]
                calibration_nudge_exposure_id = emitted["exposure_id"]
                surface_decision_recorded = True
        if surface_decision_recorded:
            db.commit()

        response = StopwatchStopResponse(
            task_id=task.task_id,
            session_id=session.session_id,
            duration_minutes=task.executed_duration_minutes or 0,
            planned_duration_minutes=task.planned_duration_minutes,
            delta_minutes=task.duration_delta_minutes,
            executed_at=to_local(task.executed_end_utc or datetime.utcnow()),
            is_early_stop=is_early_stop,
            post_task_reflection=task.post_task_reflection,
            discrepancy_score=task.discrepancy_score,
            paused_parent=paused_parent,
            micro_mirror=micro_mirror,
            micro_mirror_view_id=micro_mirror_view_id,
            micro_mirror_exposure_id=micro_mirror_exposure_id,
            skipped=zero_duration_skip,
            skip_reason="zero_duration" if zero_duration_skip else None,
            calibration_nudge=calibration_nudge,
            calibration_nudge_view_id=calibration_nudge_view_id,
            calibration_nudge_exposure_id=calibration_nudge_exposure_id,
            task_completion_percentage=session.task_completion_percentage,
            mid_task_completion_pct=pre_existing_pct if pre_existing_pct is not None else None,
        )
        if cache_key:
            _cache_response(
                redis=manager.redis,
                key=cache_key,
                user_id=current_user_id,
                response=response,
            )
        return response

    except NoActiveStopwatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stopwatch stop error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status", response_model=StopwatchStatusResponse)
def stopwatch_status(db: Session = Depends(get_db)) -> StopwatchStatusResponse:
    """Get stopwatch status. Includes paused state, total paused minutes,
    and paused_others (other paused-with-open-session tasks for this user
    that the multi-tasking swap UX uses as switch candidates)."""
    try:
        manager = StopwatchManager(db)
        status = manager.get_status()
        if status.get("start_time"):
            status["start_time"] = to_local(status["start_time"])
        return StopwatchStatusResponse(**status)
    except Exception as e:
        logger.error(f"Stopwatch status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/switch/{task_id}", response_model=StopwatchSwitchResponse)
def switch_stopwatch(
    task_id: str,
    db: Session = Depends(get_db),
) -> StopwatchSwitchResponse:
    """Atomically swap the active stopwatch to a different paused task.

    Multi-tasking swap (Apr 25): operator runs Task A as an interruption
    while Task B is paused-with-open-session. Calling this endpoint with
    target=B pauses A in a single transaction and resumes B.

    Validation errors (HTTP 400):
      * Target task not found
      * Target task is voided
      * Target task state != PAUSED
      * Target task has no open StopwatchSession (start it instead)

    Idempotent on switch-to-self: target == current active returns noop=True
    (or falls through to a regular resume if the active task happens to be
    paused).
    """
    try:
        manager = StopwatchManager(db)
        result = manager.switch_to_task(target_task_id=task_id)
        if result.get("to_start_time"):
            result["to_start_time"] = to_local(result["to_start_time"])
        return StopwatchSwitchResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NoActiveStopwatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StopwatchNotPausedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stopwatch switch error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/update-completion", response_model=UpdateCompletionResponse)
def update_completion(
    request: UpdateCompletionRequest,
    db: Session = Depends(get_db),
) -> UpdateCompletionResponse:
    """
    Update task_completion_percentage on the active session without stopping.

    Used by the timer overflow check-in flow: when the user replies with a
    percentage (e.g. "80%"), this records the progress mid-task. The value
    persists on the StopwatchSession and is available when the timer is
    eventually stopped. Does NOT stop the timer.
    """
    try:
        manager = StopwatchManager(db)
        result = manager.update_completion(
            task_completion_percentage=request.task_completion_percentage,
        )
        return UpdateCompletionResponse(**result)
    except NoActiveStopwatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Update completion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/correct-readiness", response_model=ReadinessCorrectionResponse)
def correct_readiness(
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
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/stale-pauses/{session_id}/resolve",
    response_model=StalePauseResolveResponse,
)
def resolve_stale_pause(
    session_id: str,
    request: StalePauseResolveRequest,
    db: Session = Depends(get_db),
) -> StalePauseResolveResponse:
    """Resolve a 72h+ paused session with explicit post-task reflection."""
    try:
        result = StopwatchManager(db).resolve_stale_pause(
            session_id,
            post_task_reflection=request.post_task_reflection,
            task_completion_percentage=request.task_completion_percentage,
            scope_outcome=request.scope_outcome,
        )
        return StalePauseResolveResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stale pause resolve error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/retroactive", response_model=RetroactiveResponse)
def retroactive_log(
    request: RetroactiveRequest,
    db: Session = Depends(get_db),
) -> RetroactiveResponse:
    """
    Log a completed session after the fact with full timestamp control.
    Creates task directly in EXECUTED state with initiation_status='retroactive'.
    If planned_duration_minutes provided, computes real delta. Otherwise delta=0.

    Returns HTTP 400 with missing_fields when contextual fields are absent.
    The caller should ask the user for each field's prompt (one at a time),
    collect all answers, then retry with the completed request.
    """
    missing = []
    if request.post_task_reflection is None:
        missing.append({
            "field": "post_task_reflection",
            "prompt": "Focus quality? (1=very poor, 3=average, 5=excellent)",
        })
    if request.total_paused_minutes is None:
        missing.append({
            "field": "total_paused_minutes",
            "prompt": "Any paused time to subtract? (minutes, or 0)",
        })
    if request.unplanned_reason is None:
        missing.append({
            "field": "unplanned_reason",
            "prompt": "Why wasn't this planned? 1. Unexpected task  2. Forgot to log  3. Planning friction  4. Spontaneous decision",
            "options": {"1": "unexpected_task", "2": "forgot_to_log", "3": "planning_friction", "4": "spontaneous_decision"},
        })
    if missing:
        raise HTTPException(
            status_code=400,
            detail={"error": "missing_required_fields", "missing_fields": missing},
        )

    try:
        manager = TaskManager(db)
        task, _legacy_external_sync = manager.create_retroactive_task(
            title=request.title,
            start_time=request.start_time,
            end_time=request.end_time,
            category=request.category,
            pre_task_readiness=request.pre_task_readiness,
            post_task_reflection=request.post_task_reflection,
            planned_duration_minutes=request.planned_duration_minutes,
            unplanned_reason=request.unplanned_reason,
            total_paused_minutes=request.total_paused_minutes,
        )
        delta = task.planned_duration_minutes - task.executed_duration_minutes
        return RetroactiveResponse(
            task_id=task.task_id,
            title=task.title,
            start_time=to_local(task.executed_start_utc),
            end_time=to_local(task.executed_end_utc),
            duration_minutes=task.executed_duration_minutes,
            planned_duration_minutes=task.planned_duration_minutes,
            delta_minutes=delta,
            initiation_status="retroactive",
            pre_task_readiness=task.pre_task_readiness,
            post_task_reflection=task.post_task_reflection,
            discrepancy_score=task.discrepancy_score,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Retroactive log error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
