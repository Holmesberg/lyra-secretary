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
from app.utils.time_utils import to_utc
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


def test_commit_duplicate_deadline_reuses_existing_for_bindings(client, db):
    """Brain dump should not inflate pressure by creating same-day duplicate
    deadlines. If a confirmed task binding targets that parsed duplicate, it
    should resolve to the existing deadline instead.
    """
    user = _make_user(db)
    when_local = (datetime.utcnow() + timedelta(days=10)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    due_at_utc = to_utc(when_local)
    existing = Deadline(
        deadline_id=str(uuid4()),
        user_id=user.user_id,
        title="AI final",
        due_at_utc=due_at_utc,
        state="active",
        created_at=datetime.utcnow(),
    )
    db.add(existing)
    db.commit()

    deadline_item_id = str(uuid4())
    task_item_id = str(uuid4())
    r = client.post(
        "/v1/brain-dump/commit",
        json=_commit_payload(
            [
                {
                    "item_id": deadline_item_id,
                    "kind": "deadline",
                    "title": "ai FINAL",
                    "when_local": when_local.isoformat(),
                    "duration_minutes": None,
                },
                {
                    "item_id": task_item_id,
                    "kind": "task",
                    "title": "AI final review",
                    "when_local": (datetime.utcnow() + timedelta(hours=6)).isoformat(),
                    "duration_minutes": 30,
                },
            ],
            bindings=[
                {
                    "task_item_id": task_item_id,
                    "deadline_item_id": deadline_item_id,
                }
            ],
        ),
        headers=auth_headers(user.user_id),
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deadlines_created"] == 0
    assert body["tasks_created"] == 1
    assert body["bindings_applied"] == 1
    assert body["failed_items"][0]["reason"] == "duplicate_deadline"
    assert db.query(Deadline).filter(Deadline.user_id == user.user_id).count() == 1
    task = db.query(Task).filter(Task.task_id == body["task_ids"][0]).one()
    assert task.deadline_id == existing.deadline_id


def test_parse_suggests_existing_bindable_deadline(client, db):
    """Wave 1: Pulse preview should see existing obligations before commit.

    This protects the pressure map by letting new brain-dump tasks bind to
    already-created deadlines instead of relying on duplicate deadline creation.
    """
    user = _make_user(db)
    due_local = (datetime.utcnow() + timedelta(days=14)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    existing = Deadline(
        deadline_id=str(uuid4()),
        user_id=user.user_id,
        title="CO final",
        due_at_utc=to_utc(due_local),
        state="active",
        created_at=datetime.utcnow(),
    )
    db.add(existing)
    db.commit()

    r = client.post(
        "/v1/brain-dump/parse",
        json={
            "raw_text": "CO lec 1 tomorrow",
            "current_local_iso": datetime.utcnow().isoformat(),
        },
        headers=auth_headers(user.user_id),
    )

    assert r.status_code == 200, r.text
    body = r.json()
    existing_bindings = [
        b for b in body["bindings"]
        if b["target_kind"] == "existing_deadline"
    ]
    assert len(existing_bindings) == 1
    assert existing_bindings[0]["deadline_id"] == existing.deadline_id
    assert existing_bindings[0]["deadline_title"] == "CO final"


def test_parse_ranks_specific_existing_obligation_above_broad_same_dump_deadline(
    client,
    db,
):
    """Wave 1 regression: same-dump deadlines must not mask better existing
    obligations.

    User case: after adding "AI final" in the same dump, "read notes for AI
    discussion" was linked to AI final instead of the existing AI project
    discussion obligation.
    """
    user = _make_user(db)
    existing = Deadline(
        deadline_id=str(uuid4()),
        user_id=user.user_id,
        title="AI project discussion",
        due_at_utc=to_utc(datetime.utcnow() + timedelta(days=5)),
        state="active",
        created_at=datetime.utcnow(),
    )
    db.add(existing)
    db.commit()

    r = client.post(
        "/v1/brain-dump/parse",
        json={
            "raw_text": (
                "read notes for AI discussion tomorrow\n"
                "AI final next Thursday 9am\n"
                "AI final revision tomorrow"
            ),
            "current_local_iso": datetime.utcnow().isoformat(),
        },
        headers=auth_headers(user.user_id),
    )

    assert r.status_code == 200, r.text
    body = r.json()
    read_task = next(
        item for item in body["items"]
        if item["title"] == "read notes for AI discussion"
    )
    read_bindings = [
        binding for binding in body["bindings"]
        if binding["task_item_id"] == read_task["item_id"]
    ]

    assert len(read_bindings) >= 2
    assert read_bindings[0]["target_kind"] == "existing_deadline"
    assert read_bindings[0]["deadline_id"] == existing.deadline_id
    assert read_bindings[0]["deadline_title"] == "AI project discussion"
    assert read_bindings[0]["confidence"] > read_bindings[1]["confidence"]


def test_commit_can_bind_task_to_existing_deadline(client, db):
    """Wave 1 commit path: explicit existing-deadline binding is canonical."""
    user = _make_user(db)
    due_local = (datetime.utcnow() + timedelta(days=10)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    existing = Deadline(
        deadline_id=str(uuid4()),
        user_id=user.user_id,
        title="CO final",
        due_at_utc=to_utc(due_local),
        state="planned",
        created_at=datetime.utcnow(),
    )
    db.add(existing)
    db.commit()

    task_item_id = str(uuid4())
    r = client.post(
        "/v1/brain-dump/commit",
        json=_commit_payload(
            [
                {
                    "item_id": task_item_id,
                    "kind": "task",
                    "title": "CO lec 1",
                    "when_local": (
                        datetime.utcnow() + timedelta(hours=6)
                    ).isoformat(),
                    "duration_minutes": 90,
                },
            ],
            bindings=[
                {
                    "task_item_id": task_item_id,
                    "target_kind": "existing_deadline",
                    "deadline_id": existing.deadline_id,
                }
            ],
        ),
        headers=auth_headers(user.user_id),
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deadlines_created"] == 0
    assert body["tasks_created"] == 1
    assert body["bindings_applied"] == 1

    task = db.query(Task).filter(Task.task_id == body["task_ids"][0]).one()
    assert task.deadline_id == existing.deadline_id
    db.refresh(existing)
    assert existing.state == "active"
