"""Per-user cache for the /v1/users/me response.

Why this exists (2026-04-29 latency sweep): /v1/users/me runs 5 sequential
queries to Supabase eu-west-1 from the operator's Cairo laptop. Each
round-trip is ~600ms over Cloudflare Tunnel — the endpoint takes 3–5s.
Frontend hits it on every page load + every tab switch (via the layout
shell), so it's the single biggest contributor to "the app feels slow."

Strategy:
  * Cache the full /me response JSON for 30s, keyed by user_id.
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

Cache key versioned ("v1") so a future shape change just bumps the
version — old keys age out via TTL.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.utils.redis_client import RedisClient

logger = logging.getLogger(__name__)

_CACHE_KEY_PREFIX = "me:"
_CACHE_KEY_VERSION = "v1"
_DEFAULT_TTL_SECONDS = 30


def _key(user_id: int) -> str:
    return f"{_CACHE_KEY_PREFIX}{user_id}:{_CACHE_KEY_VERSION}"


def get_cached_me(user_id: int) -> Optional[dict[str, Any]]:
    """Return the cached /me payload for this user, or None on miss/error.

    Never raises — Redis-down or cache-poisoning fall through to None
    so the endpoint runs its normal path.
    """
    try:
        raw = RedisClient().client.get(_key(user_id))
    except Exception as e:
        # Don't let Redis hiccups break sign-in. Logged but non-blocking.
        logger.warning("me_cache: get failed for user %s: %s", user_id, e)
        return None
    if raw is None:
        return None
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)
    except Exception as e:
        logger.warning(
            "me_cache: cached payload parse failed for user %s, dropping: %s",
            user_id, e,
        )
        # Best-effort cleanup — corrupted entry should self-heal next call.
        try:
            RedisClient().client.delete(_key(user_id))
        except Exception:
            pass
        return None


def set_cached_me(
    user_id: int, payload: dict[str, Any], ttl: int = _DEFAULT_TTL_SECONDS
) -> None:
    """Store a /me response payload with TTL. Silent on failure."""
    try:
        RedisClient().client.setex(
            _key(user_id), ttl, json.dumps(payload, default=str)
        )
    except Exception as e:
        logger.warning("me_cache: set failed for user %s: %s", user_id, e)


def invalidate_me(user_id: int) -> None:
    """Drop the cached /me for this user. Called by mutating endpoints."""
    try:
        RedisClient().client.delete(_key(user_id))
    except Exception as e:
        logger.warning("me_cache: invalidate failed for user %s: %s", user_id, e)
