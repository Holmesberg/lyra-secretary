"""Deadline completion event wiring.

These tests keep overdue completion behavior separate from measured task
execution. Completion events are append-only traces; they are not stopwatch
truth and can validly occur more than once per deadline.
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import (
    Deadline,
    DeadlineCompletionEvent,
    Task,
    TaskDeadlineOutcome,
    TaskSource,
    TaskState,
    User,
)
from app.db.scoping import set_current_user_id
from app.services.deadline_manager import record_deadline_completion_event
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.query(TaskDeadlineOutcome).delete()
    db.query(DeadlineCompletionEvent).delete()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.query(TaskDeadlineOutcome).delete()
    db.query(DeadlineCompletionEvent).delete()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()


def _make_user(db, email: str = "deadline-events@example.com") -> User:
    user = User(
        email=email,
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_deadline(
    db,
    user_id: int,
    *,
    due_at: datetime,
    state: str = "planned",
    external_source: str | None = None,
) -> Deadline:
    deadline = Deadline(
        deadline_id=str(uuid4()),
        user_id=user_id,
        title="Submit research note",
        due_at_utc=due_at,
        state=state,
        external_source=external_source,
    )
    db.add(deadline)
    db.commit()
    db.refresh(deadline)
    return deadline


def test_manual_deadline_done_writes_late_completion_event(db, client):
    user = _make_user(db)
    due_at = datetime.utcnow() - timedelta(hours=2)
    payload = {
        "title": "Submit research note",
        "due_at_utc": due_at.isoformat(),
    }
    created = client.post(
        "/v1/deadlines",
        json=payload,
        headers=auth_headers(user.user_id),
    ).json()

    resp = client.put(
        f"/v1/deadlines/{created['deadline_id']}",
        json={"state": "completed"},
        headers=auth_headers(user.user_id),
    )

    assert resp.status_code == 200, resp.text
    event = db.query(DeadlineCompletionEvent).filter(
        DeadlineCompletionEvent.deadline_id == created["deadline_id"]
    ).one()
    assert event.completion_source == "user_deadline_done"
    assert event.time_provenance == "observed_user_action"
    assert event.completed_after_due is True
    assert event.delay_minutes > 0


def test_multiple_events_count_behaviors_and_distinct_deadlines_separately(db, client):
    user = _make_user(db)
    due_at = datetime(2026, 5, 1, 12, 0, 0)
    deadline = _make_deadline(db, user.user_id, due_at=due_at, state="completed")
    record_deadline_completion_event(
        db,
        deadline,
        completion_source="user_deadline_done",
        completed_at_utc=due_at + timedelta(hours=1),
        recorded_at_utc=due_at + timedelta(hours=1),
        time_provenance="observed_user_action",
    )
    record_deadline_completion_event(
        db,
        deadline,
        completion_source="moodle_submission",
        completed_at_utc=due_at + timedelta(hours=2),
        recorded_at_utc=due_at + timedelta(hours=3),
        time_provenance="external_import",
    )
    db.commit()

    resp = client.get(
        "/v1/analytics/deadline-completions",
        headers=auth_headers(user.user_id),
    )

    assert resp.status_code == 200, resp.text
    summary = resp.json()["summary"]
    assert summary["completion_behavior_count"] == 2
    assert summary["distinct_completed_deadlines"] == 1
    assert summary["late_completion_behavior_count"] == 2
    assert summary["late_distinct_completed_deadlines"] == 1


def test_due_date_drift_does_not_rewrite_historical_delay(db, client):
    user = _make_user(db)
    original_due = datetime(2026, 5, 1, 12, 0, 0)
    deadline = _make_deadline(db, user.user_id, due_at=original_due, state="completed")
    record_deadline_completion_event(
        db,
        deadline,
        completion_source="user_deadline_done",
        completed_at_utc=original_due + timedelta(hours=1),
        recorded_at_utc=original_due + timedelta(hours=1),
        time_provenance="observed_user_action",
    )
    deadline.due_at_utc = original_due + timedelta(days=1)
    db.commit()

    resp = client.get(
        "/v1/analytics/deadline-completions",
        headers=auth_headers(user.user_id),
    )

    assert resp.status_code == 200, resp.text
    row = resp.json()["per_deadline"][0]
    assert row["earliest_delay_minutes"] == 60
    assert row["earliest_completed_after_due"] is True


def test_reopened_deadlines_retain_prior_completion_events(db, client):
    user = _make_user(db)
    deadline = _make_deadline(
        db,
        user.user_id,
        due_at=datetime.utcnow() - timedelta(days=1),
        state="completed",
    )
    record_deadline_completion_event(
        db,
        deadline,
        completion_source="user_deadline_done",
        completed_at_utc=datetime.utcnow(),
        recorded_at_utc=datetime.utcnow(),
        time_provenance="observed_user_action",
    )
    deadline.state = "planned"
    db.commit()

    resp = client.get(
        "/v1/analytics/deadline-completions",
        headers=auth_headers(user.user_id),
    )

    assert resp.status_code == 200, resp.text
    summary = resp.json()["summary"]
    assert summary["completion_behavior_count"] == 1
    assert resp.json()["per_deadline"][0]["state"] == "planned"


def test_retroactive_task_done_records_completion_but_not_deadline_outcome(db, client):
    user = _make_user(db)
    due_at = datetime.utcnow() - timedelta(hours=3)
    deadline = _make_deadline(db, user.user_id, due_at=due_at, state="active")
    task = Task(
        task_id=str(uuid4()),
        title="Bound overdue task",
        planned_start_utc=datetime.utcnow() - timedelta(hours=4),
        planned_end_utc=datetime.utcnow() - timedelta(hours=3),
        planned_duration_minutes=60,
        state=TaskState.PLANNED,
        source=TaskSource.MANUAL,
        user_id=user.user_id,
        deadline_id=deadline.deadline_id,
    )
    db.add(task)
    db.commit()

    resp = client.post(
        f"/v1/tasks/{task.task_id}/mark-done",
        headers=auth_headers(user.user_id),
    )

    assert resp.status_code == 200, resp.text
    event = db.query(DeadlineCompletionEvent).filter(
        DeadlineCompletionEvent.deadline_id == deadline.deadline_id
    ).one()
    assert event.completion_source == "task_retroactive_done"
    assert event.time_provenance == "user_reported_retroactive"
    assert event.task_id == task.task_id
    assert db.query(TaskDeadlineOutcome).count() == 0
