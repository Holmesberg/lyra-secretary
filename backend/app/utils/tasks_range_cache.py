"""Per-user cache for the canonical ``/v1/tasks/query`` range response.

Pulse, Calendar, and Table share this heavier range read. Cache entries are
scoped by user, date window, and mutation generation. A mutating command
advances the generation, so an older in-flight read may finish but can publish
only into an obsolete generation. Redis failure remains a cache miss and never
blocks the endpoint.

Superseded payloads expire after 60 seconds. User-data purge already removes
the complete ``tasks_range:{user_id}:*`` namespace, including generation keys.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.utils.redis_client import RedisClient

logger = logging.getLogger(__name__)

_CACHE_KEY_PREFIX = "tasks_range:"
_CACHE_KEY_VERSION = "v2"
_DEFAULT_TTL_SECONDS = 60


def _epoch_key(user_id: int) -> str:
    return f"{_CACHE_KEY_PREFIX}{user_id}:epoch:{_CACHE_KEY_VERSION}"


def _key(user_id: int, epoch: int, date_from: str, date_to: str) -> str:
    return (
        f"{_CACHE_KEY_PREFIX}{user_id}:{epoch}:"
        f"{date_from}:{date_to}:{_CACHE_KEY_VERSION}"
    )


def _decode_epoch(raw: Any) -> int:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return int(raw or 0)


def get_cached_range_with_epoch(
    user_id: int, date_from: str, date_to: str
) -> tuple[Optional[dict[str, Any]], Optional[int]]:
    """Return the current payload and generation safe for publication."""
    try:
        client = RedisClient().client
        confirmed_epoch = 0
        for _attempt in range(2):
            epoch = _decode_epoch(client.get(_epoch_key(user_id)))
            key = _key(user_id, epoch, date_from, date_to)
            raw = client.get(key)
            confirmed_epoch = _decode_epoch(client.get(_epoch_key(user_id)))
            if confirmed_epoch != epoch:
                continue
            if raw is None:
                return None, epoch
            try:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                return json.loads(raw), epoch
            except Exception as exc:
                logger.warning(
                    "tasks_range_cache: parse failed for user %s, dropping: %s",
                    user_id,
                    exc,
                )
                try:
                    client.delete(key)
                except Exception:
                    pass
                return None, epoch
        return None, confirmed_epoch
    except Exception as exc:
        logger.warning(
            "tasks_range_cache: get failed for user %s: %s",
            user_id,
            exc,
        )
        return None, None


def get_cached_range(
    user_id: int, date_from: str, date_to: str
) -> Optional[dict[str, Any]]:
    """Return the current cached payload, or ``None`` on miss/error."""
    payload, _epoch = get_cached_range_with_epoch(user_id, date_from, date_to)
    return payload


def set_cached_range(
    user_id: int,
    date_from: str,
    date_to: str,
    payload: dict[str, Any],
    ttl: int = _DEFAULT_TTL_SECONDS,
) -> None:
    """Store against the current generation. Silent on Redis failure."""
    try:
        client = RedisClient().client
        epoch = _decode_epoch(client.get(_epoch_key(user_id)))
        client.setex(
            _key(user_id, epoch, date_from, date_to),
            ttl,
            json.dumps(payload, default=str),
        )
    except Exception as exc:
        logger.warning(
            "tasks_range_cache: set failed for user %s: %s",
            user_id,
            exc,
        )


def set_cached_range_if_epoch(
    user_id: int,
    date_from: str,
    date_to: str,
    payload: dict[str, Any],
    expected_epoch: Optional[int],
    ttl: int = _DEFAULT_TTL_SECONDS,
) -> bool:
    """Publish into a captured generation; stale generations stay unread."""
    if expected_epoch is None:
        return False
    try:
        RedisClient().client.setex(
            _key(user_id, expected_epoch, date_from, date_to),
            ttl,
            json.dumps(payload, default=str),
        )
        return True
    except Exception as exc:
        logger.warning(
            "tasks_range_cache: fenced set failed for user %s: %s",
            user_id,
            exc,
        )
        return False


def invalidate_user_ranges(user_id: int) -> None:
    """Advance the user's generation so older publications become unread."""
    try:
        RedisClient().client.incr(_epoch_key(user_id))
    except Exception as exc:
        logger.warning(
            "tasks_range_cache: invalidate_user_ranges failed for user %s: %s",
            user_id,
            exc,
        )
