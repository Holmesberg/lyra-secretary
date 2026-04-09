"""Background job to retry failed Notion syncs (per-user, gated)."""
import logging

from app.db.models import Task, User
from app.utils.redis_client import RedisClient
from app.services.notion_client import NotionClient
from app.workers.jobs._per_user import for_each_user

logger = logging.getLogger(__name__)


def retry_failed_syncs():
    for_each_user(_run_for_one_user)


def _run_for_one_user(db, user: User):
    """Notion sync is gated on user.notion_enabled (operator-only in Phase 2)."""
    if not user.notion_enabled:
        return

    redis = RedisClient()
    items = redis.get_notion_sync_queue(limit=10)
    if not items:
        return

    notion = NotionClient()
    success_count = 0
    try:
        for item in items:
            task_id = item["task_id"]
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                # Belongs to a different user, or deleted — drop from queue.
                success_count += 1
                continue
            try:
                notion.sync_task(task)
                success_count += 1
                logger.info(f"Retried Notion sync for {task_id} (user {user.user_id})")
            except Exception as e:
                logger.error(f"Notion sync retry failed for {task_id}: {e}")
                break
    finally:
        if success_count > 0:
            db.commit()
            redis.remove_from_notion_queue(success_count)
