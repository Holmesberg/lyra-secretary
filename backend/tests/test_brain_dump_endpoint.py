"""Brain-dump commit endpoint tests — partial-failure surface (LYR-114).

The endpoint accepts a batch of items + bindings and reports per-item
outcomes. Previously the endpoint logged failures + dropped them
silently from the response, so ~19/61 stress-test items lost their
failure signal. This test set pins down the new failed_items[] surface
so a regression silently dropping items again would fail the suite.
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import Task, TaskState, Deadline, User
from app.db.scoping import set_current_user_id
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()


def _make_user(db) -> User:
    u = User(
        email=f"u{uuid4().hex[:8]}@test",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _commit_payload(items, bindings=None):
    return {"items": items, "bindings": bindings or []}


def test_commit_clean_batch_returns_empty_failed_items(client, db):
    """Happy path: all items valid → failed_items empty."""
    user = _make_user(db)
    future = (datetime.utcnow() + timedelta(hours=6)).isoformat()
    r = client.post(
        "/v1/brain-dump/commit",
        json=_commit_payload([
            {
                "item_id": str(uuid4()),
                "kind": "task",
                "title": "test task A",
                "when_local": future,
                "duration_minutes": 30,
            },
        ]),
        headers=auth_headers(user.user_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tasks_created"] == 1
    assert body["failed_items"] == []


def test_commit_preserves_parse_inferred_category(client, db):
    user = _make_user(db)
    future = (datetime.utcnow() + timedelta(hours=6)).isoformat()
    r = client.post(
        "/v1/brain-dump/commit",
        json=_commit_payload([
            {
                "item_id": str(uuid4()),
                "kind": "task",
                "title": "AI final revision",
                "when_local": future,
                "duration_minutes": 90,
                "category": "study",
                "category_source": "title_heuristic_v1",
                "duration_source": "research_prior_v1",
                "duration_confidence": 0.55,
                "duration_basis": "study exam-prep block prior",
            },
        ]),
        headers=auth_headers(user.user_id),
    )

    assert r.status_code == 200
    body = r.json()
    task = db.query(Task).filter(Task.task_id == body["task_ids"][0]).one()
    assert task.category == "study"
    assert task.planned_duration_minutes == 90


def test_commit_past_time_task_lands_in_failed_items(client, db):
    """LYR-114 core regression: past-time tasks must surface in
    failed_items rather than being silently dropped."""
    user = _make_user(db)
    past = (datetime.utcnow() - timedelta(hours=2)).isoformat()
    item_id = str(uuid4())
    r = client.post(
        "/v1/brain-dump/commit",
        json=_commit_payload([
            {
                "item_id": item_id,
                "kind": "task",
                "title": "should fail past time",
                "when_local": past,
                "duration_minutes": 30,
            },
        ]),
        headers=auth_headers(user.user_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tasks_created"] == 0
    assert len(body["failed_items"]) == 1
    failed = body["failed_items"][0]
    assert failed["item_id"] == item_id
    assert failed["kind"] == "task"
    assert failed["title"] == "should fail past time"
    assert failed["reason"] == "past_time"
    assert failed["retry_hint"] == "schedule_tomorrow_same_time"


def test_commit_mixed_pass_and_fail_partitions_correctly(client, db):
    """Batch with one good + one bad task: response reports
    tasks_created=1 AND failed_items contains exactly the bad item.
    Pre-fix this dropped the bad item silently; tasks_created was
    still 1 but the user had no idea their second task vanished."""
    user = _make_user(db)
    future = (datetime.utcnow() + timedelta(hours=4)).isoformat()
    past = (datetime.utcnow() - timedelta(hours=2)).isoformat()
    good_id = str(uuid4())
    bad_id = str(uuid4())
    r = client.post(
        "/v1/brain-dump/commit",
        json=_commit_payload([
            {
                "item_id": good_id,
                "kind": "task",
                "title": "good task",
                "when_local": future,
                "duration_minutes": 30,
            },
            {
                "item_id": bad_id,
                "kind": "task",
                "title": "bad task past",
                "when_local": past,
                "duration_minutes": 30,
            },
        ]),
        headers=auth_headers(user.user_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tasks_created"] == 1
    assert len(body["task_ids"]) == 1
    assert len(body["failed_items"]) == 1
    failed = body["failed_items"][0]
    assert failed["item_id"] == bad_id
    assert failed["reason"] == "past_time"


def test_commit_deadline_without_when_lands_in_failed_items(client, db):
    """Deadline kind without a parsed when_local is now reported as
    a failure with reason=missing_when (was silently skipped)."""
    user = _make_user(db)
    item_id = str(uuid4())
    r = client.post(
        "/v1/brain-dump/commit",
        json=_commit_payload([
            {
                "item_id": item_id,
                "kind": "deadline",
                "title": "deadline no when",
                "when_local": None,
                "duration_minutes": None,
            },
        ]),
        headers=auth_headers(user.user_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["deadlines_created"] == 0
    assert len(body["failed_items"]) == 1
    assert body["failed_items"][0]["reason"] == "missing_when"
    assert body["failed_items"][0]["retry_hint"] == "edit_when_local"
