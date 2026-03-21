"""Redis client with Lyra-specific patterns."""
import json
import redis
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client with application-specific patterns."""
    
    def __init__(self):
        self.client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
    
    # Stopwatch patterns
    def set_active_stopwatch(
        self,
        user_id: str,
        session_id: str,
        task_id: str,
        title: str,
        start_time: str
    ):
        """Store active stopwatch session (no TTL - persists until stopped)."""
        key = f"stopwatch:active:{user_id}"
        data = {
            "session_id": session_id,
            "task_id": task_id,
            "title": title,
            "start_time": start_time
        }
        self.client.set(key, json.dumps(data))
        logger.info(f"Stopwatch started: {task_id}")
    
    def get_active_stopwatch(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get active stopwatch session."""
        key = f"stopwatch:active:{user_id}"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def clear_active_stopwatch(self, user_id: str):
        """Clear active stopwatch."""
        key = f"stopwatch:active:{user_id}"
        self.client.delete(key)
        logger.info(f"Stopwatch cleared for user {user_id}")
    
    # Undo pattern (30 second TTL)
    def cache_undo_action(
        self,
        action_type: str,
        entity_id: str,
        data: Dict[str, Any],
        ttl_seconds: int = 30
    ):
        """Cache action for undo."""
        key = f"undo:{entity_id}"
        undo_data = {
            "action": action_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.client.setex(key, ttl_seconds, json.dumps(undo_data))
    
    def get_undo_data(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get undo data if within TTL."""
        key = f"undo:{entity_id}"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def clear_undo_data(self, entity_id: str):
        """Clear undo data."""
        key = f"undo:{entity_id}"
        self.client.delete(key)
    
    # Idempotency pattern (Telegram webhooks)
    def check_telegram_update(self, update_id: int) -> bool:
        """
        Check if Telegram update already processed.
        
        Returns:
            True if duplicate (already processed)
            False if new
        """
        key = f"telegram:update:{update_id}"
        
        if self.client.exists(key):
            return True  # Duplicate
        
        # Mark as processed (60 second TTL)
        self.client.setex(key, 60, "1")
        return False  # New
    
    # Notion sync queue
    def queue_notion_sync(self, task_id: str, task_data: Dict[str, Any]):
        """Queue task for Notion sync (if API down)."""
        key = "notion:sync_queue"
        self.client.rpush(key, json.dumps({"task_id": task_id, "data": task_data}))
    
    def get_notion_sync_queue(self, limit: int = 10) -> list:
        """Get pending Notion sync items."""
        key = "notion:sync_queue"
        items = self.client.lrange(key, 0, limit - 1)
        return [json.loads(item) for item in items]
    
    def remove_from_notion_queue(self, count: int):
        """Remove synced items from queue."""
        key = "notion:sync_queue"
        self.client.ltrim(key, count, -1)
