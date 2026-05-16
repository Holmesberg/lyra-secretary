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
        # Multi-user gate (Phase 2): skip for users without notion_enabled.
        # Use the caller's session when provided so tests with :memory: DBs
        # don't fall through to the real DATABASE_URL-bound engine (which may
        # not exist in CI — sqlite3 OperationalError: unable to open database).
        from app.db.models import User
        _s = db
        _owned = False
        if _s is None:
            from app.db.session import SessionLocal
            _s = SessionLocal()
            _owned = True
        try:
            owner = _s.query(User).filter(User.user_id == getattr(task, "user_id", 1)).first()
            if owner is None or not owner.notion_enabled:
                return None
        finally:
            if _owned:
                _s.close()
        # If no Notion creds are passed, gracefully allow it to fail or skip
        if not self.database_id or not settings.NOTION_API_KEY:
            return None

        try:
            properties = self._build_properties(task)
            logger.info(
                "Notion sync prepared task_id=%s property_count=%s",
                task.task_id,
                len(properties),
            )
            
            if task.notion_page_id:
                # Update existing page
                logger.info(f"Updating existing Notion page {task.notion_page_id}")
                response = self.client.pages.update(
                    page_id=task.notion_page_id,
                    properties=properties
                )
                logger.info("Updated Notion page for task %s", task.task_id)
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
            # LYR-091: An archived Notion page is a permanent state — the page
            # stays archived until someone manually unarchives it in Notion.
            # Re-raising here feeds it back into @retry_with_backoff and the
            # Redis retry queue, producing pure log noise every 5 minutes
            # forever. Return None instead: the retry worker treats a
            # no-exception return as success and drops the item from the
            # queue head via its success_count / ltrim path.
            if "archived" in str(e).lower():
                logger.warning(
                    f"Notion page archived for task {task.task_id} "
                    f"(page_id={task.notion_page_id}); dropping from retry "
                    f"queue permanently. Unarchive the page in Notion to "
                    f"re-enable sync."
                )
                return None
            logger.error(
                "Notion API error for task_id=%s code=%s status=%s",
                task.task_id,
                getattr(e, "code", None),
                getattr(e, "status", None),
            )
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
            TaskState.PAUSED: "⏸",
            TaskState.EXECUTED: "✓",
            TaskState.SKIPPED: "⊘",
            TaskState.DELETED: "🗑️"
        }
        icon = state_icons.get(task.state, "")

        state_val = task.state.value if hasattr(task.state, 'value') else str(task.state)
        notion_status_name = state_val
        
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
                    "name": notion_status_name
                }
            },
            # Always include Category so update syncs never silently lose it.
            # Empty array explicitly clears it in Notion when SQLite has null.
            "Category": {
                "multi_select": [{"name": task.category}] if task.category else []
            },
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
            logger.error(
                "Failed to archive Notion page_id=%s code=%s status=%s",
                page_id,
                getattr(e, "code", None),
                getattr(e, "status", None),
            )
