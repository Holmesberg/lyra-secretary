"""LYR Path A (Apr 16 2026): conflict-detection severity model tests.

Validates the classified `ConflictResult` from `services/conflict_detector.py`
and the integration through `POST /v1/create`:

  HARD — overlap with EXECUTING. Always rejects, force=true cannot override.
  SOFT — PLANNED/PAUSED overlap, OR same title + same UTC date.
         Force=true accepts.

Per dogfood `Conflict detection too strict for planned tasks` (Apr 15 2026).
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.db.models import Task, TaskState, User
from app.db.scoping import set_current_user_id
from app.services.conflict_detector import ConflictDetector, ConflictResult
from app.utils.time_utils import now_utc
from tests.conftest import TestingSession


USER_ID = 903


@pytest.fixture(autouse=True)
def _clean_env(db):
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
            user_id=USER_ID, email="conflict-severity@test",
            is_operator=False, notion_enabled=False,
            created_at=datetime.utcnow(),
        ))
        seed.commit()
    finally:
        seed.close()
    yield
    set_current_user_id(None)


def _seed_task(
    db, *, title="t", state=TaskState.PLANNED,
    start_offset_min=60, duration_min=30, voided_at=None,
) -> Task:
    start = now_utc() + timedelta(minutes=start_offset_min)
    end = start + timedelta(minutes=duration_min)
    t = Task(
        title=title,
        planned_start_utc=start,
        planned_end_utc=end,
        planned_duration_minutes=duration_min,
        state=state,
        category="dev",
        user_id=USER_ID,
        voided_at=voided_at,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


# ---------------------------------------------------------------------------
# ConflictDetector — direct unit tests
# ---------------------------------------------------------------------------

def test_no_conflicts_returns_empty_result(db):
    detector = ConflictDetector(db)
    start = now_utc() + timedelta(hours=2)
    end = start + timedelta(minutes=30)
    result = detector.detect(start, end, title="Lunch")
    assert isinstance(result, ConflictResult)
    assert result.severity() is None
    assert result.has_hard() is False
    assert result.has_soft() is False
    assert result.all_conflicts() == []


def test_hard_conflict_executing_overlap(db):
    existing = _seed_task(db, title="active work", state=TaskState.EXECUTING,
                          start_offset_min=60, duration_min=60)
    detector = ConflictDetector(db)
    new_start = existing.planned_start_utc + timedelta(minutes=15)
    new_end = new_start + timedelta(minutes=20)
    result = detector.detect(new_start, new_end)
    assert result.severity() == "hard"
    assert result.has_hard() is True
    assert existing.task_id in {t.task_id for t in result.hard}
    assert result.soft_reasons() == []


def test_soft_conflict_planned_overlap(db):
    existing = _seed_task(db, title="planned A", state=TaskState.PLANNED,
                          start_offset_min=60, duration_min=60)
    detector = ConflictDetector(db)
    new_start = existing.planned_start_utc + timedelta(minutes=15)
    new_end = new_start + timedelta(minutes=20)
    result = detector.detect(new_start, new_end)
    assert result.severity() == "soft"
    assert result.has_hard() is False
    assert existing.task_id in {t.task_id for t in result.soft_overlap}
    assert "overlap" in result.soft_reasons()


def test_soft_conflict_paused_overlap_preserves_pause_state(db):
    """PAUSED overlap stays SOFT — frontend's PAUSED interruption flow
    still inspects c.state to specialize before falling back to severity."""
    existing = _seed_task(db, title="paused parent", state=TaskState.PAUSED,
                          start_offset_min=60, duration_min=60)
    detector = ConflictDetector(db)
    new_start = existing.planned_start_utc + timedelta(minutes=10)
    new_end = new_start + timedelta(minutes=20)
    result = detector.detect(new_start, new_end)
    assert result.severity() == "soft"
    assert existing.task_id in {t.task_id for t in result.soft_overlap}


def test_soft_conflict_duplicate_title_same_utc_day(db):
    # Existing 'Lunch' at +2h
    _seed_task(db, title="Lunch", state=TaskState.PLANNED, start_offset_min=120)
    detector = ConflictDetector(db)
    # New 'Lunch' at +6h — same UTC day, no overlap
    new_start = now_utc() + timedelta(hours=6)
    new_end = new_start + timedelta(minutes=30)
    result = detector.detect(new_start, new_end, title="Lunch")
    assert result.severity() == "soft"
    assert result.has_hard() is False
    assert "duplicate_title" in result.soft_reasons()
    assert len(result.soft_duplicate) == 1


def test_duplicate_title_case_insensitive(db):
    _seed_task(db, title="Lunch", state=TaskState.PLANNED, start_offset_min=120)
    detector = ConflictDetector(db)
    new_start = now_utc() + timedelta(hours=6)
    new_end = new_start + timedelta(minutes=30)
    result = detector.detect(new_start, new_end, title="LUNCH")
    assert "duplicate_title" in result.soft_reasons()


def test_duplicate_title_different_utc_day_no_conflict(db):
    # Existing 'Lunch' today
    _seed_task(db, title="Lunch", state=TaskState.PLANNED, start_offset_min=120)
    detector = ConflictDetector(db)
    # New 'Lunch' 2 days later
    new_start = now_utc() + timedelta(days=2)
    new_end = new_start + timedelta(minutes=30)
    result = detector.detect(new_start, new_end, title="Lunch")
    assert result.severity() is None
    assert result.soft_duplicate == []


def test_duplicate_title_skipped_executed_still_match(db):
    """Already-finished or skipped tasks count for duplicate-title — useful
    for "you already had Lunch today" warning."""
    _seed_task(db, title="Lunch", state=TaskState.EXECUTED, start_offset_min=-120)
    _seed_task(db, title="Lunch", state=TaskState.SKIPPED, start_offset_min=-60)
    detector = ConflictDetector(db)
    new_start = now_utc() + timedelta(hours=4)
    new_end = new_start + timedelta(minutes=30)
    result = detector.detect(new_start, new_end, title="Lunch")
    assert result.severity() == "soft"
    assert len(result.soft_duplicate) == 2


def test_duplicate_title_voided_excluded(db):
    _seed_task(db, title="Lunch", state=TaskState.PLANNED,
               start_offset_min=120, voided_at=now_utc())
    detector = ConflictDetector(db)
    new_start = now_utc() + timedelta(hours=6)
    new_end = new_start + timedelta(minutes=30)
    result = detector.detect(new_start, new_end, title="Lunch")
    assert result.severity() is None


def test_duplicate_title_deleted_excluded(db):
    _seed_task(db, title="Lunch", state=TaskState.DELETED, start_offset_min=120)
    detector = ConflictDetector(db)
    new_start = now_utc() + timedelta(hours=6)
    new_end = new_start + timedelta(minutes=30)
    result = detector.detect(new_start, new_end, title="Lunch")
    assert result.severity() is None


def test_mixed_hard_and_soft_hard_wins(db):
    # Existing EXECUTING task at +1h
    executing = _seed_task(db, title="active", state=TaskState.EXECUTING,
                           start_offset_min=60, duration_min=60)
    # Existing PLANNED with same title at +5h (would soft-trigger duplicate)
    planned = _seed_task(db, title="ambiguous", state=TaskState.PLANNED,
                         start_offset_min=300, duration_min=30)
    detector = ConflictDetector(db)
    new_start = executing.planned_start_utc + timedelta(minutes=10)
    new_end = new_start + timedelta(minutes=15)
    # Same title as planned + overlapping with executing
    result = detector.detect(new_start, new_end, title="ambiguous")
    assert result.severity() == "hard"
    assert result.has_hard() is True
    # Soft buckets may also have entries — that's fine, severity gates.
    assert len(result.hard) == 1


def test_voided_overlap_excluded(db):
    _seed_task(db, title="voided", state=TaskState.EXECUTING,
               start_offset_min=60, voided_at=now_utc())
    detector = ConflictDetector(db)
    new_start = now_utc() + timedelta(minutes=70)
    new_end = new_start + timedelta(minutes=15)
    result = detector.detect(new_start, new_end)
    assert result.severity() is None


def test_executed_overlap_excluded(db):
    """EXECUTED tasks no longer reserve calendar time — overlap allowed."""
    _seed_task(db, title="done", state=TaskState.EXECUTED, start_offset_min=60)
    detector = ConflictDetector(db)
    new_start = now_utc() + timedelta(minutes=70)
    new_end = new_start + timedelta(minutes=15)
    result = detector.detect(new_start, new_end)
    assert result.severity() is None


def test_exclude_task_id_used_by_reschedule_path(db):
    """Rescheduling a task into its own original slot must not self-conflict."""
    t = _seed_task(db, title="self", state=TaskState.PLANNED, start_offset_min=60)
    detector = ConflictDetector(db)
    result = detector.detect(
        t.planned_start_utc, t.planned_end_utc,
        exclude_task_id=t.task_id, title=t.title,
    )
    assert result.severity() is None


# ---------------------------------------------------------------------------
# Endpoint integration — /v1/create severity wire shape
# ---------------------------------------------------------------------------

def _h() -> dict:
    return {"X-User-Id": str(USER_ID)}


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat() + "Z"


def test_endpoint_no_conflict_returns_severity_null(client):
    start = now_utc() + timedelta(hours=2)
    end = start + timedelta(minutes=30)
    r = client.post("/v1/create", json={
        "title": "fresh", "start": _iso(start), "end": _iso(end),
    }, headers=_h())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] is True
    assert body["severity"] is None
    assert body["soft_reasons"] == []
    assert body["can_proceed"] is True


def test_endpoint_soft_planned_overlap_returns_can_proceed(client, db):
    _seed_task(db, title="planned A", state=TaskState.PLANNED,
               start_offset_min=120, duration_min=60)
    new_start = now_utc() + timedelta(hours=2, minutes=15)
    new_end = new_start + timedelta(minutes=20)
    r = client.post("/v1/create", json={
        "title": "overlap B", "start": _iso(new_start), "end": _iso(new_end),
    }, headers=_h())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] is False
    assert body["severity"] == "soft"
    assert body["can_proceed"] is True
    assert "overlap" in body["soft_reasons"]
    assert all(c["gate_id"] == "planned_overlap" for c in body["conflicts"])


def test_endpoint_soft_force_true_creates(client, db):
    _seed_task(db, title="planned A", state=TaskState.PLANNED,
               start_offset_min=120, duration_min=60)
    new_start = now_utc() + timedelta(hours=2, minutes=15)
    new_end = new_start + timedelta(minutes=20)
    r = client.post("/v1/create", json={
        "title": "overlap B", "start": _iso(new_start), "end": _iso(new_end),
        "force": True,
    }, headers=_h())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] is True
    assert body["severity"] is None


def test_endpoint_hard_executing_blocks_with_can_proceed_false(client, db):
    _seed_task(db, title="active", state=TaskState.EXECUTING,
               start_offset_min=120, duration_min=60)
    new_start = now_utc() + timedelta(hours=2, minutes=15)
    new_end = new_start + timedelta(minutes=20)
    r = client.post("/v1/create", json={
        "title": "would-collide", "start": _iso(new_start), "end": _iso(new_end),
    }, headers=_h())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] is False
    assert body["severity"] == "hard"
    assert body["can_proceed"] is False
    assert all(c["gate_id"] == "active_overlap" for c in body["conflicts"])


def test_endpoint_hard_force_true_still_blocked(client, db):
    """force=true cannot override single-mutation-authority."""
    _seed_task(db, title="active", state=TaskState.EXECUTING,
               start_offset_min=120, duration_min=60)
    new_start = now_utc() + timedelta(hours=2, minutes=15)
    new_end = new_start + timedelta(minutes=20)
    r = client.post("/v1/create", json={
        "title": "force-attempt", "start": _iso(new_start), "end": _iso(new_end),
        "force": True,
    }, headers=_h())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] is False
    assert body["severity"] == "hard"
    assert body["can_proceed"] is False


def test_endpoint_duplicate_title_soft(client, db):
    _seed_task(db, title="Lunch", state=TaskState.PLANNED, start_offset_min=120)
    new_start = now_utc() + timedelta(hours=6)
    new_end = new_start + timedelta(minutes=30)
    r = client.post("/v1/create", json={
        "title": "Lunch", "start": _iso(new_start), "end": _iso(new_end),
    }, headers=_h())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] is False
    assert body["severity"] == "soft"
    assert "duplicate_title" in body["soft_reasons"]
