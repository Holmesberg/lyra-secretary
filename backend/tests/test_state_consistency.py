"""5-state system consistency checks across Task/Session/Redis/Notion/Scheduler.

Gate #11 in the durable verification suite. Runs after any commit touching
a state transition path (stop, pause, resume, void, skip, delete, mark_abandoned,
interruption, reschedule, early_stop override).

Verifies invariants that cross system boundaries — the class of bugs where
4 of 5 systems agree but 1 doesn't, and the symptom appears hours later in
dogfood (ghost banner incident Apr 11, mark-abandoned Redis leak Apr 12).

Invariants checked:
  1. Terminal task state (SKIPPED, EXECUTED, DELETED) → no Redis active/paused
  2. EXECUTING → Redis active key present, session end_time_utc is None
  3. PAUSED → Redis paused key present, session paused_at_utc stamped
  4. mark_abandoned → session end_time_utc set + Redis cleared + task SKIPPED
  5. void_task → session end_time_utc set + Redis cleared + voided_at stamped
  6. update_completion → session.task_completion_percentage set, timer still active
  7. APScheduler → all 5 jobs registered
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.db.models import StopwatchSession, Task, TaskState, User
from app.db.scoping import set_current_user_id
from tests.conftest import TestingSession


def _redis_available() -> bool:
    try:
        from app.utils.redis_client import RedisClient
        RedisClient().client.ping()
        return True
    except Exception:
        return False


needs_redis = pytest.mark.skipif(
    not _redis_available(), reason="redis not reachable"
)

USER_ID = 77  # dedicated to this test file, avoids collision


@pytest.fixture
def state_env(db):
    """Clean state: wipe Redis + DB, seed a single user."""
    try:
        from app.utils.redis_client import RedisClient
        rc = RedisClient()
        for uid in ("1", str(USER_ID), "user_primary"):
            rc.clear_active_stopwatch(uid)
            rc.client.delete(f"stopwatch:paused:{uid}")
    except Exception:
        pass

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
    seed = TestingSession()
    try:
        seed.add(User(
            user_id=USER_ID, email="state-consistency@test",
            is_operator=False, notion_enabled=False,
            created_at=datetime.utcnow(),
        ))
        seed.commit()
    finally:
        seed.close()

    yield db
    set_current_user_id(None)


def _h() -> dict:
    return {"X-User-Id": str(USER_ID)}


def _future(minutes: int = 10, duration: int = 60):
    start = datetime.utcnow() + timedelta(minutes=minutes)
    end = start + timedelta(minutes=duration)
    return (
        start.replace(microsecond=0).isoformat() + "Z",
        end.replace(microsecond=0).isoformat() + "Z",
    )


def _create_and_start(client, title="consistency test", readiness=3):
    """Helper: create a PLANNED task and start its timer. Returns task_id."""
    start, end = _future(10, 60)
    r = client.post(
        "/v1/create",
        json={"title": title, "start": start, "end": end},
        headers=_h(),
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["task_id"]

    r = client.post(
        "/v1/stopwatch/start",
        json={"task_id": task_id, "pre_task_readiness": readiness},
        headers=_h(),
    )
    assert r.status_code == 200, r.text
    return task_id


def _assert_redis_clear(uid: str = str(USER_ID)):
    """Assert no Redis active/paused keys for this user."""
    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    assert rc.get_active_stopwatch(uid) is None, (
        f"Redis stopwatch:active:{uid} should be None after terminal transition"
    )
    assert rc.get_pause_state(uid) is None, (
        f"Redis stopwatch:paused:{uid} should be None after terminal transition"
    )


def _assert_redis_active(uid: str = str(USER_ID)):
    """Assert Redis active key exists for this user."""
    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    active = rc.get_active_stopwatch(uid)
    assert active is not None, (
        f"Redis stopwatch:active:{uid} should exist for EXECUTING task"
    )
    return active


def _assert_session_closed(task_id: str):
    """Assert StopwatchSession for this task has end_time_utc set."""
    check = TestingSession()
    try:
        sessions = check.query(StopwatchSession).filter(
            StopwatchSession.task_id == task_id,
        ).all()
        assert len(sessions) >= 1, f"No StopwatchSession found for task {task_id}"
        for s in sessions:
            assert s.end_time_utc is not None, (
                f"StopwatchSession {s.session_id} for task {task_id} "
                f"must have end_time_utc after terminal transition"
            )
    finally:
        check.close()


def _assert_session_open(task_id: str):
    """Assert at least one open StopwatchSession for this task."""
    check = TestingSession()
    try:
        unclosed = check.query(StopwatchSession).filter(
            StopwatchSession.task_id == task_id,
            StopwatchSession.end_time_utc.is_(None),
        ).all()
        assert len(unclosed) == 1, (
            f"Expected exactly 1 open session for task {task_id}, "
            f"found {len(unclosed)}"
        )
        return unclosed[0]
    finally:
        check.close()


def _get_task(task_id: str) -> Task:
    check = TestingSession()
    try:
        task = check.query(Task).filter(Task.task_id == task_id).first()
        assert task is not None, f"Task {task_id} not found"
        return task
    finally:
        check.close()


# ---------------------------------------------------------------
# Invariant 1: EXECUTING → Redis active, session open
# ---------------------------------------------------------------

@needs_redis
def test_executing_state_redis_and_session(state_env, client):
    """EXECUTING task must have Redis active key and open session."""
    task_id = _create_and_start(client)

    # Task state = EXECUTING
    task = _get_task(task_id)
    assert task.state == TaskState.EXECUTING

    # Redis: active key present
    active = _assert_redis_active()
    assert active["task_id"] == task_id

    # Session: open (no end_time_utc)
    _assert_session_open(task_id)

    # Status endpoint agrees
    r = client.get("/v1/stopwatch/status", headers=_h())
    assert r.json()["active"] is True
    assert r.json()["task_id"] == task_id


# ---------------------------------------------------------------
# Invariant 2: PAUSED → Redis paused key + active key, session paused_at set
# ---------------------------------------------------------------

@needs_redis
def test_paused_state_redis_and_session(state_env, client):
    """PAUSED task must have Redis active + paused keys, session.paused_at set."""
    task_id = _create_and_start(client)

    r = client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "intentional_break", "pause_initiator": "self"},
        headers=_h(),
    )
    assert r.status_code == 200

    # Task state = PAUSED
    task = _get_task(task_id)
    assert task.state == TaskState.PAUSED

    # Redis: active + paused keys present
    _assert_redis_active()
    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    pause = rc.get_pause_state(str(USER_ID))
    assert pause is not None, "Redis paused key must exist for PAUSED task"

    # Session: paused_at_utc stamped, still open
    session = _assert_session_open(task_id)
    assert session.paused_at_utc is not None


# ---------------------------------------------------------------
# Invariant 3: Normal stop → EXECUTED, Redis clear, session closed
# ---------------------------------------------------------------

@needs_redis
def test_stop_executed_clears_all(state_env, client):
    """Normal stop → task EXECUTED, Redis cleared, session closed with end_time."""
    task_id = _create_and_start(client)

    # Pass task_completion_percentage=80 to bypass the zero-duration guard
    # (active_elapsed == 0 in tests because start→stop is instant).
    r = client.post(
        "/v1/stopwatch/stop",
        json={"post_task_reflection": 4, "task_completion_percentage": 80},
        params={"confirmed": "true"},
        headers=_h(),
    )
    assert r.status_code == 200

    task = _get_task(task_id)
    assert task.state == TaskState.EXECUTED

    _assert_redis_clear()
    _assert_session_closed(task_id)


# ---------------------------------------------------------------
# Invariant 4: mark_abandoned → SKIPPED, Redis clear, session closed
# ---------------------------------------------------------------

@needs_redis
def test_mark_abandoned_executing_clears_all(state_env, client):
    """mark_abandoned on EXECUTING → SKIPPED + Redis cleared + session closed."""
    task_id = _create_and_start(client)

    r = client.post(
        f"/v1/tasks/{task_id}/mark-abandoned",
        json={"reason": "test abandonment"},
        headers=_h(),
    )
    assert r.status_code == 200
    assert r.json()["new_state"] == "SKIPPED"

    task = _get_task(task_id)
    assert task.state == TaskState.SKIPPED

    _assert_redis_clear()
    _assert_session_closed(task_id)


@needs_redis
def test_mark_abandoned_paused_clears_all(state_env, client):
    """mark_abandoned on PAUSED → SKIPPED + Redis active AND paused cleared."""
    task_id = _create_and_start(client)

    client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "distraction", "pause_initiator": "self"},
        headers=_h(),
    )

    r = client.post(
        f"/v1/tasks/{task_id}/mark-abandoned",
        json={"reason": "ghost banner regression"},
        headers=_h(),
    )
    assert r.status_code == 200
    assert r.json()["new_state"] == "SKIPPED"

    _assert_redis_clear()
    _assert_session_closed(task_id)


# ---------------------------------------------------------------
# Invariant 5: void_task → Redis clear, session closed, voided_at stamped
# ---------------------------------------------------------------

@needs_redis
def test_void_paused_clears_all(state_env, client):
    """Void a PAUSED task → voided_at set, Redis cleared, session closed."""
    task_id = _create_and_start(client)

    client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "external_interruption", "pause_initiator": "external"},
        headers=_h(),
    )

    r = client.post(
        f"/v1/tasks/{task_id}/void",
        json={"voided_reason": "test_contamination"},
        headers=_h(),
    )
    assert r.status_code == 200

    task = _get_task(task_id)
    assert task.voided_at is not None

    _assert_redis_clear()
    _assert_session_closed(task_id)


# ---------------------------------------------------------------
# Invariant 6: Self-heal catches SKIPPED task on status poll
# ---------------------------------------------------------------

@needs_redis
def test_self_heal_skipped_task_clears_banner(state_env, client):
    """Simulate stale Redis: task already SKIPPED but Redis keys still live.

    Next /stopwatch/status poll must detect the terminal state and clean up.
    Covers the ghost banner scenario where mark-abandoned ran before the
    Redis cleanup fix shipped.
    """
    task_id = _create_and_start(client)

    # Pause to set both Redis keys.
    client.post(
        "/v1/stopwatch/pause",
        json={"pause_reason": "intentional_break", "pause_initiator": "self"},
        headers=_h(),
    )

    # Force task to SKIPPED directly (bypass mark_abandoned to simulate stale state).
    write = TestingSession()
    try:
        write.execute(
            text("UPDATE task SET state = 'SKIPPED' WHERE task_id = :tid"),
            {"tid": task_id},
        )
        write.commit()
    finally:
        write.close()

    # Redis keys are still live — simulates pre-fix state.
    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    assert rc.get_active_stopwatch(str(USER_ID)) is not None, (
        "Setup error: Redis active key should still exist"
    )

    # Status poll triggers self-heal.
    r = client.get("/v1/stopwatch/status", headers=_h())
    assert r.status_code == 200
    assert r.json().get("active") is not True, (
        "Self-heal failed: status still reports active for SKIPPED task"
    )

    # Redis must be cleaned up as side effect.
    _assert_redis_clear()


# ---------------------------------------------------------------
# Invariant 7: update-completion does NOT stop the timer
# ---------------------------------------------------------------

@needs_redis
def test_update_completion_keeps_timer_running(state_env, client):
    """POST /v1/stopwatch/update-completion sets pct without stopping."""
    task_id = _create_and_start(client)

    r = client.post(
        "/v1/stopwatch/update-completion",
        json={"task_completion_percentage": 75},
        headers=_h(),
    )
    assert r.status_code == 200
    assert r.json()["updated"] is True
    assert r.json()["task_completion_percentage"] == 75

    # Timer must still be active.
    task = _get_task(task_id)
    assert task.state == TaskState.EXECUTING

    _assert_redis_active()
    _assert_session_open(task_id)

    # Status endpoint confirms still running.
    r = client.get("/v1/stopwatch/status", headers=_h())
    assert r.json()["active"] is True

    # The pct must be persisted on the session row.
    check = TestingSession()
    try:
        session = check.query(StopwatchSession).filter(
            StopwatchSession.task_id == task_id,
            StopwatchSession.end_time_utc.is_(None),
        ).first()
        assert session.task_completion_percentage == 75
    finally:
        check.close()


# ---------------------------------------------------------------
# Invariant 8: APScheduler job count
# ---------------------------------------------------------------

def test_apscheduler_job_count():
    """All 13 background jobs must be registered in scheduler.py.

    Count (as of 2026-04-29 — Moodle LMS sync, alembic 041):
      1. reminders
      2. notion_sync
      3. timer_overflow
      4. overdue_tasks
      5. stale_session_recovery
      6. orphan_task_recovery
      7. pause_prediction
      8. reconcile_responses
      9. reconcile_deadline_outcomes  (Loop 11)
     10. sweep_missed_deadlines        (Loop 11)
     11. llm_enrichment                 (magic-for-alpha W1)
     12. resume_prediction              (magic-for-alpha W2)
     13. moodle_ics_sync                (LMS wedge, alembic 041)

    Update this when adding/removing a job — this is the gate.
    """
    import importlib
    import ast

    spec = importlib.util.find_spec("app.workers.scheduler")
    assert spec is not None and spec.origin is not None, "scheduler.py not found"

    with open(spec.origin) as f:
        source = f.read()

    tree = ast.parse(source)
    add_job_calls = sum(
        1 for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(getattr(node, "func", None), ast.Attribute)
        and getattr(node.func, "attr", "") == "add_job"
    )
    assert add_job_calls == 13, (
        f"Expected 13 add_job calls in scheduler.py, found {add_job_calls}. "
        f"A background job may have been added or removed without updating "
        f"the state consistency gate."
    )


# ---------------------------------------------------------------
# Invariant 9: Terminal states block rehydration from DB
# ---------------------------------------------------------------

@needs_redis
def test_recover_from_db_blocks_terminal_states(state_env, client):
    """_recover_from_db must not rehydrate sessions bound to terminal tasks.

    Scenario: Redis empty (restart), session unclosed, task EXECUTED.
    _recover_from_db must skip it — otherwise the banner reappears.
    """
    task_id = _create_and_start(client)

    # Force task to EXECUTED and clear Redis (simulates restart after stop
    # where session wasn't properly closed).
    from app.utils.redis_client import RedisClient
    rc = RedisClient()
    rc.clear_active_stopwatch(str(USER_ID))
    rc.clear_pause_state(str(USER_ID))

    write = TestingSession()
    try:
        write.execute(
            text("UPDATE task SET state = 'EXECUTED' WHERE task_id = :tid"),
            {"tid": task_id},
        )
        write.commit()
    finally:
        write.close()

    # Status poll should NOT rehydrate the unclosed session.
    r = client.get("/v1/stopwatch/status", headers=_h())
    assert r.status_code == 200
    assert r.json().get("active") is not True, (
        "_recover_from_db rehydrated a session for an EXECUTED task"
    )
