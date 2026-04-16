"""Task management endpoints."""
import json
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.api.deps import get_db
from app.schemas.task import (
    TaskCreateRequest,
    TaskCreateResponse,
    TaskRescheduleRequest,
    TaskRescheduleResponse,
    TaskDeleteRequest,
    TaskDeleteResponse,
    TaskDetail,
    TaskVoidRequest,
    TaskVoidResponse,
    MarkAbandonedRequest,
    MarkAbandonedResponse,
    SwapRequest,
    SwapResponse,
    ConflictInfo,
)
from app.db.models import TaskState
from app.utils.time_utils import now_utc as _now_utc
from app.services.task_manager import TaskManager
from app.services.stopwatch_manager import StopwatchManager, NoActiveStopwatchError
from app.services.notion_client import NotionClient
from app.utils.redis_client import RedisClient
from app.core.exceptions import ImmutableTaskError
from app.db.models import Task
from app.utils.time_utils import to_local

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/create", response_model=TaskCreateResponse)
async def create_task(
    request: TaskCreateRequest,
    db: Session = Depends(get_db),
    x_idempotency_key: Optional[str] = Header(None)
) -> TaskCreateResponse:
    """
    Create a new task.
    
    If conflicts detected and force=False, returns conflicts without creating.
    If force=True or no conflicts, creates task and syncs to Notion.
    
    Optional: Pass X-Idempotency-Key header to prevent duplicate creates
    within a 30-second window.
    """
    try:
        # FIX 4: Idempotency check
        redis = RedisClient()
        if x_idempotency_key:
            cached = redis.check_idempotency(x_idempotency_key)
            if cached:
                logger.info(f"Idempotency hit for key {x_idempotency_key}")
                return TaskCreateResponse(**json.loads(cached))

        manager = TaskManager(db)
        
        task, result, notion_synced = manager.create_task(
            title=request.title,
            start=request.start,
            end=request.end,
            category=request.category,
            state=request.state,
            source=request.source,
            confidence_score=request.confidence_score,
            force_conflicts=request.force
        )

        if task is None:
            # Conflicts exist (HARD always rejects; SOFT rejects when
            # force=False). Serialize per-conflict gate_id so the frontend
            # can render hard vs soft + the analytics layer can attribute
            # override rates per gate.
            conflict_info: list[ConflictInfo] = []
            for c in result.hard:
                conflict_info.append(ConflictInfo(
                    task_id=c.task_id, title=c.title,
                    start=to_local(c.planned_start_utc),
                    end=to_local(c.planned_end_utc),
                    state=c.state, gate_id="active_overlap",
                ))
            for c in result.soft_overlap:
                conflict_info.append(ConflictInfo(
                    task_id=c.task_id, title=c.title,
                    start=to_local(c.planned_start_utc),
                    end=to_local(c.planned_end_utc),
                    state=c.state, gate_id="planned_overlap",
                ))
            for c in result.soft_duplicate:
                conflict_info.append(ConflictInfo(
                    task_id=c.task_id, title=c.title,
                    start=to_local(c.planned_start_utc),
                    end=to_local(c.planned_end_utc),
                    state=c.state, gate_id="duplicate_title",
                ))

            severity = result.severity()
            return TaskCreateResponse(
                task_id=None,
                created=False,
                notion_synced=False,
                conflicts=conflict_info,
                # HARD never overridable; SOFT is.
                can_proceed=(severity == "soft"),
                severity=severity,
                soft_reasons=result.soft_reasons(),
            )

        assert task is not None  # guaranteed by the None check above
        response = TaskCreateResponse(
            task_id=task.task_id,
            created=True,
            notion_synced=notion_synced,
            conflicts=[],
            can_proceed=True,
            severity=None,
            soft_reasons=[],
        )

        # FIX 4: Cache response for idempotency
        if x_idempotency_key:
            redis.set_idempotency(x_idempotency_key, response.model_dump_json())
        
        return response
        
    except ValueError as e:
        error_msg = str(e)
        if "start_in_past" in error_msg:
            raise HTTPException(
                status_code=400,
                detail={"error": "start_in_past", "message": "Task start time is in the past. Did you mean tomorrow?"}
            )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Task creation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reschedule", response_model=TaskRescheduleResponse)
async def reschedule_task(
    request: TaskRescheduleRequest,
    db: Session = Depends(get_db)
) -> TaskRescheduleResponse:
    """Reschedule task (preserves TaskID)."""
    try:
        manager = TaskManager(db)
        
        task, conflicts = manager.reschedule_task(
            task_id=request.task_id,
            new_start=request.new_start,
            new_end=request.new_end,
            title=request.title,
            category=request.category,
        )
        
        conflict_info = [
            ConflictInfo(
                task_id=c.task_id,
                title=c.title,
                start=to_local(c.planned_start_utc),
                end=to_local(c.planned_end_utc),
                state=c.state
            )
            for c in conflicts
        ]

        return TaskRescheduleResponse(
            task_id=task.task_id,
            rescheduled=True,
            new_start=to_local(task.planned_start_utc),
            new_end=to_local(task.planned_end_utc),
            conflicts=conflict_info
        )
        
    except (ImmutableTaskError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Reschedule error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete", response_model=TaskDeleteResponse)
async def delete_task(
    request: TaskDeleteRequest,
    db: Session = Depends(get_db)
) -> TaskDeleteResponse:
    """Delete task (soft delete)."""
    try:
        manager = TaskManager(db)
        task = manager.delete_task(request.task_id)
        
        return TaskDeleteResponse(
            task_id=task.task_id,
            deleted=True
        )
        
    except ImmutableTaskError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Delete error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/void", response_model=TaskVoidResponse)
async def void_task(
    task_id: str,
    request: TaskVoidRequest,
    db: Session = Depends(get_db),
) -> TaskVoidResponse:
    """
    Void a task (any non-DELETED state) — Phase 3.2 redesign.

    The row is preserved (immutable history) but `voided_at` is stamped
    and analytics queries exclude it. `voided_reason` must be one of the
    VOID_REASONS enum; `void_reason_detail` is required when
    voided_reason='other'. EXECUTED tasks still get
    initiation_status='system_error' for backward compatibility with
    existing analytics filters.
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.state == TaskState.DELETED:
        raise HTTPException(
            status_code=400,
            detail="Cannot void a DELETED task",
        )
    previous_state = task.state.value if hasattr(task.state, "value") else str(task.state)
    previous_status = task.initiation_status
    task.voided_at = _now_utc()
    task.voided_reason = request.voided_reason
    task.void_reason_detail = request.void_reason_detail
    # Preserve legacy EXECUTED→system_error mapping so old analytics
    # filters that test initiation_status still exclude the row.
    if task.state == TaskState.EXECUTED:
        task.initiation_status = "system_error"
    db.commit()
    db.refresh(task)

    # Close any unclosed stopwatch session bound to this task and clear
    # the user's Redis active/pause keys. Without this, the frontend
    # /stopwatch/status banner keeps showing a PAUSED timer for the
    # voided task indefinitely (CO-block 65h incident, Apr 11). If the
    # cleanup itself errors we still return success — _get_active has a
    # defensive self-heal that will catch it on the next poll.
    try:
        StopwatchManager(db).void_cleanup(task.task_id)
    except Exception as e:
        logger.warning(
            f"void_cleanup failed for {task.task_id}: {e}. The _get_active "
            f"self-heal will recover on the next status poll."
        )

    return TaskVoidResponse(
        task_id=task.task_id,
        voided=True,
        previous_state=previous_state,
        previous_initiation_status=previous_status,
        voided_at=to_local(task.voided_at),
        voided_reason=task.voided_reason,
        void_reason_detail=task.void_reason_detail,
    )


@router.post("/tasks/{task_id}/mark-abandoned", response_model=MarkAbandonedResponse)
async def mark_abandoned(
    task_id: str,
    request: MarkAbandonedRequest = None,
    db: Session = Depends(get_db),
) -> MarkAbandonedResponse:
    """
    Skip an EXECUTING, PAUSED, or PLANNED task (→ SKIPPED).

    EXECUTING/PAUSED: initiation_status='abandoned' (started but not finished).
    PLANNED: initiation_status='user_skipped' (explicitly declined before starting).
    Both preserve the task as a cascade data point.
    """
    if request is None:
        request = MarkAbandonedRequest()

    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.voided_at is not None:
        raise HTTPException(status_code=400, detail="Cannot skip a voided task")
    if task.state not in (TaskState.EXECUTING, TaskState.PAUSED, TaskState.PLANNED):
        raise HTTPException(
            status_code=400,
            detail=f"Only EXECUTING, PAUSED, or PLANNED tasks can be skipped (current state: {task.state})",
        )

    previous = task.state
    was_active = task.state in (TaskState.EXECUTING, TaskState.PAUSED)
    is_planned = task.state == TaskState.PLANNED
    default_reason = "user_skipped" if is_planned else "abandoned mid-session"
    try:
        manager = TaskManager(db)
        task = manager.skip_task(task_id, reason=request.reason or default_reason)
        task.initiation_status = "user_skipped" if is_planned else "abandoned"
        db.commit()
        db.refresh(task)
    except ImmutableTaskError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Close any unclosed stopwatch session and clear Redis active/pause
    # keys for EXECUTING/PAUSED tasks. Without this the frontend banner
    # keeps showing a PAUSED timer for the now-SKIPPED task (ghost banner
    # bug, Apr 12). Same pattern as void_task — _get_active self-heal is
    # the backup if this fails.
    if was_active:
        try:
            StopwatchManager(db).void_cleanup(task.task_id)
        except Exception as e:
            logger.warning(
                f"stopwatch cleanup failed for mark-abandoned {task.task_id}: {e}. "
                f"_get_active self-heal will recover on next status poll."
            )

    return MarkAbandonedResponse(
        task_id=task.task_id,
        abandoned=True,
        previous_state=previous,
        new_state=task.state,
    )


@router.post("/tasks/swap", response_model=SwapResponse)
async def swap_tasks(
    request: SwapRequest,
    db: Session = Depends(get_db),
) -> SwapResponse:
    """
    Atomically swap a SKIPPED task and a PLANNED task.

    The SKIPPED task is reactivated as PLANNED at the PLANNED task's time slot.
    The PLANNED task is marked SKIPPED (initiation_status='user_skipped').
    Either task_id can be the SKIPPED or PLANNED one — order doesn't matter.
    """
    try:
        manager = TaskManager(db)
        reactivated, skipped = manager.swap_tasks(request.task_a_id, request.task_b_id)
        return SwapResponse(
            swapped=True,
            reactivated_task_id=reactivated.task_id,
            skipped_task_id=skipped.task_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Swap error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule/clear")
async def clear_schedule(
    db: Session = Depends(get_db),
) -> dict:
    """
    Delete all PLANNED tasks from the schedule.

    Blocked with 400 if a stopwatch session is active — the user must stop
    the timer first so the session is properly closed with reflection.
    EXECUTING / PAUSED / EXECUTED / SKIPPED tasks are never touched.
    """
    sw = StopwatchManager(db)
    status = sw.get_status()
    if status.get("active"):
        task_title = status.get("task_title", "current task")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "active_timer",
                "message": f"Stop timer for {task_title} before clearing schedule.",
            },
        )

    manager = TaskManager(db)
    planned = db.query(Task).filter(Task.state == TaskState.PLANNED).all()
    deleted_ids = []
    for t in planned:
        try:
            manager.delete_task(t.task_id)
            deleted_ids.append(t.task_id)
        except Exception as e:
            logger.warning(f"clear_schedule: could not delete {t.task_id}: {e}")

    return {
        "cleared": True,
        "planned_deleted": len(deleted_ids),
    }


@router.post("/tasks/{task_id}/sync")
async def sync_task_to_notion(
    task_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    Force a Notion sync for a specific task.

    Use to backfill tasks created before the timezone pipeline fix (LYR-015),
    or to recover tasks that failed to sync due to transient Notion API errors.
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        notion = NotionClient()
        page_id = notion.sync_task(task, db=db)
        return {
            "task_id": task_id,
            "synced": True,
            "notion_page_id": page_id or task.notion_page_id,
        }
    except Exception as e:
        logger.error(f"Manual Notion sync failed for {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Notion sync failed: {e}")


@router.get("/tasks/{task_id}", response_model=TaskDetail)
async def get_task(
    task_id: str,
    db: Session = Depends(get_db)
) -> TaskDetail:
    """Fetch a single task by ID."""
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskDetail(
        task_id=task.task_id,
        title=task.title,
        category=task.category,
        planned_start=to_local(task.planned_start_utc),
        planned_end=to_local(task.planned_end_utc),
        planned_duration_minutes=task.planned_duration_minutes,
        executed_start=to_local(task.executed_start_utc) if task.executed_start_utc else None,
        executed_end=to_local(task.executed_end_utc) if task.executed_end_utc else None,
        executed_duration_minutes=task.executed_duration_minutes,
        state=task.state,
        source=task.source,
        confidence_score=task.confidence_score,
        notes=task.notes,
        created_at=task.created_at,
        last_modified_at=task.last_modified_at,
        duration_delta_minutes=task.duration_delta_minutes,
        is_mutable=task.is_mutable
    )

