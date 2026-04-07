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
        
        task, conflicts, notion_synced = manager.create_task(
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
            # Conflicts exist, not forced
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

            return TaskCreateResponse(
                task_id=None,
                created=False,
                notion_synced=False,
                conflicts=conflict_info,
                can_proceed=True
            )
        
        assert task is not None  # guaranteed by the None check above
        response = TaskCreateResponse(
            task_id=task.task_id,
            created=True,
            notion_synced=notion_synced,
            conflicts=[],
            can_proceed=True
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
            new_end=request.new_end
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
        
    except ImmutableTaskError as e:
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
    request: TaskVoidRequest = None,
    db: Session = Depends(get_db),
) -> TaskVoidResponse:
    """
    Void an EXECUTED task — marks initiation_status='system_error'.
    Task stays EXECUTED (immutable history preserved) but is excluded
    from all analytics queries. Use for sessions corrupted by agent
    or testing errors.
    """
    if request is None:
        request = TaskVoidRequest()

    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.state != TaskState.EXECUTED:
        raise HTTPException(
            status_code=400,
            detail=f"Only EXECUTED tasks can be voided (current state: {task.state})",
        )
    previous = task.initiation_status
    task.initiation_status = "system_error"
    task.voided_at = _now_utc()
    task.voided_reason = request.voided_reason
    db.commit()
    db.refresh(task)
    return TaskVoidResponse(
        task_id=task.task_id,
        voided=True,
        previous_initiation_status=previous,
        voided_at=to_local(task.voided_at),
        voided_reason=task.voided_reason,
    )


@router.post("/tasks/{task_id}/mark-abandoned", response_model=MarkAbandonedResponse)
async def mark_abandoned(
    task_id: str,
    request: MarkAbandonedRequest = None,
    db: Session = Depends(get_db),
) -> MarkAbandonedResponse:
    """
    Mark an EXECUTING or PAUSED task as abandoned (→ SKIPPED).
    Sets initiation_status='abandoned'. Use when user stops mid-task
    without completing, or when a paused task is never resumed.
    """
    if request is None:
        request = MarkAbandonedRequest()

    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.state not in (TaskState.EXECUTING, TaskState.PAUSED):
        raise HTTPException(
            status_code=400,
            detail=f"Only EXECUTING or PAUSED tasks can be abandoned (current state: {task.state})",
        )

    previous = task.state
    try:
        manager = TaskManager(db)
        task = manager.skip_task(task_id, reason=request.reason or "abandoned mid-session")
        task.initiation_status = "abandoned"
        db.commit()
        db.refresh(task)
    except ImmutableTaskError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return MarkAbandonedResponse(
        task_id=task.task_id,
        abandoned=True,
        previous_state=previous,
        new_state=task.state,
    )


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

