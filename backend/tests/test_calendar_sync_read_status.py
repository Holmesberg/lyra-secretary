import json
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services import calendar_sync


class _FakeRedis:
    def __init__(self):
        self.cached = None

    def get(self, _key):
        return self.cached

    def setex(self, _key, _ttl, value):
        self.cached = value


class _FakeQuery:
    def __init__(self, user):
        self.user = user

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.user


class _FakeSession:
    def __init__(self, user):
        self.user = user
        self.closed = False

    def query(self, _model):
        return _FakeQuery(self.user)

    def close(self):
        self.closed = True


class _FakeCalendarRequest:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class _FakeCalendarService:
    def __init__(self, payload):
        self.payload = payload

    def events(self):
        return self

    def list(self, **_kwargs):
        return _FakeCalendarRequest(self.payload)


def _window():
    start = datetime(2026, 7, 13, 8, 0)
    return start, start + timedelta(days=1)


def _install_common(monkeypatch, *, user):
    redis = _FakeRedis()
    session = _FakeSession(user)
    monkeypatch.setattr(calendar_sync, "RedisClient", lambda: SimpleNamespace(client=redis))
    monkeypatch.setattr(calendar_sync, "SessionLocal", lambda: session)
    return redis, session


def test_google_calendar_read_status_distinguishes_empty_success_from_failure(
    monkeypatch,
):
    user = SimpleNamespace(
        user_id=17,
        google_refresh_token="encrypted-fixture",
        is_operator=False,
    )
    _redis, first_session = _install_common(monkeypatch, user=user)
    monkeypatch.setattr(calendar_sync, "_get_credentials", lambda _user, _db: object())
    monkeypatch.setattr(
        calendar_sync,
        "build",
        lambda *_args, **_kwargs: _FakeCalendarService({"items": []}),
    )
    start, end = _window()

    available = calendar_sync.fetch_google_events_with_status(user.user_id, start, end)

    assert available.status == "available"
    assert available.events == []
    assert available.reason is None
    assert first_session.closed is True

    _redis, failed_session = _install_common(monkeypatch, user=user)
    monkeypatch.setattr(
        calendar_sync,
        "build",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    unavailable = calendar_sync.fetch_google_events_with_status(user.user_id, start, end)

    assert unavailable.status == "unavailable"
    assert unavailable.events == []
    assert unavailable.reason == "provider_RuntimeError"
    assert failed_session.closed is True


def test_google_calendar_read_status_reports_not_connected(monkeypatch):
    user = SimpleNamespace(
        user_id=18,
        google_refresh_token=None,
        is_operator=False,
    )
    _redis, session = _install_common(monkeypatch, user=user)
    monkeypatch.setattr(calendar_sync, "_get_credentials", lambda _user, _db: None)
    start, end = _window()

    result = calendar_sync.fetch_google_events_with_status(user.user_id, start, end)

    assert result.status == "not_connected"
    assert result.events == []
    assert result.reason == "not_connected"
    assert session.closed is True


def test_google_calendar_partial_read_status_survives_cache(monkeypatch):
    user = SimpleNamespace(
        user_id=20,
        google_refresh_token="encrypted-fixture",
        is_operator=False,
    )
    redis, session = _install_common(monkeypatch, user=user)
    monkeypatch.setattr(calendar_sync, "_get_credentials", lambda _user, _db: object())
    monkeypatch.setattr(
        calendar_sync,
        "build",
        lambda *_args, **_kwargs: _FakeCalendarService(
            {
                "items": [
                    {
                        "id": "timed-event",
                        "summary": "Timed fixture",
                        "start": {"dateTime": "2026-07-13T08:00:00Z"},
                        "end": {"dateTime": "2026-07-13T09:00:00Z"},
                    },
                    {
                        "id": "all-day-event",
                        "summary": "All-day fixture",
                        "start": {"date": "2026-07-13"},
                        "end": {"date": "2026-07-14"},
                    },
                ],
                "nextPageToken": "more-events-exist",
            }
        ),
    )
    start, end = _window()

    first = calendar_sync.fetch_google_events_with_status(user.user_id, start, end)

    assert first.status == "partial"
    assert [event.id for event in first.events] == ["timed-event"]
    assert first.reason == "all_day_events_excluded,pagination_truncated"
    assert session.closed is True
    cached = json.loads(redis.cached)
    assert cached["status"] == "partial"
    assert cached["reason"] == first.reason

    second = calendar_sync.fetch_google_events_with_status(user.user_id, start, end)

    assert second.status == "partial"
    assert [event.id for event in second.events] == ["timed-event"]
    assert second.reason == first.reason


def test_google_calendar_legacy_cached_list_remains_available(monkeypatch):
    user = SimpleNamespace(
        user_id=21,
        google_refresh_token="encrypted-fixture",
        is_operator=False,
    )
    redis, session = _install_common(monkeypatch, user=user)
    redis.cached = json.dumps(
        [
            {
                "id": "legacy-event",
                "title": "Legacy fixture",
                "start": "2026-07-13T10:00:00",
                "end": "2026-07-13T11:00:00",
                "calendar_id": "primary",
                "source": "google",
            }
        ]
    )
    start, end = _window()

    result = calendar_sync.fetch_google_events_with_status(user.user_id, start, end)

    assert result.status == "available"
    assert result.reason is None
    assert [event.id for event in result.events] == ["legacy-event"]
    assert session.closed is False


def test_google_calendar_compatibility_reader_returns_only_events(monkeypatch):
    event = calendar_sync.ExternalEvent(
        id="event-1",
        title="Fixture",
        start="2026-07-13T10:00:00",
        end="2026-07-13T11:00:00",
        calendar_id="primary",
    )
    monkeypatch.setattr(
        calendar_sync,
        "fetch_google_events_with_status",
        lambda *_args: calendar_sync.ExternalEventFetchResult(
            events=[event],
            status="available",
        ),
    )
    start, end = _window()

    assert calendar_sync.fetch_google_events(19, start, end) == [event]
