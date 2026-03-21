"""Task management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.api.deps import get_db
from app.schemas.task import (
    TaskCreateRequest,
    TaskCreateResponse,
    TaskRescheduleRequest,
    TaskRescheduleResponse,
    TaskDeleteRequest,
    TaskDeleteResponse,
    ConflictInfo,
)
from app.services.task_manager import TaskManager
from app.core.exceptions import ImmutableTaskError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/create", response_model=TaskCreateResponse)
async def create_task(
    request: TaskCreateRequest,
    db: Session = Depends(get_db)
) -> TaskCreateResponse:
    """
    Create a new task.
    
    If conflicts detected and force=False, returns conflicts without creating.
    If force=True or no conflicts, creates task and syncs to Notion.
    """
    try:
        manager = TaskManager(db)
        
        task, conflicts = manager.create_task(
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
                    start=c.planned_start_utc,
                    end=c.planned_end_utc,
                    state=c.state
                )
                for c in conflicts
            ]
            
            return TaskCreateResponse(
                task_id=None,
                created=False,
                conflicts=conflict_info,
                can_proceed=True
            )
        
        return TaskCreateResponse(
            task_id=task.task_id,
            created=True,
            conflicts=[],
            can_proceed=True
        )
        
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
                start=c.planned_start_utc,
                end=c.planned_end_utc,
                state=c.state
            )
            for c in conflicts
        ]
        
        return TaskRescheduleResponse(
            task_id=task.task_id,
            rescheduled=True,
            new_start=task.planned_start_utc,
            new_end=task.planned_end_utc,
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
