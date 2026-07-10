from datetime import datetime, timedelta
from uuid import uuid4

from app.db.models import Task, User
from app.services.task_manager import TaskManager
from tests.conftest import auth_headers


def _make_user(db) -> User:
    user = User(
        email=f"category-{uuid4().hex[:8]}@test",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_academic_schedule_terms_infer_academic_without_manual_category(db):
    manager = TaskManager(db)

    assert manager._infer_category("CO MARS labs") == "academic"
    assert manager._infer_category("Operating Systems tutorial") == "academic"
    assert manager._infer_category("AI lecture 5") == "academic"


def test_self_study_terms_infer_study_without_manual_category(db):
    manager = TaskManager(db)

    assert manager._infer_category("AI final revision") == "study"
    assert manager._infer_category("read CO slides") == "study"
    assert manager._infer_category("solve algorithms problem set") == "study"


def test_create_endpoint_infers_academic_category_without_manual_category(client, db):
    user = _make_user(db)
    start = datetime.utcnow() + timedelta(hours=8)
    end = start + timedelta(minutes=90)

    response = client.post(
        "/v1/create",
        json={
            "title": "lec 2 AI",
            "start": start.replace(microsecond=0).isoformat() + "Z",
            "end": end.replace(microsecond=0).isoformat() + "Z",
        },
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] is True
    task = db.query(Task).filter(Task.task_id == body["task_id"]).one()
    assert task.user_id == user.user_id
    assert task.category == "academic"
