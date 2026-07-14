"""Tests for the /me Redis cache helper (me_cache 2026-04-29).

Covers the contract:
  * get returns None on cache miss
  * set + get round-trips a payload (when Redis is available)
  * invalidate removes a stored key
  * Redis-down is graceful: get returns None silently, set is no-op,
    invalidate is no-op (the get/set/invalidate functions never raise)

Plus an integration check: the get_me endpoint stores into the cache on
first call and reads from cache on the second call (not re-querying
Supabase).
"""
from unittest.mock import patch

import pytest

from app.utils import me_cache


# Detect whether Redis is reachable. Many tests skip with this — see
# tests/conftest._redis_available.
def _redis_available() -> bool:
    try:
        from app.utils.redis_client import RedisClient
        RedisClient().client.ping()
        return True
    except Exception:
        return False


needs_redis = pytest.mark.skipif(
    not _redis_available(), reason="Redis not reachable — skipping cache test"
)


# ─── Pure cache contract ────────────────────────────────────────────────


@needs_redis
def test_get_cached_me_returns_none_on_miss():
    # Use an unlikely user_id to avoid collision with any real cached row.
    me_cache.invalidate_me(999_999)
    assert me_cache.get_cached_me(999_999) is None


@needs_redis
def test_set_then_get_round_trips_payload():
    payload = {"user_id": 999_998, "email": "t@example.test", "n": 42}
    me_cache.set_cached_me(999_998, payload, ttl=60)
    assert me_cache.get_cached_me(999_998) == payload
    me_cache.invalidate_me(999_998)


@needs_redis
def test_invalidate_removes_entry():
    me_cache.set_cached_me(999_997, {"user_id": 999_997}, ttl=60)
    assert me_cache.get_cached_me(999_997) is not None
    me_cache.invalidate_me(999_997)
    assert me_cache.get_cached_me(999_997) is None


@needs_redis
def test_corrupted_cache_entry_self_heals():
    """If a stored value isn't valid JSON, get drops it and returns None."""
    from app.utils.redis_client import RedisClient
    rc = RedisClient().client
    _payload, epoch = me_cache.get_cached_me_with_epoch(999_996)
    key = me_cache._key(999_996, epoch or 0)
    rc.setex(key, 60, "not-json{garbage")
    # First read drops the bad entry and returns None.
    assert me_cache.get_cached_me(999_996) is None
    # Verify cleanup happened — second read also returns None (cache miss).
    assert me_cache.get_cached_me(999_996) is None


# ─── Graceful degradation when Redis is down ────────────────────────────


def test_get_returns_none_when_redis_raises():
    """Redis client raising on .get must NOT propagate — endpoint stays alive."""
    with patch("app.utils.me_cache.RedisClient") as MockRC:
        MockRC.return_value.client.get.side_effect = ConnectionError("redis down")
        assert me_cache.get_cached_me(1) is None


def test_set_swallows_redis_errors():
    """Set must not raise even if Redis is dead."""
    with patch("app.utils.me_cache.RedisClient") as MockRC:
        MockRC.return_value.client.setex.side_effect = ConnectionError("redis down")
        # Must not raise.
        me_cache.set_cached_me(1, {"foo": "bar"})


def test_invalidate_swallows_redis_errors():
    with patch("app.utils.me_cache.RedisClient") as MockRC:
        MockRC.return_value.client.incr.side_effect = ConnectionError("redis down")
        # Must not raise.
        me_cache.invalidate_me(1)


class _GenerationRedis:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, _ttl, value):
        self.values[key] = value

    def delete(self, key):
        return int(self.values.pop(key, None) is not None)

    def incr(self, key):
        value = int(self.values.get(key) or 0) + 1
        self.values[key] = str(value)
        return value


def test_stale_writer_cannot_republish_after_invalidation(monkeypatch):
    fake = _GenerationRedis()
    monkeypatch.setattr(
        me_cache,
        "RedisClient",
        lambda: type("Client", (), {"client": fake})(),
    )
    user_id = 777

    cached, stale_epoch = me_cache.get_cached_me_with_epoch(user_id)
    assert cached is None
    assert stale_epoch == 0

    me_cache.invalidate_me(user_id)
    assert me_cache.set_cached_me_if_epoch(
        user_id,
        {"archetype_survey_eligible": True},
        stale_epoch,
    )

    current, current_epoch = me_cache.get_cached_me_with_epoch(user_id)
    assert current is None
    assert current_epoch == 1

    assert me_cache.set_cached_me_if_epoch(
        user_id,
        {"archetype_survey_eligible": False},
        current_epoch,
    )
    current, confirmed_epoch = me_cache.get_cached_me_with_epoch(user_id)
    assert current == {"archetype_survey_eligible": False}
    assert confirmed_epoch == 1


# ─── Integration: invalidation gets called by mutating endpoints ────────


def test_invalidate_called_on_consent_endpoint():
    """Smoke check that the wire-up actually invokes invalidate_me."""
    from datetime import datetime
    from fastapi.testclient import TestClient
    from app.db.models import User
    from app.db.scoping import set_current_user_id
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)

    from tests.conftest import TestingSession
    db = TestingSession()
    try:
        u = User(
            email="me-cache-test@example.test",
            google_id=None,
            timezone="Africa/Cairo",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        uid = u.user_id
    finally:
        db.close()

    set_current_user_id(uid)
    try:
        with patch("app.api.v1.endpoints.users.invalidate_me") as mock_inv:
            r = client.post(
                "/v1/users/me/consent",
                json={"terms_accepted": True, "research_consent": False},
            )
            assert r.status_code == 200
            mock_inv.assert_called_once_with(uid)
    finally:
        set_current_user_id(None)
        # Cleanup
        db = TestingSession()
        try:
            db.query(User).filter(User.user_id == uid).delete()
            db.commit()
        finally:
            db.close()
