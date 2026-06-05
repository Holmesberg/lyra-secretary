"""Undo endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
import json
from datetime import datetime

from app.api.deps import get_db
from app.db.scoping import get_current_user_id
from app.utils.redis_client import RedisClient
from app.services.task_manager import TaskManager
from app.db.models import PauseEvent, StopwatchSession, TaskState, Task
from app.utils.me_cache import invalidate_me
from app.utils.tasks_range_cache import invalidate_user_ranges

router = APIRouter()
logger = logging.getLogger(__name__)

from pydantic import BaseModel

class UndoResponse(BaseModel):
    success: bool
    action_undone: str
    message: str

@router.post("/undo", response_model=UndoResponse)
def undo_action(db: Session = Depends(get_db)) -> UndoResponse:
    """
    Undo the last action within the 30-second window.
    Supports reverting task creation, deletion, and accidental timer start.
    """
    try:
        redis = RedisClient()
        uid = get_current_user_id()
        if uid is None:
            raise HTTPException(status_code=401, detail="not authenticated")
        user_id = str(uid)

        # Get undo keys scoped to this user
        keys = redis.client.keys(f"undo:{user_id}:*")
        if not keys:
            raise HTTPException(status_code=400, detail="Nothing to undo or undo window expired")

        # Multiple undoable actions can briefly overlap (for example, create a
        # task and immediately start its timer). Undo must target the latest
        # action, not whichever Redis key happens to be returned first.
        undo_candidates = []
        for candidate_key in keys:
            raw = redis.client.get(candidate_key)
            if not raw:
                continue
            try:
                payload = json.loads(raw)
                undo_candidates.append((candidate_key, payload))
            except Exception:
                logger.warning("Malformed undo payload ignored for key %s", candidate_key)
        if not undo_candidates:
            raise HTTPException(status_code=400, detail="Undo data expired")
        key, undo_data = max(
            undo_candidates,
            key=lambda item: item[1].get("timestamp", ""),
        )
        # Key format: undo:{user_id}:{entity_id}
        entity_id = key.split(":")[2] if isinstance(key, str) else key.decode().split(":")[2]

        action = undo_data["action"]
        data = undo_data["data"]
        
        manager = TaskManager(db)
        message = ""
        
        if action == "create_task":
            # Undo creation = soft delete
            # We must be careful that task is still mutable
            try:
                task = manager.delete_task(data["task_id"])
                message = f"Undid creation of task '{data['title']}'"
            except Exception as e:
                # If it fails (e.g., transition invalid), we propagate error
                raise HTTPException(status_code=400, detail=f"Failed to undo creation: {e}")
            
        elif action == "delete_task":
            # Undo deletion = restore state
            task = db.query(Task).filter(Task.task_id == data["task_id"]).first()
            if not task:
                raise HTTPException(status_code=400, detail="Task not found to restore")
                
            with db.begin():
                # Direct override to bypass state machine's immutable block on DELETED tasks
                prev_state_str = data.get("previous_state", "PLANNED")
                task.state = TaskState(prev_state_str)
            
            # Re-sync to Notion (un-archive and sync)
            try:
                from app.services.notion_client import NotionClient
                notion = NotionClient()
                if task.notion_page_id:
                    # Un-archive prior to syncing properties
                    notion.client.pages.update(page_id=task.notion_page_id, archived=False)
                notion.sync_task(task)
            except Exception as e:
                logger.warning(f"Failed to sync un-archived task to Notion during undo: {e}")
                # Let task_manager fallback or log it 
                
            message = f"Undid deletion of task '{data['title']}'"
        elif action == "start_stopwatch":
            session_id = data["session_id"]
            task_id = data["task_id"]
            active = redis.get_active_stopwatch(user_id)
            if not active or active.get("session_id") != session_id:
                raise HTTPException(
                    status_code=400,
                    detail="Timer changed since it started; stop or resolve the current session instead.",
                )
            pause_state = redis.get_pause_state(user_id)
            if pause_state and pause_state.get("session_id") == session_id:
                raise HTTPException(
                    status_code=400,
                    detail="Timer was paused after it started; resume or stop it instead.",
                )
            session = (
                db.query(StopwatchSession)
                .filter(
                    StopwatchSession.session_id == session_id,
                    StopwatchSession.user_id == uid,
                    StopwatchSession.task_id == task_id,
                )
                .first()
            )
            if session is None:
                raise HTTPException(status_code=400, detail="Timer session not found")
            if session.end_time_utc is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Timer already ended; undo start is no longer available.",
                )
            pause_events = (
                db.query(PauseEvent)
                .filter(PauseEvent.session_id == session_id, PauseEvent.user_id == uid)
                .count()
            )
            if pause_events:
                raise HTTPException(
                    status_code=400,
                    detail="Timer has pause history; stop or resolve it instead.",
                )
            task = (
                db.query(Task)
                .filter(Task.task_id == task_id, Task.user_id == uid)
                .first()
            )
            if task is None:
                raise HTTPException(status_code=400, detail="Task not found")

            if data.get("created_task"):
                db.delete(task)
            else:
                db.delete(session)
                snapshot = data.get("task_snapshot") or {}
                previous_state = snapshot.get("state", TaskState.PLANNED.value)
                task.state = TaskState(previous_state)
                task.pre_task_readiness = snapshot.get("pre_task_readiness")
                task.initiation_status = snapshot.get("initiation_status")
                task.initiation_delay_minutes = snapshot.get("initiation_delay_minutes")
                task.parent_task_id = snapshot.get("parent_task_id")
                task.interruption_type = snapshot.get("interruption_type")
                task.last_modified_at = datetime.utcnow()
            db.commit()

            previous_active = data.get("active_before_start")
            previous_pause = (
                data.get("parent_pause_state_after_switch")
                or data.get("pause_state_before_start")
            )
            if previous_active:
                if previous_pause:
                    redis.activate_paused_stopwatch(
                        user_id=user_id,
                        session_id=previous_active["session_id"],
                        task_id=previous_active["task_id"],
                        title=previous_active["title"],
                        start_time=previous_active["start_time"],
                        paused_at=previous_pause["paused_at"],
                    )
                else:
                    redis.activate_stopwatch(
                        user_id=user_id,
                        session_id=previous_active["session_id"],
                        task_id=previous_active["task_id"],
                        title=previous_active["title"],
                        start_time=previous_active["start_time"],
                    )
            else:
                redis.clear_stopwatch_state(user_id)

            try:
                redis.queue_notion_sync(task_id, {"action": "sync"}, user_id=user_id)
            except Exception as e:
                logger.warning("Failed to queue Notion sync during timer-start undo: %s", e)

            try:
                invalidate_me(uid)
                invalidate_user_ranges(uid)
            except Exception as e:
                logger.warning("Failed to invalidate cache during timer-start undo: %s", e)

            message = f"Undid timer start for '{data['title']}'"
        else:
            raise HTTPException(status_code=400, detail=f"Cannot undo action: {action}")
            
        # Clear the undo key
        redis.clear_undo_data(entity_id, user_id=user_id)
        if action == "start_stopwatch":
            redis.clear_undo_data(data["task_id"], user_id=user_id)
        
        return UndoResponse(
            success=True,
            action_undone=action,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Undo error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
