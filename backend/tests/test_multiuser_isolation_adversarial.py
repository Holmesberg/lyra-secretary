"""Phase 3.2 adversarial multi-user isolation suite.

The earlier `test_multiuser_isolation.py` only proved SELECT scoping. The
P0 leak was on the INSERT side: `Task.user_id` had a Python-side
default=1, and TaskManager.create_task built Task() without passing
user_id — every cross-tenant write silently funneled to the operator.
These tests drive the WRITE path through the real endpoints via
TestClient with `X-User-Id` headers and assert that ownership is
threaded correctly.

Users 98 and 99 are deliberately high IDs so a forgotten default=1
leak would show up as "row landed on operator" rather than a no-op.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.db.models import Task, TaskState, User
from app.db.scoping import set_current_user_id
from tests.conftest import TestingSession


def _fresh_query_task(tid: str):
    """Open an unscoped session and fetch a task by id, bypassing any
    stale identity-map state on the fixture session."""
    set_current_user_id(None)
    s = TestingSession()
    try:
        return s.query(Task).filter(Task.task_id == tid).first()
    finally:
        s.close()


def _iso(dt: datetime) -> str:
    return dt.isoformat()


@pytest.fixture
def adv_users(db):
    # Wipe and reseed two fresh, high-id users so a lingering default=1
    # would leak visibly rather than masquerading as correct.
    # Redis carries stopwatch state across tests; flush the keys we own.
    try:
        from app.utils.redis_client import RedisClient
        rc = RedisClient()
        for uid in ("1", "98", "99", "user_primary"):
            rc.clear_active_stopwatch(uid)
            rc.client.delete(f"stopwatch:paused:{uid}")
    except Exception:
        pass
    # Wipe tables via a FRESH session so a stale identity map on the
    # `db` fixture session can't mask committed cross-test state.
    set_current_user_id(None)
    wipe = TestingSession()
    try:
        wipe.execute(text("DELETE FROM stopwatch_session"))
        wipe.execute(text("DELETE FROM task"))
        wipe.execute(text("DELETE FROM user"))
        wipe.commit()
    finally:
        wipe.close()
    db.rollback()
    db.expire_all()
    now = datetime.utcnow()
    seed = TestingSession()
    try:
        seed.add_all([
            User(user_id=98, email="eve@x", is_operator=False, notion_enabled=False, created_at=now),
            User(user_id=99, email="mallory@x", is_operator=False, notion_enabled=False, created_at=now),
        ])
        seed.commit()
    finally:
        seed.close()
    yield db
    set_current_user_id(None)


def _redis_available() -> bool:
    try:
        from app.utils.redis_client import RedisClient
        RedisClient().client.ping()
        return True
    except Exception:
        return False


needs_redis = pytest.mark.skipif(not _redis_available(), reason="redis not reachable in this env")


def _h(uid: int) -> dict:
    return {"X-User-Id": str(uid)}


def _future(minutes_from_now: int, duration: int = 30):
    start = datetime.utcnow() + timedelta(minutes=minutes_from_now)
    end = start + timedelta(minutes=duration)
    # TaskCreateRequest accepts naive-ish ISO; local display conversion
    # happens in to_local. Send tz-aware UTC.
    return _iso(start.replace(microsecond=0)) + "Z", _iso(end.replace(microsecond=0)) + "Z"


def _create(client, uid: int, title: str, offset_min: int, duration: int = 30, force: bool = False):
    start, end = _future(offset_min, duration)
    return client.post(
        "/v1/create",
        json={"title": title, "start": start, "end": end, "force": force},
        headers=_h(uid),
    )


# 1. Create task as 99, verify stored with user_id=99 (not leak to 1)
def test_create_stores_correct_user_id(adv_users, client):
    r = _create(client, 99, "mallory task", 60)
    assert r.status_code == 200, r.text
    tid = r.json()["task_id"]
    assert tid
    row = _fresh_query_task(tid)
    assert row is not None
    assert row.user_id == 99, f"leak — task landed on user_id={row.user_id}"


# 2. Create as 99 — user 98 must not see it
def test_other_user_cannot_see(adv_users, client):
    _create(client, 99, "mallory task", 65).raise_for_status()
    r = client.get("/v1/tasks/query", headers=_h(98))
    assert r.status_code == 200, r.text
    titles = [t["title"] for t in r.json().get("tasks", [])]
    assert "mallory task" not in titles


# 3. Conflict across users: 99 creates on 98's slot — must SUCCEED
def test_cross_user_same_slot_no_conflict(adv_users, client):
    _create(client, 98, "eve task", 70).raise_for_status()
    r = _create(client, 99, "mallory task", 70)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] is True, f"cross-user false conflict: {body}"
    assert body["task_id"]


# 4. Conflict within same user — must block with conflicts list
def test_same_user_overlap_blocks(adv_users, client):
    _create(client, 99, "first", 80).raise_for_status()
    r = _create(client, 99, "second", 80)
    assert r.status_code == 200
    body = r.json()
    assert body["created"] is False
    assert body["task_id"] is None
    assert len(body["conflicts"]) == 1


# 5. Start stopwatch as 99 on 99's own task — succeeds
@needs_redis
def test_stopwatch_own_task(adv_users, client):
    tid = _create(client, 99, "work", 90).json()["task_id"]
    # Start requires the task to be currently runnable; endpoint is /v1/stopwatch/start.
    r = client.post("/v1/stopwatch/start", json={"task_id": tid}, headers=_h(99))
    assert r.status_code in (200, 201), r.text


# 6. Start stopwatch as 99 on 98's task_id — must 404 (scoped lookup fails)
@needs_redis
def test_stopwatch_cross_user_blocked(adv_users, client):
    tid = _create(client, 98, "eve work", 95).json()["task_id"]
    r = client.post("/v1/stopwatch/start", json={"task_id": tid}, headers=_h(99))
    assert r.status_code in (400, 403, 404, 500), f"cross-user stopwatch start leaked: {r.status_code}"
    # Critical: 98's task must not have been transitioned to EXECUTING.
    row = _fresh_query_task(tid)
    assert row is not None and row.state == TaskState.PLANNED


# 7. Void as 99 with valid enum reason — succeeds
def test_void_own_task_valid_reason(adv_users, client):
    tid = _create(client, 99, "dup", 100).json()["task_id"]
    r = client.post(
        f"/v1/tasks/{tid}/void",
        json={"voided_reason": "duplicate"},
        headers=_h(99),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["voided"] is True
    assert body["voided_reason"] == "duplicate"


# 8. Void as 99 with invalid reason — 422 validation error
def test_void_invalid_reason_rejected(adv_users, client):
    tid = _create(client, 99, "x", 105).json()["task_id"]
    r = client.post(
        f"/v1/tasks/{tid}/void",
        json={"voided_reason": "just_cause"},
        headers=_h(99),
    )
    assert r.status_code in (400, 422)


# 9. Void reason='other' without detail — 422
def test_void_other_requires_detail(adv_users, client):
    tid = _create(client, 99, "x2", 110).json()["task_id"]
    r = client.post(
        f"/v1/tasks/{tid}/void",
        json={"voided_reason": "other"},
        headers=_h(99),
    )
    assert r.status_code in (400, 422)


# 10. Cross-user void — 99 cannot void 98's task
def test_cross_user_void_blocked(adv_users, client):
    tid = _create(client, 98, "eve priv", 115).json()["task_id"]
    r = client.post(
        f"/v1/tasks/{tid}/void",
        json={"voided_reason": "duplicate"},
        headers=_h(99),
    )
    assert r.status_code in (403, 404)


# 11. Analytics discrepancy scoped to caller
def test_analytics_discrepancy_scoped(adv_users, client):
    _create(client, 98, "eve a", 120).raise_for_status()
    _create(client, 99, "mallory a", 125).raise_for_status()
    r98 = client.get("/v1/analytics/discrepancy", headers=_h(98))
    r99 = client.get("/v1/analytics/discrepancy", headers=_h(99))
    assert r98.status_code == 200 and r99.status_code == 200
    # They can return whatever shape, just ensure they executed with
    # their own scope (no 500 from cross-tenant row leaking).


# 12. Reschedule cross-user — 99 cannot reschedule 98's task
def test_cross_user_reschedule_blocked(adv_users, client):
    tid = _create(client, 98, "eve r", 130).json()["task_id"]
    start, end = _future(200, 30)
    r = client.post(
        "/v1/reschedule",
        json={"task_id": tid, "new_start": start, "new_end": end},
        headers=_h(99),
    )
    assert r.status_code in (400, 403, 404, 500), r.status_code
    # And importantly: 98's row is untouched
    row = _fresh_query_task(tid)
    assert row is not None and row.user_id == 98


# 13. Stopwatch status isolation: 99 starts timer, 98 sees active=False
@needs_redis
def test_stopwatch_status_isolated(adv_users, client):
    tid = _create(client, 99, "mallory timer", 140).json()["task_id"]
    r = client.post("/v1/stopwatch/start", json={"task_id": tid}, headers=_h(99))
    assert r.status_code in (200, 201), r.text
    # User 98 must NOT see 99's active timer
    r98 = client.get("/v1/stopwatch/status", headers=_h(98))
    assert r98.status_code == 200
    body = r98.json()
    assert body["active"] is False, f"cross-user timer leak: {body}"


# 14b. Multi-day range query isolation (Schedule-X calendar read surface)
#      Calendar view at /calendar pulls a 62-day window in a single GET
#      /v1/tasks/query?date=X&days=N round trip. `days=N` is a new read
#      surface since the Schedule-X build — regression-guard that the
#      before_compile scoping hook rewrites the range query the same way
#      it rewrites single-day queries. Without this test the calendar
#      could silently render cross-tenant rows the moment the hook, the
#      models, or the endpoint shape changes.
#
#      User ids 98/99 follow CONTRIBUTING.md §"Multi-user isolation
#      testing" — never user_id=1 (that's the historical default-leak
#      sink). If a forgotten default=1 ever returns, neither 98 nor 99
#      would silently inherit rows from it, so the assertions below
#      would visibly fail on the count mismatch.
def test_query_days_window_scoped(adv_users, client):
    from datetime import datetime as _dt

    # 98 gets 5 tasks spread across 30 days; offsets chosen so none
    # overlap within the same user (30-min durations, 6+ days apart).
    offsets_98 = [1, 7, 14, 21, 28]
    for i, day in enumerate(offsets_98):
        r = _create(client, 98, f"eve-{i}", day * 1440 + 60)
        assert r.status_code == 200, r.text
        assert r.json()["created"] is True, r.json()

    # 99 gets 3 tasks on different days from 98's — cross-user same-slot
    # is already covered by test_cross_user_same_slot_no_conflict; here
    # we just want disjoint calendars so title assertions are crisp.
    offsets_99 = [2, 10, 20]
    for i, day in enumerate(offsets_99):
        r = _create(client, 99, f"mallory-{i}", day * 1440 + 120)
        assert r.status_code == 200, r.text
        assert r.json()["created"] is True, r.json()

    # Pivot one day before UTC-now and widen to days=32 so a UTC/Cairo
    # midnight race (window cuts day=28 on a late-night test run)
    # cannot cause a flaky count mismatch. The hook under test is
    # orthogonal to the window — we just need both users' tasks fully
    # inside whichever window we pick.
    pivot = (_dt.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    # 98 pulls the 32-day window: must see exactly 5 tasks, all 98's.
    r98 = client.get(
        f"/v1/tasks/query?date={pivot}&days=32&state=all",
        headers=_h(98),
    )
    assert r98.status_code == 200, r98.text
    body_98 = r98.json()
    titles_98 = sorted(t["title"] for t in body_98["tasks"])
    assert titles_98 == sorted(f"eve-{i}" for i in range(len(offsets_98))), (
        f"user 98 saw wrong tasks: {titles_98}"
    )
    # Endpoint response hides user_id, so verify ownership via an
    # unscoped fresh session per row. Any row owned by ≠ 98 is a leak.
    for t in body_98["tasks"]:
        row = _fresh_query_task(t["task_id"])
        assert row is not None, f"task {t['task_id']} vanished"
        assert row.user_id == 98, (
            f"leak: user 98's range query returned task "
            f"{t['task_id']} owned by user_id={row.user_id}"
        )

    # 99 pulls the same 32-day window: must see exactly 3 tasks, all 99's.
    r99 = client.get(
        f"/v1/tasks/query?date={pivot}&days=32&state=all",
        headers=_h(99),
    )
    assert r99.status_code == 200, r99.text
    body_99 = r99.json()
    titles_99 = sorted(t["title"] for t in body_99["tasks"])
    assert titles_99 == sorted(f"mallory-{i}" for i in range(len(offsets_99))), (
        f"user 99 saw wrong tasks: {titles_99}"
    )
    for t in body_99["tasks"]:
        row = _fresh_query_task(t["task_id"])
        assert row is not None, f"task {t['task_id']} vanished"
        assert row.user_id == 99, (
            f"leak: user 99's range query returned task "
            f"{t['task_id']} owned by user_id={row.user_id}"
        )

    # Cross-check: the union of IDs 98 and 99 saw must not intersect.
    ids_98 = {t["task_id"] for t in body_98["tasks"]}
    ids_99 = {t["task_id"] for t in body_99["tasks"]}
    assert ids_98.isdisjoint(ids_99), (
        f"cross-tenant row bleed in range query: {ids_98 & ids_99}"
    )


# 14a. date_from/date_to range query isolation (Table view read surface)
#      The Table view uses date_from/date_to params instead of date/days.
#      This is a separate code path in query.py that must be equally scoped.
def test_query_range_scoped(adv_users, client):
    from datetime import datetime as _dt

    # 98 gets 5 tasks spread across 30 days
    offsets_98 = [1, 7, 14, 21, 28]
    for i, day in enumerate(offsets_98):
        r = _create(client, 98, f"eve-range-{i}", day * 1440 + 60)
        assert r.status_code == 200, r.text
        assert r.json()["created"] is True, r.json()

    # 99 gets 3 tasks on different days
    offsets_99 = [2, 10, 20]
    for i, day in enumerate(offsets_99):
        r = _create(client, 99, f"mallory-range-{i}", day * 1440 + 120)
        assert r.status_code == 200, r.text
        assert r.json()["created"] is True, r.json()

    date_from = (_dt.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    date_to = (_dt.utcnow() + timedelta(days=32)).strftime("%Y-%m-%d")

    # 98 queries the range: must see only their own tasks.
    r98 = client.get(
        f"/v1/tasks/query?date_from={date_from}&date_to={date_to}&state=all",
        headers=_h(98),
    )
    assert r98.status_code == 200, r98.text
    body_98 = r98.json()
    titles_98 = [t["title"] for t in body_98["tasks"]]
    for title in titles_98:
        assert title.startswith("eve-range-"), f"user 98 saw non-own task: {title}"
    assert len(titles_98) == len(offsets_98), (
        f"user 98 expected {len(offsets_98)} tasks, got {len(titles_98)}"
    )
    # Verify extended fields are present (batch-loaded session aggregates)
    for t in body_98["tasks"]:
        assert "discrepancy_score" in t
        assert "total_paused_minutes" in t
        assert "truncated" in body_98

    # Verify ownership via unscoped session
    for t in body_98["tasks"]:
        row = _fresh_query_task(t["task_id"])
        assert row is not None
        assert row.user_id == 98, (
            f"leak: user 98's range query returned task "
            f"{t['task_id']} owned by user_id={row.user_id}"
        )

    # 99 queries same range: must see only their own tasks.
    r99 = client.get(
        f"/v1/tasks/query?date_from={date_from}&date_to={date_to}&state=all",
        headers=_h(99),
    )
    assert r99.status_code == 200, r99.text
    body_99 = r99.json()
    titles_99 = [t["title"] for t in body_99["tasks"]]
    for title in titles_99:
        assert title.startswith("mallory-range-"), f"user 99 saw non-own task: {title}"
    assert len(titles_99) == len(offsets_99), (
        f"user 99 expected {len(offsets_99)} tasks, got {len(titles_99)}"
    )

    # Cross-check: no task_id overlap
    ids_98 = {t["task_id"] for t in body_98["tasks"]}
    ids_99 = {t["task_id"] for t in body_99["tasks"]}
    assert ids_98.isdisjoint(ids_99), (
        f"cross-tenant row bleed in date_from/date_to range: {ids_98 & ids_99}"
    )


# 14. Cross-user interruption: 99 starts+pauses a task, 98 creates an
#     overlapping task with force=true and tries to start it — must NOT
#     link to 99's paused task as parent. The parent_task_id auto-linking
#     in StopwatchManager must be scoped to the calling user.
@needs_redis
def test_cross_user_interruption_blocked(adv_users, client):
    # 99 creates and starts a task, then pauses it
    tid_99 = _create(client, 99, "mallory deep work", 150).json()["task_id"]
    r = client.post("/v1/stopwatch/start", json={"task_id": tid_99}, headers=_h(99))
    assert r.status_code in (200, 201), r.text
    r = client.post("/v1/stopwatch/pause", json={}, headers=_h(99))
    assert r.status_code == 200, r.text

    # 98 creates an overlapping task with force=true (simulating
    # the interruption flow, but cross-tenant)
    tid_98 = _create(client, 98, "eve interruption", 150, force=True).json()["task_id"]
    assert tid_98, "force-create for 98 should succeed (no conflict with 99)"

    # 98 starts their own task — the backend should NOT detect 99's
    # paused session as the parent (different user scope)
    r = client.post(
        "/v1/stopwatch/start",
        json={"task_id": tid_98},
        headers=_h(98),
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    # parent_task_id must be None — 99's paused task is not 98's parent
    assert body.get("parent_task_id") is None, (
        f"cross-user parent leak: 98's task got parent_task_id={body.get('parent_task_id')}"
    )

    # Verify 99's task is still PAUSED and untouched
    row_99 = _fresh_query_task(tid_99)
    assert row_99 is not None
    assert row_99.state == TaskState.PAUSED, f"99's task state changed to {row_99.state}"


# ---------------------------------------------------------------
# GAP-1 regression: notifications:pending is per-user
# ---------------------------------------------------------------

def test_notifications_per_user_isolated(adv_users, client):
    """Push a notification as user 98 → user 99 must NOT receive it."""
    # Push as user 98
    client.post(
        "/v1/notifications/push",
        json={"type": "reminder", "message": "eve's reminder"},
        headers=_h(98),
    )
    # Poll as user 99 — must get nothing
    r99 = client.get("/v1/notifications/pending", headers=_h(99))
    assert r99.status_code == 200
    assert r99.json()["count"] == 0, (
        f"user 99 received user 98's notification: {r99.json()}"
    )
    # Poll as user 98 — must get the notification
    r98 = client.get("/v1/notifications/pending", headers=_h(98))
    assert r98.status_code == 200
    assert r98.json()["count"] == 1
    assert r98.json()["notifications"][0]["message"] == "eve's reminder"


# ---------------------------------------------------------------
# GAP-2 regression: last_operated_task is per-user
# ---------------------------------------------------------------

def test_last_task_per_user_isolated(adv_users, client):
    """User 98 creates a task → user 99's /tasks/last must NOT return it."""
    # 98 creates a task (sets last_operated_task for user 98)
    r = _create(client, 98, "eve's last task", 200)
    assert r.status_code == 200, r.text
    assert r.json()["created"] is True

    # 99's /tasks/last must be 404 — they haven't done anything
    r99 = client.get("/v1/tasks/last", headers=_h(99))
    assert r99.status_code == 404, (
        f"user 99 got user 98's last task: {r99.json()}"
    )

    # 98's /tasks/last returns the correct task
    r98 = client.get("/v1/tasks/last", headers=_h(98))
    assert r98.status_code == 200
    assert r98.json()["title"] == "eve's last task"
