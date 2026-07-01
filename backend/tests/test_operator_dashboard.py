from datetime import datetime, timedelta

from app.db.models import (
    ExposureAckEvent,
    ExposureDecisionEvent,
    ExposureRenderEvent,
    NotificationLifecycleEvent,
    StopwatchSession,
    Task,
    TaskState,
    User,
)
from app.db.scoping import get_current_user_id, set_current_user_id
from app.services.exposure_ledger import record_decision, record_render, record_suppression
from app.api.v1.endpoints import operator as operator_endpoint
from tests.conftest import auth_headers


def _clear_ids(db, ids: list[int]) -> None:
    original_uid = get_current_user_id()
    set_current_user_id(None)
    try:
        exposure_ids = [
            row[0]
            for row in (
                db.query(ExposureDecisionEvent.exposure_id)
                .filter(ExposureDecisionEvent.user_id.in_(ids))
                .all()
            )
        ]
        if exposure_ids:
            db.query(NotificationLifecycleEvent).filter(
                NotificationLifecycleEvent.exposure_id.in_(exposure_ids)
            ).delete(synchronize_session=False)
            db.query(ExposureAckEvent).filter(
                ExposureAckEvent.exposure_id.in_(exposure_ids)
            ).delete(synchronize_session=False)
            db.query(ExposureRenderEvent).filter(
                ExposureRenderEvent.exposure_id.in_(exposure_ids)
            ).delete(synchronize_session=False)
        db.query(NotificationLifecycleEvent).filter(
            NotificationLifecycleEvent.user_id.in_(ids)
        ).delete(synchronize_session=False)
        db.query(ExposureDecisionEvent).filter(
            ExposureDecisionEvent.user_id.in_(ids)
        ).delete(synchronize_session=False)
        db.query(StopwatchSession).filter(StopwatchSession.user_id.in_(ids)).delete()
        db.query(Task).filter(Task.user_id.in_(ids)).delete()
        db.query(User).filter(User.user_id.in_(ids)).delete()
        db.commit()
    finally:
        set_current_user_id(original_uid)


def _clear_notification_lifecycle(db) -> None:
    original_uid = get_current_user_id()
    set_current_user_id(None)
    try:
        db.query(NotificationLifecycleEvent).delete()
        db.commit()
    finally:
        set_current_user_id(original_uid)


def _user(user_id: int, *, operator: bool = False) -> User:
    user = User(
        user_id=user_id,
        email=f"user-{user_id}@cohort.example.com",
        google_id=f"google-{user_id}",
        is_operator=operator,
        timezone="Africa/Cairo",
        created_at=datetime.utcnow() - timedelta(days=10),
        terms_accepted_at=datetime.utcnow() - timedelta(days=10),
    )
    if not operator:
        user.google_first_name = f"User{user_id}"
        user.google_display_name = f"User{user_id} Example"
    return user


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
    issue_ids = {issue["id"] for issue in body["dynamic_issues"]}
    assert "duplicate_open_sessions" in issue_ids
    assert "executed_tasks_missing_execution_interval" in issue_ids
    assert "stale_paused_sessions_need_resolution" in issue_ids
    assert "duplicate_open_sessions" in body["cohort_readiness"]["minimum_fix_set"]
    assert "user-9112@cohort.example.com" not in str(body)
    assert "Task clean-task" not in str(body)
    row = next(row for row in body["users"] if row["user_id"] == 9112)
    assert row["first_name"] == "User9112"
    assert row["name_source"] == "google_profile"


def test_operator_dashboard_marks_uninstrumented_metrics(client, db):
    ids = [9121, 9122]
    _clear_ids(db, ids)
    _clear_notification_lifecycle(db)
    db.add(_user(9121, operator=True))
    db.add(_user(9122, operator=False))
    db.commit()

    res = client.get("/v1/operator/dashboard", headers=auth_headers(9121))
    assert res.status_code == 200
    body = res.json()

    assert body["activity_frequency"]["login_frequency_status"] == "not_instrumented"
    assert body["notification_lifecycle"]["web_rendered"] == 0
    assert "web_rendered" not in body["notification_lifecycle"]["not_instrumented_fields"]
    assert "login_only" in body["meaningful_activity_definition"]["excluded_events"]
    assert "task_created" in body["meaningful_activity_definition"]["included_events"]
    issue_ids = {issue["id"] for issue in body["dynamic_issues"]}
    assert "notification_source_freshness_not_instrumented" in issue_ids


def test_operator_dashboard_blocks_on_exposure_without_render(client, db):
    ids = list(range(9101, 9150))
    _clear_ids(db, ids)
    db.add(_user(9131, operator=True))
    db.add(_user(9132, operator=False))
    old_exposure_stamp = datetime.utcnow() - timedelta(days=30)
    recent_render_stamp = datetime.utcnow() - timedelta(minutes=2)
    rendered_decision = record_decision(
        db,
        user_id=9132,
        eligible_at=old_exposure_stamp,
        delivered_at=old_exposure_stamp,
        decision_status="shown",
        exposure_category="behavioral_insight",
        content_template_id="analytics_insights",
        initiative="system",
        trigger_source="test",
    )
    rendered_decision.created_at = old_exposure_stamp
    record_render(
        db,
        exposure_id=rendered_decision.exposure_id,
        rendered_at=recent_render_stamp,
        surface="operator_test",
        channel="web",
        content_snapshot="rendered older exposure",
        render_policy_version="test",
        interruptiveness="low",
        salience_level="low",
    )

    exposure_stamp = datetime.utcnow() - timedelta(minutes=5)
    decision = record_decision(
        db,
        user_id=9132,
        eligible_at=exposure_stamp,
        delivered_at=exposure_stamp,
        decision_status="shown",
        exposure_category="behavioral_insight",
        content_template_id="analytics_insights",
        initiative="system",
        trigger_source="test",
    )
    decision.created_at = exposure_stamp
    db.commit()

    res = client.get("/v1/operator/dashboard", headers=auth_headers(9131))
    assert res.status_code == 200
    body = res.json()
    assert body["notification_lifecycle"]["exposure_without_render_count"] >= 1
    issue = next(
        issue
        for issue in body["dynamic_issues"]
        if issue["id"] == "exposure_records_without_render_evidence"
    )
    assert issue["severity"] == "critical"
    assert issue["blocks_cohort_expansion"] is True
    assert issue["tags"] == []
    assert "exposure_records_without_render_evidence" in body["cohort_readiness"]["blockers"]
    assert "exposure_records_without_render_evidence" in body["cohort_readiness"]["minimum_fix_set"]
    assert any(
        rec["message"] == issue["message"]
        and rec["blocks_cohort_expansion"] is True
        for rec in body["operator_recommendations"]
    )


def test_operator_dashboard_does_not_block_on_suppressed_exposures(client, db):
    ids = list(range(9101, 9150))
    _clear_ids(db, ids)
    db.add(_user(9131, operator=True))
    db.add(_user(9132, operator=False))
    exposure_stamp = datetime.utcnow() - timedelta(minutes=5)
    suppressed = record_decision(
        db,
        user_id=9132,
        eligible_at=exposure_stamp,
        delivered_at=None,
        decision_status="suppressed",
        exposure_category="behavioral_insight",
        content_template_id="analytics_insights",
        initiative="system",
        trigger_source="test",
    )
    suppressed.created_at = exposure_stamp
    record_suppression(
        db,
        exposure_id=suppressed.exposure_id,
        suppressed_at=exposure_stamp,
        suppression_reason="measurement_safety",
        would_have_rendered_template_id="analytics_insights",
    )
    db.commit()

    res = client.get("/v1/operator/dashboard", headers=auth_headers(9131))
    assert res.status_code == 200
    body = res.json()
    assert body["notification_lifecycle"]["exposure_without_render_count"] == 0
    assert body["notification_lifecycle"]["suppressed_without_render_count"] == 1
    issue_ids = {issue["id"] for issue in body["dynamic_issues"]}
    assert "exposure_records_without_render_evidence" not in issue_ids


def test_operator_dashboard_does_not_block_on_queued_notification_decisions(client, db):
    ids = list(range(9101, 9150))
    _clear_ids(db, ids)
    db.add(_user(9131, operator=True))
    db.add(_user(9132, operator=False))
    exposure_stamp = datetime.utcnow() - timedelta(minutes=5)
    queued = record_decision(
        db,
        user_id=9132,
        eligible_at=exposure_stamp,
        delivered_at=None,
        decision_status="queued",
        exposure_category="reminder",
        content_template_id="pre_task_reminder",
        initiative="system",
        trigger_source="worker.reminder",
    )
    queued.created_at = exposure_stamp
    db.commit()

    res = client.get("/v1/operator/dashboard", headers=auth_headers(9131))
    assert res.status_code == 200
    body = res.json()
    assert body["notification_lifecycle"]["exposure_without_render_count"] == 0
    assert body["notification_lifecycle"]["queued_without_render_count"] == 1
    issue_ids = {issue["id"] for issue in body["dynamic_issues"]}
    assert "exposure_records_without_render_evidence" not in issue_ids


class _DashboardRedis:
    def __init__(self, rows_by_key):
        self.rows_by_key = rows_by_key

    def lrange(self, key, _start, _end):
        return self.rows_by_key.get(key, [])


class _DashboardRedisClient:
    def __init__(self, rows_by_key):
        self.client = _DashboardRedis(rows_by_key)


def test_operator_dashboard_reminder_duplicates_do_not_fail_k02(client, db, monkeypatch):
    ids = list(range(9101, 9150))
    _clear_ids(db, ids)
    db.add(_user(9131, operator=True))
    db.add(_user(9132, operator=False))
    db.commit()
    payloads = [
        '{"notification_id":"r-1","type":"reminder","message":"redacted"}',
        '{"notification_id":"r-2","type":"reminder","message":"redacted"}',
        '{"notification_id":"r-3","type":"reminder","message":"redacted"}',
    ]
    monkeypatch.setattr(
        operator_endpoint,
        "RedisClient",
        lambda: _DashboardRedisClient({"notifications:pending:9132": payloads}),
    )

    res = client.get("/v1/operator/dashboard", headers=auth_headers(9131))
    assert res.status_code == 200
    body = res.json()
    assert body["notification_lifecycle"]["duplicate_prompt_count"] == 2
    assert body["notification_lifecycle"]["duplicate_prompt_type_counts"] == {
        "reminder": 2
    }
    assert body["bug_watchlist"]["k02_timer_overflow_duplicate"] == "pass"
    issue = next(
        issue
        for issue in body["dynamic_issues"]
        if issue["id"] == "duplicate_pending_reminder_prompt"
    )
    assert issue["blocks_cohort_expansion"] is True
    assert "K02" not in issue["tags"]


def test_operator_dashboard_distinct_legacy_reminders_are_not_duplicates(
    client, db, monkeypatch
):
    ids = list(range(9101, 9150))
    _clear_ids(db, ids)
    db.add(_user(9131, operator=True))
    db.add(_user(9132, operator=False))
    db.commit()
    payloads = [
        '{"notification_id":"r-1","type":"reminder","message":"Task A starts soon"}',
        '{"notification_id":"r-2","type":"reminder","message":"Task B starts soon"}',
        '{"notification_id":"r-3","type":"reminder","message":"Task C starts soon"}',
    ]
    monkeypatch.setattr(
        operator_endpoint,
        "RedisClient",
        lambda: _DashboardRedisClient({"notifications:pending:9132": payloads}),
    )

    res = client.get("/v1/operator/dashboard", headers=auth_headers(9131))
    assert res.status_code == 200
    body = res.json()
    assert body["notification_lifecycle"]["duplicate_prompt_count"] == 0
    assert body["notification_lifecycle"]["duplicate_prompt_type_counts"] == {}
    assert "duplicate_pending_reminder_prompt" not in {
        issue["id"] for issue in body["dynamic_issues"]
    }


def test_operator_dashboard_exposure_contamination_is_task_window_scoped(client, db):
    ids = list(range(9101, 9150))
    _clear_ids(db, ids)
    db.add(_user(9131, operator=True))
    db.add(_user(9132, operator=False))

    clean_task = _task(9132, "exposure-clean-task", state=TaskState.EXECUTED)
    clean_task.created_at = datetime.utcnow() - timedelta(hours=3)
    clean_task.planned_start_utc = datetime.utcnow() - timedelta(hours=2)
    clean_task.planned_end_utc = clean_task.planned_start_utc + timedelta(minutes=60)
    clean_task.executed_start_utc = clean_task.planned_start_utc
    clean_task.executed_end_utc = clean_task.planned_start_utc + timedelta(minutes=50)
    clean_task.executed_duration_minutes = 50
    db.add(clean_task)
    db.add(
        StopwatchSession(
            session_id="exposure-clean-session",
            task_id="exposure-clean-task",
            user_id=9132,
            start_time_utc=clean_task.executed_start_utc,
            end_time_utc=clean_task.executed_end_utc,
            total_paused_minutes=0.0,
            auto_closed=False,
        )
    )
    db.flush()

    unrelated = record_decision(
        db,
        user_id=9132,
        eligible_at=clean_task.executed_start_utc + timedelta(minutes=5),
        delivered_at=clean_task.executed_start_utc + timedelta(minutes=5),
        decision_status="shown",
        exposure_category="behavioral_insight",
        content_template_id="analytics_insights",
        initiative="system",
        trigger_source="test",
    )
    record_render(
        db,
        exposure_id=unrelated.exposure_id,
        rendered_at=clean_task.executed_start_utc + timedelta(minutes=5),
        surface="operator_test",
        channel="web",
        content_snapshot="unrelated after-start insight",
        render_policy_version="test",
        interruptiveness="low",
        salience_level="low",
    )
    db.commit()

    res = client.get("/v1/operator/dashboard", headers=auth_headers(9131))
    assert res.status_code == 200
    body = res.json()
    assert body["measurement_integrity"]["clean_trace_ratio"] == 1.0
    assert body["measurement_integrity"]["dirty_reasons"]["exposure_contaminated"] == 0

    contaminating = record_decision(
        db,
        user_id=9132,
        eligible_at=clean_task.executed_start_utc - timedelta(minutes=5),
        delivered_at=clean_task.executed_start_utc - timedelta(minutes=5),
        decision_status="shown",
        exposure_category="behavioral_insight",
        content_template_id="analytics_insights",
        initiative="system",
        trigger_source="test",
    )
    record_render(
        db,
        exposure_id=contaminating.exposure_id,
        rendered_at=clean_task.executed_start_utc - timedelta(minutes=5),
        surface="operator_test",
        channel="web",
        content_snapshot="in-window insight",
        render_policy_version="test",
        interruptiveness="low",
        salience_level="low",
    )
    db.commit()

    res = client.get("/v1/operator/dashboard", headers=auth_headers(9131))
    assert res.status_code == 200
    body = res.json()
    assert body["measurement_integrity"]["clean_trace_ratio"] == 0.0
    assert body["measurement_integrity"]["dirty_trace_count"] == 1
    assert body["measurement_integrity"]["dirty_reasons"]["exposure_contaminated"] == 1
    assert body["measurement_integrity"]["dirty_reason_distribution"]["exposure_contaminated"] == 1
    assert body["measurement_integrity"]["clean_trace_ratio_basis"]["denominator"] == 1
    assert "excluded_from_denominator" in body["measurement_integrity"]["clean_trace_ratio_basis"]
    assert "operator_user_sessions" in body["measurement_integrity"]["clean_trace_ratio_basis"]["excluded_from_denominator"]


def test_operator_dashboard_read_is_side_effect_free(client, db):
    ids = list(range(9101, 9150))
    _clear_ids(db, ids)
    db.add(_user(9141, operator=True))
    db.add(_user(9142, operator=False))
    event = NotificationLifecycleEvent(
        event_id="operator-readonly-lifecycle",
        user_id=9142,
        notification_id="operator-readonly-notification",
        channel="web",
        notification_type="timer_overflow",
        status="queued",
        queued_at=datetime.utcnow(),
        last_transition_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()

    before = {
        "notifications": db.query(NotificationLifecycleEvent).count(),
        "decisions": db.query(ExposureDecisionEvent).count(),
        "renders": db.query(ExposureRenderEvent).count(),
        "acks": db.query(ExposureAckEvent).count(),
    }
    res = client.get("/v1/operator/dashboard", headers=auth_headers(9141))
    assert res.status_code == 200
    after = {
        "notifications": db.query(NotificationLifecycleEvent).count(),
        "decisions": db.query(ExposureDecisionEvent).count(),
        "renders": db.query(ExposureRenderEvent).count(),
        "acks": db.query(ExposureAckEvent).count(),
    }
    assert after == before
