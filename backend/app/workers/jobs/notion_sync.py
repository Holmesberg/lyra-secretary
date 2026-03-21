"""Retry failed Notion syncs job."""
import logging
from app.utils.redis_client import RedisClient
from app.services.notion_client import NotionClient
from app.db.session import SessionLocal
from app.db.models import Task

logger = logging.getLogger(__name__)

def retry_failed_syncs():
    """Retry Notion syncs from the Redis queue."""
    redis = RedisClient()
    queue = redis.get_notion_sync_queue(limit=10)
    
    if not queue:
        return
        
    client = NotionClient()
    db = SessionLocal()
    successful_count = 0
    
    try:
        for item in queue:
            task_id = item.get("task_id")
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if task:
                try:
                    client.sync_task(task)
                    successful_count += 1
                except Exception as e:
                    logger.error(f"Failed to sync task {task_id} on retry: {e}")
                    break
        
        if successful_count > 0:
            redis.remove_from_notion_queue(successful_count)
            logger.info(f"Successfully retried {successful_count} Notion syncs")
            
    finally:
        db.close()
