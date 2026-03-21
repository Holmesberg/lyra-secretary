"""Notion API client for calendar sync."""
import logging
from typing import Optional, Dict, Any

from notion_client import Client
from notion_client.errors import APIResponseError

from app.core.config import settings
from app.db.models import Task, TaskState
from app.utils.time_utils import to_local
from app.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class NotionClient:
    """Client for syncing tasks to Notion calendar database."""
    
    def __init__(self):
        self.client = Client(auth=settings.NOTION_API_KEY)
        self.database_id = settings.NOTION_DATABASE_ID
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def sync_task(self, task: Task) -> Optional[str]:
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
            
            if task.notion_page_id:
                # Update existing page
                response = self.client.pages.update(
                    page_id=task.notion_page_id,
                    properties=properties
                )
                logger.info(f"Updated Notion page for task {task.task_id}")
            else:
                # Create new page
                response = self.client.pages.create(
                    parent={"database_id": self.database_id},
                    properties=properties
                )
                task.notion_page_id = response["id"]
                logger.info(f"Created Notion page for task {task.task_id}")
            
            return response["id"]
            
        except APIResponseError as e:
            logger.error(f"Notion API error: {e}", exc_info=True)
            raise
    
    def _build_properties(self, task: Task) -> Dict[str, Any]:
        """Build Notion page properties from task."""
        # Use executed time if available, else planned
        start = task.executed_start_utc or task.planned_start_utc
        end = task.executed_end_utc or task.planned_end_utc
        
        # Convert UTC to local time for display
        start_local = to_local(start)
        end_local = to_local(end)
        
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
                    "start": start_local.isoformat(),
                    "end": end_local.isoformat()
                }
            },
            "State": {
                "status": {
                    "name": task.state.value
                }
            },
        }
        
        # Optional fields
        if task.category:
            properties["Category"] = {
                "multi_select": [{"name": task.category}]
            }
        
        if task.notes:
            properties["Notes"] = {
                "rich_text": [
                    {
                        "text": {"content": task.notes[:2000]}
                    }
                ]
            }
        
        # Duration info (THE CORE VALUE)
        if task.executed_duration_minutes:
            duration_text = f"Planned: {task.planned_duration_minutes}min, "
            duration_text += f"Actual: {task.executed_duration_minutes}min"
            if task.duration_delta_minutes:
                duration_text += f" (Δ {task.duration_delta_minutes:+d}min)"
            
            properties["Duration"] = {
                "rich_text": [
                    {"text": {"content": duration_text}}
                ]
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
