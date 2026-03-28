"""Undo endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
import json

from app.api.deps import get_db
from app.utils.redis_client import RedisClient
from app.services.task_manager import TaskManager
from app.db.models import TaskState, Task

router = APIRouter()
logger = logging.getLogger(__name__)

from pydantic import BaseModel

class UndoResponse(BaseModel):
    success: bool
    action_undone: str
    message: str

@router.post("/undo", response_model=UndoResponse)
async def undo_action(db: Session = Depends(get_db)) -> UndoResponse:
    """
    Undo the last action within the 30-second window.
    Supports reverting task creation and deletion.
    """
    try:
        redis = RedisClient()
        
        # Get all undo keys
        keys = redis.client.keys("undo:*")
        if not keys:
            raise HTTPException(status_code=400, detail="Nothing to undo or undo window expired")
            
        # We take the first one (v1 single user, simple design)
        # To be robust, we sort by timestamp inside the payload if we had multiple
        # But we assume the latest action
        key = keys[0]
        entity_id = key.split(":")[1]
        
        undo_data_str = redis.client.get(key)
        if not undo_data_str:
            raise HTTPException(status_code=400, detail="Undo data expired")
            
        undo_data = json.loads(undo_data_str)
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
        else:
            raise HTTPException(status_code=400, detail=f"Cannot undo action: {action}")
            
        # Clear the undo key
        redis.clear_undo_data(entity_id)
        
        return UndoResponse(
            success=True,
            action_undone=action,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Undo error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
