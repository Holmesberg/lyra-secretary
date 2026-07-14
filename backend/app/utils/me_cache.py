"""Per-user cache for the /v1/users/me response.

Why this exists (2026-04-29 latency sweep): /v1/users/me runs 5 sequential
queries to Supabase eu-west-1 from the operator's Cairo laptop. Each
round-trip is ~600ms over Cloudflare Tunnel — the endpoint takes 3–5s.
Frontend hits it on every page load + every tab switch (via the layout
shell), so it's the single biggest contributor to "the app feels slow."

Strategy:
  * Cache the full /me response JSON for 30s, keyed by user and mutation
    generation.
  * Bust ONLY on user-row mutations (~10 endpoints) — accept 30s of
    stale `executed_session_count` and `has_active_task_history`. The
    one exception that must bust outside the user row: the first
    TaskManager.create_task per user (flips has_active_task_history
    false→true, gating the onboarding screen).
  * Lazy-stamp side effects (d1_return_at, onboarding backfill) fire
    on cache MISS only. They're one-time stamps so missing them on
    cache hits is correct — the next miss after the 30s window will
    handle the first eligible call.
  * Redis-down is graceful: cache get/set silently fall through; the
    endpoint runs the queries directly. Same shape as
    services/calendar_sync.py.

Invalidation advances the generation. An older in-flight read may finish, but
its payload is published only under the obsolete generation and cannot become
current. Payload keys remain versioned so old generations age out via TTL.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.utils.redis_client import RedisClient

logger = logging.getLogger(__name__)

_CACHE_KEY_PREFIX = "me:"
_CACHE_KEY_VERSION = "v2"
_DEFAULT_TTL_SECONDS = 30


def _epoch_key(user_id: int) -> str:
    return f"{_CACHE_KEY_PREFIX}{user_id}:epoch:{_CACHE_KEY_VERSION}"


def _key(user_id: int, epoch: int = 0) -> str:
    return f"{_CACHE_KEY_PREFIX}{user_id}:{epoch}:{_CACHE_KEY_VERSION}"


def _decode_epoch(raw: Any) -> int:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return int(raw or 0)


def get_cached_me_with_epoch(
    user_id: int,
) -> tuple[Optional[dict[str, Any]], Optional[int]]:
    """Return the current payload and the generation safe for publication."""
    try:
        client = RedisClient().client
        confirmed_epoch = 0
        for _attempt in range(2):
            epoch = _decode_epoch(client.get(_epoch_key(user_id)))
            raw = client.get(_key(user_id, epoch))
            confirmed_epoch = _decode_epoch(client.get(_epoch_key(user_id)))
            if confirmed_epoch != epoch:
                continue
            if raw is None:
                return None, epoch
            try:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                return json.loads(raw), epoch
            except Exception as e:
                logger.warning(
                    "me_cache: cached payload parse failed for user %s, "
                    "dropping: %s",
                    user_id,
                    e,
                )
                try:
                    client.delete(_key(user_id, epoch))
                except Exception:
                    pass
                return None, epoch
        return None, confirmed_epoch
    except Exception as e:
        logger.warning("me_cache: get failed for user %s: %s", user_id, e)
        return None, None


def get_cached_me(user_id: int) -> Optional[dict[str, Any]]:
    """Return the cached /me payload for this user, or None on miss/error.

    Never raises — Redis-down or cache-poisoning fall through to None
    so the endpoint runs its normal path.
    """
    payload, _epoch = get_cached_me_with_epoch(user_id)
    return payload


def set_cached_me(
    user_id: int, payload: dict[str, Any], ttl: int = _DEFAULT_TTL_SECONDS
) -> None:
    """Store a /me response payload with TTL. Silent on failure."""
    try:
        client = RedisClient().client
        epoch = _decode_epoch(client.get(_epoch_key(user_id)))
        client.setex(_key(user_id, epoch), ttl, json.dumps(payload, default=str))
    except Exception as e:
        logger.warning("me_cache: set failed for user %s: %s", user_id, e)


def set_cached_me_if_epoch(
    user_id: int,
    payload: dict[str, Any],
    expected_epoch: Optional[int],
    ttl: int = _DEFAULT_TTL_SECONDS,
) -> bool:
    """Publish into the captured generation; stale generations stay unread."""
    if expected_epoch is None:
        return False
    try:
        RedisClient().client.setex(
            _key(user_id, expected_epoch),
            ttl,
            json.dumps(payload, default=str),
        )
        return True
    except Exception as e:
        logger.warning("me_cache: fenced set failed for user %s: %s", user_id, e)
        return False


def invalidate_me(user_id: int) -> None:
    """Advance the user's generation so older publications become unread."""
    try:
        RedisClient().client.incr(_epoch_key(user_id))
    except Exception as e:
        logger.warning("me_cache: invalidate failed for user %s: %s", user_id, e)
