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
    ConflictInfo,
)
from app.services.task_manager import TaskManager
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

