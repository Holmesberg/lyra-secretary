"""POST /v1/tasks/{id}/reject-llm-binding — bug fix 2026-05-01.

Operator: "I clicked no deadline, still binded." Prior endpoint only
set llm_binding_rejected_at and left task.deadline_id intact, so
heuristic-auto bindings persisted after explicit user rejection.

Behavior under fix:
  - System-auto sources (heuristic_*, llm_auto_confirmed, parser_auto)
    → clear deadline_id + reset deadline_match_source on reject
  - Alternative-suggestion "Keep current" rejects only the alternative,
    preserving the current canonical deadline even when its source is
    system-auto
  - User-owned sources (user_explicit, manual_user) → preserve
    deadline_id; rejection only stops the chip from re-rendering
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


def _make_user(db) -> User:
    u = User(
        email=f"u{uuid4().hex[:8]}@test",
        timezone="Africa/Cairo",
        is_operator=True,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_deadline(db, user_id: int) -> Deadline:
    d = Deadline(
        deadline_id=str(uuid4()),
        user_id=user_id,
        title="CSE221 Major Task Phase II",
        due_at_utc=datetime.utcnow() + timedelta(days=7),
        state="planned",
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def _make_named_deadline(db, user_id: int, title: str) -> Deadline:
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


def _make_task(db, user_id: int, *, deadline_id: str, source: str | None) -> Task:
    now = datetime.utcnow()
    t = Task(
        task_id=str(uuid4()),
        user_id=user_id,
        title="Build CSE221 phase II",
        category="study",
        planned_start_utc=now,
        planned_end_utc=now + timedelta(minutes=60),
        planned_duration_minutes=60,
        state=TaskState.PLANNED,
        source="manual",
        deadline_id=deadline_id,
        deadline_match_source=source,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def test_reject_clears_deadline_for_heuristic_auto_source(db, client):
    """Operator's case: heuristic auto-bound the task → user clicks
    'Not relevant' → deadline must be cleared, not just chip hidden."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    deadline = _make_deadline(db, user.user_id)
    task = _make_task(
        db, user.user_id,
        deadline_id=deadline.deadline_id,
        source="heuristic_substring",
    )

    r = client.post(
        f"/v1/tasks/{task.task_id}/reject-llm-binding",
        headers=auth_headers(user.user_id),
    )
    assert r.status_code == 200
    db.expire(task)
    refreshed = db.query(Task).filter(Task.task_id == task.task_id).first()
    assert refreshed.deadline_id is None
    assert refreshed.deadline_match_source is None
    assert refreshed.llm_binding_rejected_at is not None


def test_reject_clears_deadline_for_confirmed_heuristic_source(db, client):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    deadline = _make_deadline(db, user.user_id)
    task = _make_task(
        db, user.user_id,
        deadline_id=deadline.deadline_id,
        source="heuristic_confirmed",
    )

    r = client.post(
        f"/v1/tasks/{task.task_id}/reject-llm-binding",
        headers=auth_headers(user.user_id),
    )
    assert r.status_code == 200
    db.expire_all()
    refreshed = db.query(Task).filter(Task.task_id == task.task_id).first()
    assert refreshed.deadline_id is None
    assert refreshed.deadline_match_source is None
    assert refreshed.deadline_match_confidence is None


def test_reject_refuses_historical_model_alternative_without_mutation(db, client):
    """Historical model output is retained for audit, not current action."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    current = _make_named_deadline(db, user.user_id, "AI project discussion")
    alternative = _make_named_deadline(db, user.user_id, "AI final")
    task = _make_task(
        db,
        user.user_id,
        deadline_id=current.deadline_id,
        source="llm_auto_confirmed",
    )
    task.deadline_match_confidence = 0.7
    task.llm_parse_status = "enriched"
    task.llm_alternative_suggestion = {
        "deadline_id": alternative.deadline_id,
        "title": alternative.title,
        "confidence": 0.85,
        "from_source": "llm_auto",
    }
    db.commit()

    r = client.post(
        f"/v1/tasks/{task.task_id}/reject-llm-binding",
        headers=auth_headers(user.user_id),
    )

    assert r.status_code == 409
    db.expire_all()
    refreshed = db.query(Task).filter(Task.task_id == task.task_id).first()
    assert refreshed.deadline_id == current.deadline_id
    assert refreshed.deadline_match_source == "llm_auto_confirmed"
    assert refreshed.deadline_match_confidence == 0.7
    assert refreshed.llm_alternative_suggestion is not None
    assert refreshed.llm_binding_rejected_at is None


def test_reject_preserves_deadline_for_user_explicit_source(db, client):
    """User picked the deadline manually — rejection must only stop the
    LLM chip, not undo the user's choice."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    deadline = _make_deadline(db, user.user_id)
    task = _make_task(
        db, user.user_id,
        deadline_id=deadline.deadline_id,
        source="user_explicit",
    )

    r = client.post(
        f"/v1/tasks/{task.task_id}/reject-llm-binding",
        headers=auth_headers(user.user_id),
    )
    assert r.status_code == 200
    db.expire_all()
    refreshed = db.query(Task).filter(Task.task_id == task.task_id).first()
    assert refreshed.deadline_id == deadline.deadline_id
    assert refreshed.deadline_match_source == "user_explicit"
    assert refreshed.llm_binding_rejected_at is not None


def test_reject_preserves_deadline_for_manual_user_source(db, client):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    deadline = _make_deadline(db, user.user_id)
    task = _make_task(
        db, user.user_id,
        deadline_id=deadline.deadline_id,
        source="manual_user",
    )

    r = client.post(
        f"/v1/tasks/{task.task_id}/reject-llm-binding",
        headers=auth_headers(user.user_id),
    )
    assert r.status_code == 200
    db.expire_all()
    refreshed = db.query(Task).filter(Task.task_id == task.task_id).first()
    assert refreshed.deadline_id == deadline.deadline_id
    assert refreshed.deadline_match_source == "manual_user"


def test_reject_on_unbound_task_is_idempotent(db, client):
    """Rejecting on a task that has no binding still records the
    rejection flag — defensive idempotency."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    task = _make_task(db, user.user_id, deadline_id=None, source=None)

    r = client.post(
        f"/v1/tasks/{task.task_id}/reject-llm-binding",
        headers=auth_headers(user.user_id),
    )
    assert r.status_code == 200
    db.expire_all()
    refreshed = db.query(Task).filter(Task.task_id == task.task_id).first()
    assert refreshed.deadline_id is None
    assert refreshed.llm_binding_rejected_at is not None


def test_confirm_accepts_only_current_deterministic_candidate(db, client):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    deadline = _make_deadline(db, user.user_id)
    task = _make_task(db, user.user_id, deadline_id=None, source=None)
    task.llm_parse_status = "retired"
    task.llm_inferred_deadline_id = deadline.deadline_id
    task.llm_deadline_candidates = [
        {
            "deadline_id": deadline.deadline_id,
            "title": deadline.title,
            "confidence": 0.9,
            "source": "heuristic_exact_title",
        }
    ]
    db.commit()

    response = client.post(
        f"/v1/tasks/{task.task_id}/llm-confirm",
        json={"accepted_fields": ["deadline"]},
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200
    db.expire_all()
    refreshed = db.query(Task).filter(Task.task_id == task.task_id).one()
    assert refreshed.deadline_id == deadline.deadline_id
    assert refreshed.deadline_match_source == "heuristic_confirmed"


def test_confirm_rejects_historical_model_candidate(db, client):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    deadline = _make_deadline(db, user.user_id)
    task = _make_task(db, user.user_id, deadline_id=None, source=None)
    task.llm_parse_status = "enriched"
    task.llm_inferred_deadline_id = deadline.deadline_id
    task.llm_deadline_candidates = [
        {
            "deadline_id": deadline.deadline_id,
            "title": deadline.title,
            "confidence": 0.9,
        }
    ]
    db.commit()

    response = client.post(
        f"/v1/tasks/{task.task_id}/llm-confirm",
        json={"accepted_fields": ["deadline"]},
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 409
    db.expire_all()
    refreshed = db.query(Task).filter(Task.task_id == task.task_id).one()
    assert refreshed.deadline_id is None


def test_confirm_does_not_reveal_another_users_candidate(db, client):
    owner = _make_user(db)
    caller = _make_user(db)
    deadline = _make_deadline(db, owner.user_id)
    task = _make_task(db, owner.user_id, deadline_id=None, source=None)
    task.llm_parse_status = "retired"
    task.llm_inferred_deadline_id = deadline.deadline_id
    task.llm_deadline_candidates = [
        {
            "deadline_id": deadline.deadline_id,
            "title": deadline.title,
            "confidence": 0.9,
            "source": "heuristic_exact_title",
        }
    ]
    db.commit()

    response = client.post(
        f"/v1/tasks/{task.task_id}/llm-confirm",
        json={"accepted_fields": ["deadline"]},
        headers=auth_headers(caller.user_id),
    )

    assert response.status_code == 404


def test_reject_preserves_deterministic_candidate_evidence(db, client):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    deadline = _make_deadline(db, user.user_id)
    task = _make_task(db, user.user_id, deadline_id=None, source=None)
    task.llm_parse_status = "retired"
    task.llm_inferred_deadline_id = deadline.deadline_id
    task.llm_deadline_match_confidence = 0.9
    task.llm_deadline_candidates = [
        {
            "deadline_id": deadline.deadline_id,
            "title": deadline.title,
            "confidence": 0.9,
            "source": "heuristic_exact_title",
        }
    ]
    db.commit()

    response = client.post(
        f"/v1/tasks/{task.task_id}/reject-llm-binding",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200
    db.expire_all()
    refreshed = db.query(Task).filter(Task.task_id == task.task_id).one()
    assert refreshed.llm_binding_rejected_at is not None
    assert refreshed.llm_inferred_deadline_id == deadline.deadline_id
    assert refreshed.llm_deadline_match_confidence == 0.9
    assert refreshed.llm_deadline_candidates[0]["source"] == "heuristic_exact_title"


def test_reject_does_not_reveal_another_users_candidate(db, client):
    owner = _make_user(db)
    caller = _make_user(db)
    task = _make_task(db, owner.user_id, deadline_id=None, source=None)

    response = client.post(
        f"/v1/tasks/{task.task_id}/reject-llm-binding",
        headers=auth_headers(caller.user_id),
    )

    assert response.status_code == 404
