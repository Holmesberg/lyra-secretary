from datetime import datetime, timedelta

from app.db.models import StopwatchSession, Task, TaskState, User
from app.db.scoping import get_current_user_id, set_current_user_id
from tests.conftest import auth_headers


def _clear_ids(db, ids: list[int]) -> None:
    original_uid = get_current_user_id()
    set_current_user_id(None)
    try:
        db.query(StopwatchSession).filter(StopwatchSession.user_id.in_(ids)).delete()
        db.query(Task).filter(Task.user_id.in_(ids)).delete()
        db.query(User).filter(User.user_id.in_(ids)).delete()
        db.commit()
    finally:
        set_current_user_id(original_uid)


def _user(user_id: int, *, operator: bool = False) -> User:
    return User(
        user_id=user_id,
        email=f"user-{user_id}@example.test",
        google_id=f"google-{user_id}",
        is_operator=operator,
        timezone="Africa/Cairo",
        created_at=datetime.utcnow() - timedelta(days=10),
        terms_accepted_at=datetime.utcnow() - timedelta(days=10),
    )


def _task(user_id: int, task_id: str, *, state: TaskState = TaskState.PLANNED) -> Task:
    start = datetime.utcnow() - timedelta(hours=2)
    end = start + timedelta(minutes=60)
    return Task(
        task_id=task_id,
        user_id=user_id,
        title=f"Task {task_id}",
        category="study",
        planned_start_utc=start,
        planned_end_utc=end,
        planned_duration_minutes=60,
        state=state,
        source="manual",
        created_at=start,
        last_modified_at=end,
    )


def test_operator_dashboard_requires_operator(client, db):
    ids = [9101, 9102]
    _clear_ids(db, ids)
    db.add(_user(9101, operator=True))
    db.add(_user(9102, operator=False))
    db.commit()

    forbidden = client.get("/v1/operator/dashboard", headers=auth_headers(9102))
    assert forbidden.status_code == 403

    allowed = client.get("/v1/operator/dashboard", headers=auth_headers(9101))
    assert allowed.status_code == 200
    assert "cohort_readiness" in allowed.json()


def test_operator_dashboard_reports_state_and_privacy_boundaries(client, db):
    ids = [9111, 9112]
    _clear_ids(db, ids)
    db.add(_user(9111, operator=True))
    user = _user(9112, operator=False)
    user.first_task_at = datetime.utcnow() - timedelta(days=9)
    user.first_timer_started_at = datetime.utcnow() - timedelta(days=9)
    db.add(user)

    clean_task = _task(9112, "clean-task", state=TaskState.EXECUTED)
    clean_task.executed_start_utc = clean_task.planned_start_utc
    clean_task.executed_end_utc = clean_task.planned_start_utc + timedelta(minutes=55)
    clean_task.executed_duration_minutes = 55
    db.add(clean_task)
    db.add(
        StopwatchSession(
            session_id="clean-session",
            task_id="clean-task",
            user_id=9112,
            start_time_utc=clean_task.executed_start_utc,
            end_time_utc=clean_task.executed_end_utc,
            total_paused_minutes=0.0,
            auto_closed=False,
        )
    )

    bad_task = _task(9112, "bad-task", state=TaskState.EXECUTED)
    bad_task.executed_start_utc = datetime.utcnow() - timedelta(hours=1)
    bad_task.executed_end_utc = None
    bad_task.executed_duration_minutes = None
    db.add(bad_task)

    executing_task = _task(9112, "dup-open-task", state=TaskState.EXECUTING)
    db.add(executing_task)
    now = datetime.utcnow()
    db.add_all(
        [
            StopwatchSession(
                session_id="dup-open-1",
                task_id="dup-open-task",
                user_id=9112,
                start_time_utc=now - timedelta(hours=4),
                end_time_utc=None,
                total_paused_minutes=0.0,
                auto_closed=False,
            ),
            StopwatchSession(
                session_id="dup-open-2",
                task_id="dup-open-task",
                user_id=9112,
                start_time_utc=now - timedelta(hours=3),
                end_time_utc=None,
                paused_at_utc=now - timedelta(hours=80),
                total_paused_minutes=0.0,
                auto_closed=False,
            ),
        ]
    )
    db.commit()

    res = client.get("/v1/operator/dashboard", headers=auth_headers(9111))
    assert res.status_code == 200
    body = res.json()

    assert body["cohort_readiness"]["status"] == "red"
    assert body["cohort_readiness"]["safe_to_invite_more_users"] is False
    assert body["state_invariants"]["duplicate_open_sessions"] >= 1
    assert body["state_invariants"]["executed_tasks_missing_start_or_end"] >= 1
    assert body["state_invariants"]["stale_reentry_candidates"] >= 1
    assert body["privacy_boundary"]["raw_task_titles_exposed"] is False
    assert body["privacy_boundary"]["raw_emails_exposed"] is False
    assert "user-9112@example.test" not in str(body)
    assert "Task clean-task" not in str(body)


def test_operator_dashboard_marks_uninstrumented_metrics(client, db):
    ids = [9121, 9122]
    _clear_ids(db, ids)
    db.add(_user(9121, operator=True))
    db.add(_user(9122, operator=False))
    db.commit()

    res = client.get("/v1/operator/dashboard", headers=auth_headers(9121))
    assert res.status_code == 200
    body = res.json()

    assert body["activity_frequency"]["login_frequency_status"] == "not_instrumented"
    assert body["notification_lifecycle"]["web_rendered"] is None
    assert "login_only" in body["meaningful_activity_definition"]["excluded_events"]
    assert "task_created" in body["meaningful_activity_definition"]["included_events"]
