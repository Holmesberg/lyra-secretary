"""Narrow task-deadline binding corrections.

Users may discover the right obligation while a task is live, or need to
repair context after execution. This path is metadata-only: it must not
reopen full task editing or mutate execution metrics.
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import Deadline, Task, TaskState, User
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


def _user(db) -> User:
    user = User(
        email=f"u{uuid4().hex[:8]}@test",
        timezone="Africa/Cairo",
        is_operator=True,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _deadline(db, user_id: int, title: str, state: str = "planned") -> Deadline:
    deadline = Deadline(
        deadline_id=str(uuid4()),
        user_id=user_id,
        title=title,
        due_at_utc=datetime.utcnow() + timedelta(days=5),
        state=state,
    )
    db.add(deadline)
    db.commit()
    db.refresh(deadline)
    return deadline


def _task(db, user_id: int, state: TaskState, deadline_id: str | None = None) -> Task:
    now = datetime.utcnow()
    task = Task(
        task_id=str(uuid4()),
        user_id=user_id,
        title="AI Bdaya",
        category="study",
        planned_start_utc=now,
        planned_end_utc=now + timedelta(minutes=90),
        planned_duration_minutes=90,
        executed_start_utc=now if state == TaskState.EXECUTED else None,
        executed_end_utc=now + timedelta(minutes=75) if state == TaskState.EXECUTED else None,
        executed_duration_minutes=75 if state == TaskState.EXECUTED else None,
        state=state,
        source="manual",
        deadline_id=deadline_id,
        deadline_match_source="llm_auto_confirmed" if deadline_id else None,
        deadline_match_confidence=0.7 if deadline_id else None,
        llm_alternative_suggestion={
            "deadline_id": str(uuid4()),
            "title": "AI final",
            "confidence": 0.85,
            "from_source": "llm_auto",
        },
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def test_bind_executing_task_to_deadline_without_full_edit(db, client):
    user = _user(db)
    set_current_user_id(user.user_id)
    deadline = _deadline(db, user.user_id, "AI project discussion")
    task = _task(db, user.user_id, TaskState.EXECUTING)

    response = client.post(
        f"/v1/tasks/{task.task_id}/deadline-binding",
        headers=auth_headers(user.user_id),
        json={"deadline_id": deadline.deadline_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["deadline_id_after"] == deadline.deadline_id
    assert body["deadline_title_after"] == "AI project discussion"
    db.expire_all()
    refreshed = db.query(Task).filter(Task.task_id == task.task_id).first()
    assert refreshed.state == TaskState.EXECUTING
    assert refreshed.deadline_id == deadline.deadline_id
    assert refreshed.deadline_match_source == "user_corrected"
    assert refreshed.deadline_match_confidence == 1.0
    assert refreshed.llm_alternative_suggestion is None
    assert refreshed.executed_duration_minutes is None


def test_rebind_executed_task_is_metadata_only_and_audited(db, client):
    user = _user(db)
    set_current_user_id(user.user_id)
    old_deadline = _deadline(db, user.user_id, "AI final", state="active")
    new_deadline = _deadline(db, user.user_id, "AI project discussion", state="active")
    task = _task(db, user.user_id, TaskState.EXECUTED, old_deadline.deadline_id)

    response = client.post(
        f"/v1/tasks/{task.task_id}/deadline-binding",
        headers=auth_headers(user.user_id),
        json={"deadline_id": new_deadline.deadline_id},
    )

    assert response.status_code == 200
    db.expire_all()
    refreshed = db.query(Task).filter(Task.task_id == task.task_id).first()
    assert refreshed.state == TaskState.EXECUTED
    assert refreshed.deadline_id == new_deadline.deadline_id
    assert refreshed.executed_duration_minutes == 75
    assert refreshed.executed_start_utc == task.executed_start_utc
    assert refreshed.executed_end_utc == task.executed_end_utc
    assert "deadline_binding_correction" in refreshed.notes
    assert old_deadline.deadline_id in refreshed.notes
    assert new_deadline.deadline_id in refreshed.notes


def test_clear_deadline_binding_on_executed_task(db, client):
    user = _user(db)
    set_current_user_id(user.user_id)
    deadline = _deadline(db, user.user_id, "AI project discussion", state="active")
    task = _task(db, user.user_id, TaskState.EXECUTED, deadline.deadline_id)

    response = client.post(
        f"/v1/tasks/{task.task_id}/deadline-binding",
        headers=auth_headers(user.user_id),
        json={"clear_deadline": True},
    )

    assert response.status_code == 200
    db.expire_all()
    refreshed = db.query(Task).filter(Task.task_id == task.task_id).first()
    assert refreshed.deadline_id is None
    assert refreshed.deadline_match_source is None
    assert refreshed.deadline_match_confidence is None
    assert refreshed.executed_duration_minutes == 75


@pytest.mark.parametrize("state", ["completed", "missed", "skipped"])
def test_deadline_binding_correction_rejects_terminal_deadlines(db, client, state):
    user = _user(db)
    set_current_user_id(user.user_id)
    deadline = _deadline(db, user.user_id, "Terminal obligation", state=state)
    task = _task(db, user.user_id, TaskState.EXECUTING)

    response = client.post(
        f"/v1/tasks/{task.task_id}/deadline-binding",
        headers=auth_headers(user.user_id),
        json={"deadline_id": deadline.deadline_id},
    )

    assert response.status_code == 400
    assert "terminal" in response.json()["detail"]
    db.expire_all()
    refreshed = db.query(Task).filter(Task.task_id == task.task_id).first()
    assert refreshed.deadline_id is None
