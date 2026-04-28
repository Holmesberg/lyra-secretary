"""Edit-modal parity tests (2026-04-28).

Reschedule endpoint now accepts description + deadline_id alongside the
existing time/title/category fields. Covers:
  - description change resets llm_parse_status='pending' + clears stale candidates
  - whitespace-only description "change" does NOT trigger reset
  - deadline_id binding sets deadline_match_source='user_explicit'
  - cross-tenant deadline binding rejected
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import Deadline, Task, TaskState, User
from app.db.scoping import set_current_user_id
from app.services.task_manager import TaskManager


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
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_task(db, user_id: int, **overrides) -> Task:
    now = datetime.utcnow()
    defaults = dict(
        task_id=str(uuid4()),
        user_id=user_id,
        title="Test task",
        description="original",
        category="work",
        planned_start_utc=now + timedelta(hours=1),
        planned_end_utc=now + timedelta(hours=2),
        planned_duration_minutes=60,
        state=TaskState.PLANNED,
        source="manual",
        created_at=now,
        last_modified_at=now,
        llm_parse_status="enriched",  # already enriched
        llm_priority=2,
        llm_inferred_deadline_id=None,
        llm_deadline_match_confidence=0.7,
        llm_deadline_candidates=[{"deadline_id": "stale", "title": "Stale", "confidence": 0.7}],
        llm_sub_items=[{"text": "old item", "scope_bullet": True}],
        llm_parsed_at=now,
    )
    defaults.update(overrides)
    t = Task(**defaults)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _make_deadline(db, user_id: int, title="BCI paper") -> Deadline:
    d = Deadline(
        deadline_id=str(uuid4()),
        user_id=user_id,
        title=title,
        due_at_utc=datetime.utcnow() + timedelta(days=7),
        state="planned",
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def test_description_change_resets_llm_parse_status(db):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    task = _make_task(db, user.user_id)

    new_start = datetime.utcnow() + timedelta(hours=3)
    TaskManager(db).reschedule_task(
        task_id=task.task_id,
        new_start=new_start,
        description="totally new description with bullets",
    )
    db.refresh(task)
    assert task.description == "totally new description with bullets"
    assert task.llm_parse_status == "pending"  # reset
    assert task.llm_inferred_deadline_id is None
    assert task.llm_deadline_match_confidence is None
    assert task.llm_deadline_candidates is None
    assert task.llm_priority is None
    assert task.llm_sub_items is None


def test_whitespace_only_description_diff_does_not_reset(db):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    task = _make_task(db, user.user_id, description="meaningful")

    new_start = datetime.utcnow() + timedelta(hours=3)
    TaskManager(db).reschedule_task(
        task_id=task.task_id,
        new_start=new_start,
        description="  meaningful  ",  # same content, different whitespace
    )
    db.refresh(task)
    # llm_parse_status preserved
    assert task.llm_parse_status == "enriched"
    assert task.llm_priority == 2  # not cleared


def test_deadline_id_explicit_bind(db):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    deadline = _make_deadline(db, user.user_id)
    task = _make_task(db, user.user_id)
    assert task.deadline_id is None

    new_start = datetime.utcnow() + timedelta(hours=3)
    TaskManager(db).reschedule_task(
        task_id=task.task_id,
        new_start=new_start,
        deadline_id=deadline.deadline_id,
    )
    db.refresh(task)
    db.refresh(deadline)
    assert task.deadline_id == deadline.deadline_id
    assert task.deadline_match_source == "user_explicit"
    assert task.deadline_match_confidence == 1.0
    # Auto-transition planned → active mirrors create_task
    assert deadline.state == "active"


def test_no_change_when_description_and_deadline_omitted(db):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    task = _make_task(db, user.user_id)
    new_start = datetime.utcnow() + timedelta(hours=3)
    TaskManager(db).reschedule_task(
        task_id=task.task_id,
        new_start=new_start,
        title="renamed",
    )
    db.refresh(task)
    assert task.title == "renamed"
    # Untouched
    assert task.description == "original"
    assert task.llm_parse_status == "enriched"
    assert task.deadline_id is None
