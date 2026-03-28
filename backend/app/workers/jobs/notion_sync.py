"""Background job to retry failed Notion syncs."""
import logging
from app.db.session import SessionLocal
from app.db.models import Task
from app.utils.redis_client import RedisClient
from app.services.notion_client import NotionClient

logger = logging.getLogger(__name__)

def retry_failed_syncs():
    """Consume from Redis queue and retry Notion sync."""
    redis = RedisClient()
    items = redis.get_notion_sync_queue(limit=10)
    
    if not items:
        return
        
    db = SessionLocal()
    notion = NotionClient()
    
    success_count = 0
    try:
        for item in items:
            task_id = item["task_id"]
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                success_count += 1 # remove from queue if task no longer exists
                continue
                
            try:
                # Update task's mutable state natively through NotionClient
                notion.sync_task(task)
                success_count += 1
                logger.info(f"Successfully retried Notion sync for {task_id}")
            except Exception as e:
                logger.error(f"Retrying Notion sync failed again for {task_id}: {e}")
                break  # stop processing if rate limited/offline
    finally:
        if success_count > 0:
            # We must be careful that we actually update state if notion_sync changed notion_page_id,
            # but notion_sync writes directly to DB internally if needed, or here we should commit.
            # Actually NotionClient's sync_task modifies task.notion_page_id but doesn't intrinsically db.commit() in retry unless stated.
            db.commit()
            
        db.close()
        
        if success_count > 0:
            redis.remove_from_notion_queue(success_count)
