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
        """Store active stopwatch session. 13h TTL as defense-in-depth above
        the 12h stale_session_recovery DB sweep — if stop/recovery both miss,
        the key auto-expires rather than persisting indefinitely."""
        key = f"stopwatch:active:{user_id}"
        data = {
            "session_id": session_id,
            "task_id": task_id,
            "title": title,
            "start_time": start_time
        }
        self.client.set(key, json.dumps(data), ex=46800)
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

    def set_pause_state(self, user_id: str, session_id: str, paused_at: str):
        """Store pause state. 13h TTL matches set_active_stopwatch."""
        key = f"stopwatch:paused:{user_id}"
        self.client.set(key, json.dumps({"session_id": session_id, "paused_at": paused_at}), ex=46800)

    def get_pause_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get pause state if stopwatch is currently paused."""
        key = f"stopwatch:paused:{user_id}"
        data = self.client.get(key)
        return json.loads(data) if data else None

    def clear_pause_state(self, user_id: str):
        """Clear pause state on resume or stop."""
        self.client.delete(f"stopwatch:paused:{user_id}")
    
    # Undo pattern (30 second TTL, per-user namespaced)
    def cache_undo_action(
        self,
        action_type: str,
        entity_id: str,
        data: Dict[str, Any],
        user_id: str = "1",
        ttl_seconds: int = 30
    ):
        """Cache action for undo (per-user)."""
        key = f"undo:{user_id}:{entity_id}"
        undo_data = {
            "action": action_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.client.setex(key, ttl_seconds, json.dumps(undo_data))

    def get_undo_data(self, entity_id: str, user_id: str = "1") -> Optional[Dict[str, Any]]:
        """Get undo data if within TTL (per-user)."""
        key = f"undo:{user_id}:{entity_id}"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None

    def clear_undo_data(self, entity_id: str, user_id: str = "1"):
        """Clear undo data (per-user)."""
        key = f"undo:{user_id}:{entity_id}"
        self.client.delete(key)
    # Idempotency (duplicate request protection)
    def check_idempotency(self, key: str) -> Optional[str]:
        """Check if idempotency key exists. Returns cached response JSON if duplicate."""
        redis_key = f"idempotency:{key}"
        return self.client.get(redis_key)

    def set_idempotency(self, key: str, response_json: str, ttl_seconds: int = 30):
        """Store idempotency key with response for TTL seconds."""
        redis_key = f"idempotency:{key}"
        self.client.setex(redis_key, ttl_seconds, response_json)

    # Notion sync queue
    def queue_notion_sync(self, task_id: str, task_data: Dict[str, Any], user_id: str = "1"):
        """Queue task for Notion sync (if API down). Per-user namespaced."""
        key = f"notion:sync_queue:{user_id}"
        self.client.rpush(key, json.dumps({"task_id": task_id, "data": task_data}))

    def get_notion_sync_queue(self, user_id: str = "1", limit: int = 10) -> list:
        """Get pending Notion sync items for a user."""
        key = f"notion:sync_queue:{user_id}"
        items = self.client.lrange(key, 0, limit - 1)
        return [json.loads(item) for item in items]

    def remove_from_notion_queue(self, user_id: str = "1", count: int = 0):
        """Remove synced items from a user's queue."""
        key = f"notion:sync_queue:{user_id}"
        self.client.ltrim(key, count, -1)

    # Last-operated task (context for follow-up corrections)
    def set_last_task(self, task_id: str, title: str, state: str, user_id: str = "1", ttl_seconds: int = 3600):
        """Store the most recently operated task for 1 hour (follow-up context).

        Per-user namespaced so user A's "actually, make that next week"
        can't target user B's most recent task.
        """
        self.client.setex(
            f"last_operated_task:{user_id}",
            ttl_seconds,
            json.dumps({"task_id": task_id, "title": title, "state": state}),
        )

    def get_last_task(self, user_id: str = "1") -> Optional[Dict[str, Any]]:
        """Return the most recently operated task, or None if window expired."""
        data = self.client.get(f"last_operated_task:{user_id}")
        return json.loads(data) if data else None
