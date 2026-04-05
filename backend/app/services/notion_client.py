"""Notion API client for calendar sync."""
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from notion_client import Client
from notion_client.errors import APIResponseError

from app.core.config import settings
from app.db.models import Task, TaskState
from app.utils.time_utils import to_local
from app.utils.retry import retry_with_backoff


def _to_utc_iso(dt):
    """Format a naive UTC datetime as ISO 8601 with +00:00 offset for Notion."""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")

logger = logging.getLogger(__name__)


class NotionClient:
    """Client for syncing tasks to Notion calendar database."""
    
    def __init__(self):
        self.client = Client(auth=settings.NOTION_API_KEY)
        self.database_id = settings.NOTION_DATABASE_ID
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def sync_task(self, task: Task, db: Optional[Session] = None) -> Optional[str]:
        """
        Sync task to Notion database.
        
        Creates page if notion_page_id is None, updates if exists.
        
        Returns:
            Notion page ID
        """
        # If no Notion creds are passed, gracefully allow it to fail or skip
        if not self.database_id or not settings.NOTION_API_KEY:
            return None

        try:
            properties = self._build_properties(task)
            logger.info(f"Notion sync payload for task {task.task_id}: {properties}")
            
            if task.notion_page_id:
                # Update existing page
                logger.info(f"Updating existing Notion page {task.notion_page_id}")
                response = self.client.pages.update(
                    page_id=task.notion_page_id,
                    properties=properties
                )
                logger.info(f"Updated Notion page for task {task.task_id}. Response: {response}")
            else:
                # Create new page
                logger.info(f"Creating new Notion page in database {self.database_id}")
                response = self.client.pages.create(
                    parent={"type": "database_id", "database_id": self.database_id},
                    properties=properties
                )
                task.notion_page_id = response["id"]
                logger.info(f"Created Notion page for task {task.task_id}. Page ID: {response['id']}")
                # Persist notion_page_id to DB so future syncs use update
                if db:
                    db.commit()
                    db.refresh(task)
            
            return response["id"]
            
        except APIResponseError as e:
            logger.error(f"Notion API error: {e}", exc_info=True)
            raise
    
    def _build_properties(self, task: Task) -> Dict[str, Any]:
        """Build Notion page properties from task."""
        # Use executed time if available, else planned
        start = task.executed_start_utc or task.planned_start_utc
        end = task.executed_end_utc or task.planned_end_utc
        
        # State icon
        state_icons = {
            TaskState.PLANNED: "☐",
            TaskState.EXECUTING: "▶️",
            TaskState.EXECUTED: "✓",
            TaskState.SKIPPED: "⊘",
            TaskState.DELETED: "🗑️"
        }
        icon = state_icons.get(task.state, "")
        
        properties = {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": f"{icon} {task.title}"
                        }
                    }
                ]
            },
            "Start": {
                "date": {
                    "start": _to_utc_iso(start),
                    "end": _to_utc_iso(end) if end else None
                }
            },
            "State": {
                "status": {
                    "name": task.state.value if hasattr(task.state, 'value') else str(task.state)
                }
            },
        }
        
        # Optional fields
        if task.category:
            properties["Category"] = {
                "multi_select": [{"name": task.category}]
            }
        
        return properties
    
    def archive_page(self, page_id: str):
        """Archive a Notion page (for deleted tasks)."""
        if not self.database_id or not settings.NOTION_API_KEY:
            return None

        try:
            self.client.pages.update(
                page_id=page_id,
                archived=True
            )
            logger.info(f"Archived Notion page {page_id}")
        except APIResponseError as e:
            logger.error(f"Failed to archive page: {e}")
