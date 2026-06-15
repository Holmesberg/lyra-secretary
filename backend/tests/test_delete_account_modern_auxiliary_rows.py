"""Delete-account regression for modern user-owned auxiliary rows.

The account deletion endpoint predates deadlines, exposure acknowledgements,
feedback, corrections, and other append-only ledgers. Those rows must not block
the final user DELETE, and they must not leave raw user-owned residue after a
hard delete.
"""
import json
from datetime import datetime, timedelta
from uuid import uuid4

from app.db.models import (
    CalibrationNudgeEvent,
    Deadline,
    DeadlineCompletionEvent,
    EmailEngagementEvent,
    ExposureAckEvent,
    ExposureDecisionEvent,
    ExposurePolicyEffectLog,
    ExposureRenderEvent,
    ExternalEventOutcome,
    Feedback,
    JarvisInvocation,
    NotificationLifecycleEvent,
    PauseEvent,
    PausePredictionLog,
    ReflectionViewLog,
    ResumePredictionLog,
    SecurityAuditEvent,
    StopwatchSession,
    SuppressionEvent,
    Task,
    TaskDeadlineOutcome,
    TaskExecutionCorrection,
    TaskSource,
    TaskState,
    User,
)
from tests.conftest import TestingSession, auth_headers


def _seed_user_with_modern_auxiliary_rows(email: str) -> dict[str, str | int]:
    now = datetime.utcnow()
    uid_by_name: dict[str, str | int] = {}
    db = TestingSession()
    try:
        user = User(
            email=email,
            google_id=None,
            timezone="Africa/Cairo",
            is_operator=False,
            notion_enabled=False,
            terms_accepted_at=now,
            google_refresh_token="raw-google-refresh-secret",
            moodle_ics_url=(
                "https://lms.example.edu/calendar/export_execute.php?"
                "authtoken=raw-moodle-secret"
            ),
            moodle_ws_token="raw-moodle-ws-secret",
            moodle_last_synced_at=now,
            moodle_ws_last_synced_at=now,
            moodle_disconnect_reason="manual_test",
            moodle_ws_disconnect_reason="manual_test",
            moodle_userid=123,
            moodle_base_url="https://lms.example.edu",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        uid = user.user_id
        deadline_id = str(uuid4())
        task_id = str(uuid4())
        session_id = str(uuid4())
        exposure_id = str(uuid4())

        db.add(
            Deadline(
                deadline_id=deadline_id,
                user_id=uid,
                title="Private exam deadline",
                description="private deadline details",
                due_at_utc=now + timedelta(days=1),
                state="active",
            )
        )
        db.commit()

        db.add(
            Task(
                task_id=task_id,
                user_id=uid,
                title="Private study task",
                category="study",
                planned_start_utc=now,
                planned_end_utc=now + timedelta(minutes=30),
                planned_duration_minutes=30,
                executed_start_utc=now,
                executed_end_utc=now + timedelta(minutes=45),
                executed_duration_minutes=45,
                state=TaskState.EXECUTED,
                source=TaskSource.MANUAL,
                notes="private notes",
                description="private description",
                deadline_id=deadline_id,
                llm_inferred_deadline_id=deadline_id,
                llm_deadline_candidates=[
                    {"deadline_id": deadline_id, "title": "Private exam deadline"}
                ],
                llm_sub_items=["private sub item"],
                llm_alternative_suggestion={
                    "deadline_id": deadline_id,
                    "title": "Private alternative",
                },
            )
        )
        db.commit()

        db.add_all(
            [
                StopwatchSession(
                    session_id=session_id,
                    task_id=task_id,
                    user_id=uid,
                    start_time_utc=now,
                    end_time_utc=now + timedelta(minutes=45),
                    total_paused_minutes=0,
                ),
                DeadlineCompletionEvent(
                    deadline_id=deadline_id,
                    user_id=uid,
                    task_id=task_id,
                    completion_source="user_deadline_done",
                    completed_at_utc=now,
                    recorded_at_utc=now,
                    due_at_utc_at_event=now + timedelta(days=1),
                    completed_after_due=False,
                    delay_minutes=-1440,
                    time_provenance="observed_user_action",
                ),
                TaskDeadlineOutcome(
                    task_id=task_id,
                    user_id=uid,
                    computed_at=now,
                    deadline_utc_at_compute=now + timedelta(days=1),
                    executed_end_utc_at_compute=now + timedelta(minutes=45),
                    deadline_met=True,
                    delay_minutes=-1395,
                ),
                TaskExecutionCorrection(
                    task_id=task_id,
                    user_id=uid,
                    note="private correction note",
                    original_executed_start_utc=now,
                    original_executed_end_utc=now + timedelta(minutes=60),
                    original_executed_duration_minutes=60,
                    corrected_executed_end_utc=now + timedelta(minutes=45),
                    corrected_executed_duration_minutes=45,
                ),
                PauseEvent(
                    session_id=session_id,
                    user_id=uid,
                    paused_at_utc=now + timedelta(minutes=10),
                    resumed_at_utc=now + timedelta(minutes=15),
                    duration_minutes=5,
                    pause_reason="break",
                    pause_initiator="user",
                ),
                PausePredictionLog(
                    user_id=uid,
                    fired_at=now,
                    predicted_at=now + timedelta(minutes=5),
                    mechanism="clock_anchor",
                    confidence=0.8,
                    lead_minutes=5,
                    sample_size=12,
                    active_task_id=task_id,
                ),
                ResumePredictionLog(
                    user_id=uid,
                    session_id=session_id,
                    task_id=task_id,
                    fired_at=now,
                    paused_for_minutes=30,
                    mechanism="cold_start_synthetic",
                    confidence=0.5,
                    sample_size=1,
                ),
                CalibrationNudgeEvent(
                    user_id=uid,
                    task_id=task_id,
                    suggested_duration_minutes=25,
                    user_planned_duration_minutes=30,
                    bias_factor=1.2,
                    sample_size=12,
                    user_decision="dismissed",
                    decided_at=now,
                ),
                ReflectionViewLog(
                    user_id=uid,
                    reflection_type="micro_mirror",
                    event_class="impression",
                    task_id=task_id,
                    payload="Private reflection payload",
                    fired_at=now,
                ),
                ExposureDecisionEvent(
                    exposure_id=exposure_id,
                    user_id=uid,
                    task_id=task_id,
                    eligible_at=now,
                    decision_status="shown",
                    initiative="system",
                    exposure_category="insight",
                    trigger_source="test",
                    randomization_arm="none",
                ),
                ExposurePolicyEffectLog(
                    user_id=uid,
                    policy_version="test",
                    exposure_category="insight",
                    signal_target="analytics",
                    state_distribution_counts={"clean": 1},
                    unknown_rate=0,
                    ledger_incomplete_rate=0,
                    sample_count=1,
                    window_start=now,
                    window_end=now + timedelta(minutes=1),
                ),
                NotificationLifecycleEvent(
                    user_id=uid,
                    notification_id="notif-private-1",
                    channel="web",
                    notification_type="timer_overflow",
                    status="queued",
                    dedupe_key="timer_overflow:private-session",
                    payload_hash="notif-hash",
                    content_snapshot="private notification content",
                    surface_id="worker.timer_overflow",
                    exposure_id=exposure_id,
                    task_id=task_id,
                    session_id=session_id,
                    queued_at=now,
                    last_transition_at=now,
                    created_at=now,
                ),
                EmailEngagementEvent(
                    user_id=uid,
                    campaign_version="activation_v1",
                    event_type="click",
                    recipient_key="recipient-key",
                    target_url="https://lyraos.org/welcome?token=raw-click-secret",
                    provider_message_id="provider-message-id",
                    request_metadata={
                        "user_agent": "private ua",
                        "ip_prefix": "127.0.0.1",
                    },
                    occurred_at=now,
                ),
                Feedback(
                    user_id=uid,
                    submitted_at=now,
                    kind="bug",
                    body="private feedback body",
                ),
                JarvisInvocation(
                    user_id=uid,
                    tool_name="read_tasks",
                    tool_args={"private": True},
                    tool_result_summary="private result",
                ),
                ExternalEventOutcome(
                    user_id=uid,
                    external_source="google_calendar",
                    external_id="private-event",
                    outcome="attended",
                    event_title="Private event",
                    marked_at=now,
                ),
                SecurityAuditEvent(
                    actor_user_id=uid,
                    user_id=uid,
                    event_type="provider_connected",
                    surface="/v1/test",
                    target_type="provider",
                    target_id="moodle",
                    status="success",
                    ip_hash="ip-hash",
                    user_agent_hash="ua-hash",
                    redacted_metadata={"provider_url": "[redacted]"},
                    created_at=now,
                ),
            ]
        )
        db.commit()

        db.add_all(
            [
                ExposureRenderEvent(
                    exposure_id=exposure_id,
                    rendered_at=now,
                    surface="insights",
                    channel="web",
                    content_hash="hash",
                    content_snapshot="private content snapshot",
                    render_policy_version="test",
                    interruptiveness="low",
                    salience_level="low",
                ),
                ExposureAckEvent(
                    exposure_id=exposure_id,
                    user_id=uid,
                    event_type="render",
                    acked_at=now,
                ),
                SuppressionEvent(
                    exposure_id=exposure_id,
                    suppressed_at=now,
                    suppression_reason="test",
                ),
            ]
        )
        db.commit()

        uid_by_name.update(
            {
                "user_id": uid,
                "task_id": task_id,
                "session_id": session_id,
                "deadline_id": deadline_id,
                "exposure_id": exposure_id,
            }
        )
        return uid_by_name
    finally:
        db.close()


def _count_user_rows(model, user_id: int) -> int:
    db = TestingSession()
    try:
        return db.query(model).filter(model.user_id == user_id).count()
    finally:
        db.close()


def _count_exposure_rows(model, exposure_id: str) -> int:
    db = TestingSession()
    try:
        return db.query(model).filter(model.exposure_id == exposure_id).count()
    finally:
        db.close()


def test_delete_retention_mode_purges_modern_auxiliary_rows(client):
    email = "delete-retain-modern-aux@example.com"
    ids = _seed_user_with_modern_auxiliary_rows(email)
    user_id = int(ids["user_id"])

    resp = client.request(
        "DELETE",
        "/v1/users/me",
        json={"confirm_email": email, "retain_for_research": True},
        headers=auth_headers(user_id),
    )

    assert resp.status_code == 200, resp.text
    assert _count_user_rows(User, user_id) == 0

    db = TestingSession()
    try:
        task = db.query(Task).filter(Task.task_id == ids["task_id"]).one()
        session = (
            db.query(StopwatchSession)
            .filter(StopwatchSession.session_id == ids["session_id"])
            .one()
        )
        assert task.title == "[anonymized]"
        assert task.notes is None
        assert task.description is None
        assert task.deadline_id is None
        assert task.llm_inferred_deadline_id is None
        assert task.llm_deadline_candidates is None
        assert task.llm_sub_items is None
        assert task.llm_alternative_suggestion is None
        assert task.post_deletion_retained_at is not None
        assert task.original_user_id_hash
        assert session.post_deletion_retained_at is not None
        assert session.original_user_id_hash
    finally:
        db.close()

    for model in (
        Deadline,
        DeadlineCompletionEvent,
        TaskDeadlineOutcome,
        TaskExecutionCorrection,
        PauseEvent,
        PausePredictionLog,
        ResumePredictionLog,
        CalibrationNudgeEvent,
        ReflectionViewLog,
        ExposureDecisionEvent,
        ExposureAckEvent,
        ExposurePolicyEffectLog,
        NotificationLifecycleEvent,
        Feedback,
        JarvisInvocation,
        ExternalEventOutcome,
        EmailEngagementEvent,
    ):
        assert _count_user_rows(model, user_id) == 0, model.__tablename__
    assert _count_exposure_rows(ExposureRenderEvent, str(ids["exposure_id"])) == 0
    assert _count_exposure_rows(SuppressionEvent, str(ids["exposure_id"])) == 0


def test_export_registry_includes_user_owned_sections_and_redacts_secrets(client):
    email = "export-registry-modern-aux@example.com"
    ids = _seed_user_with_modern_auxiliary_rows(email)
    user_id = int(ids["user_id"])

    resp = client.get("/v1/users/me/export", headers=auth_headers(user_id))

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["schema_version"] == "user_data_export_v2"

    expected_sections = {
        "tasks",
        "deadlines",
        "deadline_completion_events",
        "task_deadline_outcomes",
        "stopwatch_sessions",
        "task_execution_corrections",
        "pause_events",
        "pause_prediction_logs",
        "resume_prediction_logs",
        "calibration_nudge_events",
        "reflection_view_logs",
        "exposure_decision_events",
        "exposure_render_events",
        "exposure_ack_events",
        "suppression_events",
        "exposure_policy_effect_logs",
        "feedback",
        "external_event_outcomes",
        "notification_lifecycle_events",
        "email_engagement_events",
        "archetype_assignments",
        "jarvis_invocations",
    }
    assert expected_sections.issubset(set(data.keys()))
    assert {entry["section"] for entry in data["registry"]} >= expected_sections

    for section in expected_sections - {"archetype_assignments"}:
        assert len(data[section]) >= 1, section

    assert data["integration_state"]["google_calendar"]["connected"] is True
    assert data["integration_state"]["moodle_ics"]["connected"] is True
    assert data["integration_state"]["moodle_ws"]["connected"] is True
    assert data["integration_state"]["moodle_ics"]["credential_exported"] is False
    assert data["integration_state"]["moodle_ws"]["credential_exported"] is False
    assert data["governance_audit_policy"]["exported_in_this_file"] is False
    assert (
        data["governance_audit_policy"]["delete_policy"]
        == "append_only_redacted_security_governance_log"
    )

    encoded = json.dumps(data, sort_keys=True)
    assert "raw-google-refresh-secret" not in encoded
    assert "raw-moodle-secret" not in encoded
    assert "raw-moodle-ws-secret" not in encoded
    assert "raw-click-secret" not in encoded
    assert "authtoken=" not in encoded


def test_delete_hard_mode_purges_modern_auxiliary_rows(client):
    email = "delete-hard-modern-aux@example.com"
    ids = _seed_user_with_modern_auxiliary_rows(email)
    user_id = int(ids["user_id"])

    resp = client.request(
        "DELETE",
        "/v1/users/me",
        json={"confirm_email": email, "retain_for_research": False},
        headers=auth_headers(user_id),
    )

    assert resp.status_code == 200, resp.text
    for model in (
        User,
        Task,
        StopwatchSession,
        Deadline,
        DeadlineCompletionEvent,
        TaskDeadlineOutcome,
        TaskExecutionCorrection,
        PauseEvent,
        PausePredictionLog,
        ResumePredictionLog,
        CalibrationNudgeEvent,
        ReflectionViewLog,
        ExposureDecisionEvent,
        ExposureAckEvent,
        ExposurePolicyEffectLog,
        NotificationLifecycleEvent,
        Feedback,
        JarvisInvocation,
        ExternalEventOutcome,
        EmailEngagementEvent,
    ):
        assert _count_user_rows(model, user_id) == 0, model.__tablename__
    assert _count_exposure_rows(ExposureRenderEvent, str(ids["exposure_id"])) == 0
    assert _count_exposure_rows(SuppressionEvent, str(ids["exposure_id"])) == 0


def test_delete_account_invokes_runtime_state_purge(client, monkeypatch):
    email = "delete-runtime-purge@example.com"
    ids = _seed_user_with_modern_auxiliary_rows(email)
    user_id = int(ids["user_id"])
    calls: list[int] = []

    class FakeRedisClient:
        def purge_user_runtime_state(self, uid):
            calls.append(int(uid))
            return 12

    monkeypatch.setattr(
        "app.api.v1.endpoints.users.RedisClient",
        lambda: FakeRedisClient(),
    )

    resp = client.request(
        "DELETE",
        "/v1/users/me",
        json={"confirm_email": email, "retain_for_research": False},
        headers=auth_headers(user_id),
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["runtime_state_purged"] is True
    assert calls == [user_id]
