"""Redis client with LyraOS-specific patterns."""
import json
import redis
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

STOPWATCH_TTL_SECONDS = 46800


class RedisClient:
    IDEMPOTENCY_PENDING = "__pending__"

    """Redis client with application-specific patterns."""
    
    def __init__(self):
        self.client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
    
    # Stopwatch patterns
    def _active_stopwatch_key(self, user_id: str) -> str:
        return f"stopwatch:active:{user_id}"

    def _pause_state_key(self, user_id: str) -> str:
        return f"stopwatch:paused:{user_id}"

    def _active_stopwatch_payload(
        self,
        *,
        session_id: str,
        task_id: str,
        title: str,
        start_time: str,
    ) -> str:
        return json.dumps(
            {
                "session_id": session_id,
                "task_id": task_id,
                "title": title,
                "start_time": start_time,
            }
        )

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
        key = self._active_stopwatch_key(user_id)
        payload = self._active_stopwatch_payload(
            session_id=session_id,
            task_id=task_id,
            title=title,
            start_time=start_time,
        )
        self.client.set(key, payload, ex=STOPWATCH_TTL_SECONDS)
        logger.info(f"Stopwatch started: {task_id}")

    def activate_stopwatch(
        self,
        *,
        user_id: str,
        session_id: str,
        task_id: str,
        title: str,
        start_time: str,
        clear_pause: bool = True,
    ) -> None:
        """Atomically set active stopwatch and optionally clear pause state.

        Stopwatch active and pause keys describe one live state machine. When
        a resume/switch/recovery path changes both, use one Redis transaction
        so frontend status polls cannot observe a transient split-brain state.
        """
        payload = self._active_stopwatch_payload(
            session_id=session_id,
            task_id=task_id,
            title=title,
            start_time=start_time,
        )
        pipe = self.client.pipeline(transaction=True)
        pipe.set(
            self._active_stopwatch_key(user_id),
            payload,
            ex=STOPWATCH_TTL_SECONDS,
        )
        if clear_pause:
            pipe.delete(self._pause_state_key(user_id))
        pipe.execute()
        logger.info(f"Stopwatch activated atomically: {task_id}")

    def activate_paused_stopwatch(
        self,
        *,
        user_id: str,
        session_id: str,
        task_id: str,
        title: str,
        start_time: str,
        paused_at: str,
    ) -> None:
        """Atomically rehydrate active stopwatch plus paused state."""
        payload = self._active_stopwatch_payload(
            session_id=session_id,
            task_id=task_id,
            title=title,
            start_time=start_time,
        )
        pipe = self.client.pipeline(transaction=True)
        pipe.set(
            self._active_stopwatch_key(user_id),
            payload,
            ex=STOPWATCH_TTL_SECONDS,
        )
        pipe.set(
            self._pause_state_key(user_id),
            json.dumps({"session_id": session_id, "paused_at": paused_at}),
            ex=STOPWATCH_TTL_SECONDS,
        )
        pipe.execute()
        logger.info(f"Paused stopwatch activated atomically: {task_id}")
    
    def get_active_stopwatch(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get active stopwatch session."""
        key = self._active_stopwatch_key(user_id)
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def clear_active_stopwatch(self, user_id: str):
        """Clear active stopwatch."""
        key = self._active_stopwatch_key(user_id)
        self.client.delete(key)
        logger.info(f"Stopwatch cleared for user {user_id}")

    def clear_stopwatch_state(self, user_id: str):
        """Atomically clear active and pause stopwatch keys for a user."""
        pipe = self.client.pipeline(transaction=True)
        pipe.delete(self._active_stopwatch_key(user_id))
        pipe.delete(self._pause_state_key(user_id))
        pipe.execute()
        logger.info(f"Stopwatch state cleared for user {user_id}")

    def set_pause_state(self, user_id: str, session_id: str, paused_at: str):
        """Store pause state. 13h TTL matches set_active_stopwatch."""
        key = self._pause_state_key(user_id)
        self.client.set(
            key,
            json.dumps({"session_id": session_id, "paused_at": paused_at}),
            ex=STOPWATCH_TTL_SECONDS,
        )

    def get_pause_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get pause state if stopwatch is currently paused."""
        key = self._pause_state_key(user_id)
        data = self.client.get(key)
        return json.loads(data) if data else None

    def clear_pause_state(self, user_id: str):
        """Clear pause state on resume or stop."""
        self.client.delete(self._pause_state_key(user_id))
    
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

    def purge_user_runtime_state(self, user_id: str | int) -> int:
        """Delete all known ephemeral Redis state for a user.

        Account deletion must clear short-lived runtime state as well as DB
        rows. Keep patterns here, next to the code that creates most of these
        keys, so new per-user Redis surfaces are easier to audit.
        """
        uid = str(user_id)
        exact_keys = [
            self._active_stopwatch_key(uid),
            self._pause_state_key(uid),
            f"notifications:pending:{uid}",
            f"notion:sync_queue:{uid}",
            f"last_operated_task:{uid}",
            f"gcal:access_token:{uid}",
        ]
        patterns = [
            f"undo:{uid}:*",
            f"idempotency:user:{uid}:*",
            f"tasks_range:{uid}:*",
            f"me:{uid}:*",
            f"gcal:events:{uid}:*",
            f"reminder_sent:{uid}:*",
            f"overflow_sent:{uid}:*",
            f"insight_shown:{uid}:*",
        ]

        keys: set[str] = set(exact_keys)
        for pattern in patterns:
            for key in self.client.scan_iter(match=pattern, count=100):
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                keys.add(str(key))

        if not keys:
            return 0
        return int(self.client.delete(*sorted(keys)) or 0)

    # Idempotency (duplicate request protection)
    def _idempotency_key(self, key: str, user_id: Optional[Any] = None) -> str:
        """Build the Redis idempotency key.

        Runtime request idempotency is user-scoped so one account cannot replay
        another account's cached write response by reusing the same client key.
        The legacy bucket is retained only for non-request utility callers that
        have not yet been migrated.
        """
        if user_id is None:
            return f"idempotency:legacy:{key}"
        return f"idempotency:user:{user_id}:{key}"

    def check_idempotency(self, key: str, user_id: Optional[Any] = None) -> Optional[str]:
        """Check if idempotency key exists. Returns cached response JSON if duplicate."""
        redis_key = self._idempotency_key(key, user_id=user_id)
        return self.client.get(redis_key)

    @classmethod
    def is_idempotency_pending(cls, value: Optional[Any]) -> bool:
        """Return true when an idempotency key is reserved but not completed."""
        if value is None:
            return False
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return str(value) == cls.IDEMPOTENCY_PENDING

    def reserve_idempotency(
        self,
        key: str,
        ttl_seconds: int = 30,
        user_id: Optional[Any] = None,
    ) -> bool:
        """Atomically reserve an idempotency key before a write starts."""
        redis_key = self._idempotency_key(key, user_id=user_id)
        return bool(
            self.client.set(
                redis_key,
                self.IDEMPOTENCY_PENDING,
                ex=ttl_seconds,
                nx=True,
            )
        )

    def set_idempotency(
        self,
        key: str,
        response_json: str,
        ttl_seconds: int = 30,
        user_id: Optional[Any] = None,
    ):
        """Store idempotency key with response for TTL seconds."""
        redis_key = self._idempotency_key(key, user_id=user_id)
        self.client.setex(redis_key, ttl_seconds, response_json)

    def clear_idempotency(self, key: str, user_id: Optional[Any] = None) -> int:
        """Remove a reserved idempotency key after an abandoned write."""
        redis_key = self._idempotency_key(key, user_id=user_id)
        return int(self.client.delete(redis_key) or 0)

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
