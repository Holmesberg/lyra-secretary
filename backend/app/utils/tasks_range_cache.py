"""Per-user cache for the /v1/tasks/query range response.

Why this exists (2026-04-29 night, follow-on from the d7993d0 latency
sweep): /pulse v2 fires a 14-day /tasks/query range to power the
Recovery + System Insight charts. Single Cairo→Supabase round trip but
the underlying scan is heavier than a 1-day window. Cumulative weight
on /pulse first-paint pushes the dashboard ~200ms slower than /today.

Strategy mirrors me_cache.py:
  * Cache the full /tasks/query response JSON for 60s, keyed by
    (user_id, date_from, date_to).
  * Bust on task/deadline mutations and stopwatch transitions so Pulse
    never offers actions against stale task state.
  * Redis-down is graceful: get/set silently fall through; the
    endpoint runs the queries directly.

TTL is 60s vs me_cache's 30s because the range data is more expensive
to compute and less time-sensitive. The chart aggregations resample at
day-boundaries client-side, so 60s of staleness on a 14-day series is
imperceptible.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.utils.redis_client import RedisClient

logger = logging.getLogger(__name__)

_CACHE_KEY_PREFIX = "tasks_range:"
_CACHE_KEY_VERSION = "v1"
_DEFAULT_TTL_SECONDS = 60


def _key(user_id: int, date_from: str, date_to: str) -> str:
    return f"{_CACHE_KEY_PREFIX}{user_id}:{date_from}:{date_to}:{_CACHE_KEY_VERSION}"


def get_cached_range(
    user_id: int, date_from: str, date_to: str
) -> Optional[dict[str, Any]]:
    """Return cached range payload, or None on miss/error/decode-fail."""
    try:
        raw = RedisClient().client.get(_key(user_id, date_from, date_to))
    except Exception as e:
        logger.warning("tasks_range_cache: get failed for user %s: %s", user_id, e)
        return None
    if raw is None:
        return None
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)
    except Exception as e:
        logger.warning(
            "tasks_range_cache: parse failed for user %s, dropping: %s",
            user_id, e,
        )
        try:
            RedisClient().client.delete(_key(user_id, date_from, date_to))
        except Exception:
            pass
        return None


def set_cached_range(
    user_id: int,
    date_from: str,
    date_to: str,
    payload: dict[str, Any],
    ttl: int = _DEFAULT_TTL_SECONDS,
) -> None:
    """Store a range payload with TTL. Silent on failure."""
    try:
        RedisClient().client.setex(
            _key(user_id, date_from, date_to),
            ttl,
            json.dumps(payload, default=str),
        )
    except Exception as e:
        logger.warning("tasks_range_cache: set failed for user %s: %s", user_id, e)


def invalidate_user_ranges(user_id: int) -> None:
    """Drop ALL cached ranges for a user. Called on TaskManager.create_task
    so a new task appears in any in-flight range query within 60s."""
    try:
        client = RedisClient().client
        # SCAN for the user-prefixed keys. Barzakh alpha cohort is small;
        # typical user has ≤ 5 cached ranges (different windows /pulse,
        # /table, /insights might be requesting). SCAN is non-blocking
        # so safe even if the prefix matches more.
        pattern = f"{_CACHE_KEY_PREFIX}{user_id}:*"
        for key in client.scan_iter(match=pattern, count=100):
            client.delete(key)
    except Exception as e:
        logger.warning(
            "tasks_range_cache: invalidate_user_ranges failed for user %s: %s",
            user_id, e,
        )
