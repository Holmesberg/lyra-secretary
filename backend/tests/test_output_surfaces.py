import json
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.db.models import (
    Archetype,
    ExposureAckEvent,
    ExposureDecisionEvent,
    ExposureRenderEvent,
    ReflectionViewLog,
    SuppressionEvent,
    StopwatchSession,
    Task,
    TaskSource,
    TaskState,
    User,
)
from app.main import app
from app.services import output_surfaces as output_surface_module
from app.services.output_surfaces import (
    OutputSurfaceSpec,
    RULE11_ACTIVE_ARM,
    RULE11_CONTROL_ARM,
    RULE11_POLICY_VERSION,
    acknowledge_surface_render,
    create_output_surface_decision,
    emit_surface_render,
    emit_surface_suppression,
    get_output_surface_spec,
    load_output_surface_registry,
    output_surface_diagnostics,
    projection_class_for_profile,
    rule11_no_nudge_control_active,
    rule11_randomization_fields,
    suppress_existing_surface_decision,
)
from app.utils.time_utils import now_utc
from tests.conftest import auth_headers


def test_output_surface_registry_declares_required_runtime_fields():
    registry = load_output_surface_registry()
    first_wave_surfaces = {
        "stopwatch.micro_mirror",
        "stopwatch.calibration_nudge",
        "task.creation_nudge",
        "task.deadline_binding_suggestion",
        "academic.pressure_map",
        "worker.reminder",
        "worker.pause_prediction",
        "worker.resume_prediction",
        "analytics.archetype_proximity",
        "analytics.insights",
    }
    assert first_wave_surfaces <= set(registry)
    allowed_truth_classes = {
        "trace",
        "metric",
        "interpretation",
        "intervention",
        "diagnostic_only",
    }
    allowed_usage_classes = {
        "product",
        "research",
        "diagnostic",
        "operator",
        "not_learning_v0",
    }
    allowed_fallback_modes = {
        "empty",
        "degrade",
        "settling_in",
        "suppress",
    }

    for surface_id, spec in registry.items():
        assert spec.surface_id == surface_id
        assert spec.truth_class in allowed_truth_classes
        assert spec.usage_class in allowed_usage_classes
        assert spec.channel
        assert spec.exposure_category
        assert spec.signal_targets
        assert spec.min_n >= 0
        assert spec.time_window_days is None or spec.time_window_days >= 0
        assert spec.fallback_mode in allowed_fallback_modes
        assert isinstance(spec.operator_only, bool)
        assert spec.render_policy_version


def test_emit_surface_render_serializes_structured_payloads_and_legacy_adapter(db):
    user = User(email=f"surface-{uuid4()}@example.com", timezone="Africa/Cairo")
    db.add(user)
    db.flush()

    payload = {"kind": "creation_nudge", "estimate": 45}
    emitted = emit_surface_render(
        db,
        surface_id="task.creation_nudge",
        user_id=user.user_id,
        content_snapshot=payload,
        create_legacy_view=True,
        legacy_payload=payload,
    )
    db.commit()

    expected_payload = json.dumps(payload, sort_keys=True, default=str)
    decision = (
        db.query(ExposureDecisionEvent)
        .filter(ExposureDecisionEvent.exposure_id == emitted["exposure_id"])
        .one()
    )
    render = (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.render_id == emitted["render_id"])
        .one()
    )
    legacy = (
        db.query(ReflectionViewLog)
        .filter(ReflectionViewLog.view_id == emitted["legacy_view_id"])
        .one()
    )

    assert decision.decision_status == "rendered"
    assert decision.exposure_category == "scheduling_suggestion"
    assert render.surface == "task.creation_nudge"
    assert render.content_snapshot == expected_payload
    assert legacy.reflection_type == "creation_nudge"
    assert legacy.payload == expected_payload


def test_emit_surface_render_mirrors_to_operator_without_content(db, monkeypatch):
    user = User(email=f"surface-mirror-{uuid4()}@example.com", timezone="Africa/Cairo")
    db.add(user)
    db.flush()
    calls: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        output_surface_module.settings,
        "OPENCLAW_MIRROR_USER_NOTIFICATIONS",
        True,
    )
    monkeypatch.setattr(
        output_surface_module,
        "notify_operator",
        lambda message, **kwargs: calls.append((message, kwargs)) or True,
    )

    emitted = emit_surface_render(
        db,
        surface_id="stopwatch.micro_mirror",
        user_id=user.user_id,
        content_snapshot="Secret behavioral mirror copy",
        task_id="task-private-123",
        content_template_id="micro_mirror",
        trigger_source="stopwatch.stop",
    )

    assert emitted["surface_id"] == "stopwatch.micro_mirror"
    assert len(calls) == 1
    message, kwargs = calls[0]
    assert kwargs == {"source": "output.surface", "severity": "info"}
    assert "Output surface rendered." in message
    assert "User: user#" in message
    assert "Surface: `stopwatch.micro_mirror`" in message
    assert "Channel: `in_app_toast`" in message
    assert "Template: `micro_mirror`" in message
    assert "Trigger: `stopwatch.stop`" in message
    assert "Exposure: #" in message
    assert "Render: #" in message
    assert "Task: #" in message
    assert "Secret behavioral mirror copy" not in message
    assert "task-private-123" not in message


def test_dashboard_output_surfaces_do_not_mirror_to_operator(db, monkeypatch):
    user = User(email=f"surface-dashboard-{uuid4()}@example.com", timezone="Africa/Cairo")
    db.add(user)
    db.flush()
    calls: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        output_surface_module.settings,
        "OPENCLAW_MIRROR_USER_NOTIFICATIONS",
        True,
    )
    monkeypatch.setattr(
        output_surface_module,
        "notify_operator",
        lambda message, **kwargs: calls.append((message, kwargs)) or True,
    )

    emit_surface_render(
        db,
        surface_id="analytics.insights",
        user_id=user.user_id,
        content_snapshot={"private": "dashboard insight copy"},
        content_template_id="insights",
    )

    assert calls == []


def test_rule11_no_nudge_control_is_deterministic_after_baseline(db):
    created_at = now_utc() - timedelta(days=30)
    user = User(
        email=f"rule11-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        created_at=created_at,
    )
    db.add(user)
    db.flush()

    control_day = None
    for offset in range(8, 60):
        eligible_at = created_at + timedelta(days=offset)
        if rule11_no_nudge_control_active(
            db,
            user_id=user.user_id,
            surface_id="analytics.insights",
            eligible_at=eligible_at,
        ):
            control_day = eligible_at
            break

    assert control_day is not None
    assert rule11_no_nudge_control_active(
        db,
        user_id=user.user_id,
        surface_id="analytics.insights",
        eligible_at=control_day,
    )
    assert not rule11_no_nudge_control_active(
        db,
        user_id=user.user_id,
        surface_id="academic.pressure_map",
        eligible_at=control_day,
    )
    arm, policy = rule11_randomization_fields(
        db,
        user_id=user.user_id,
        surface_id="analytics.insights",
        eligible_at=control_day,
    )
    assert arm == RULE11_CONTROL_ARM
    assert policy == RULE11_POLICY_VERSION


def test_rule11_control_does_not_activate_during_baseline_week(db):
    created_at = now_utc() - timedelta(days=3)
    user = User(
        email=f"rule11-baseline-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        created_at=created_at,
    )
    db.add(user)
    db.flush()

    for offset in range(0, 7):
        assert not rule11_no_nudge_control_active(
            db,
            user_id=user.user_id,
            surface_id="analytics.insights",
            eligible_at=created_at + timedelta(days=offset),
        )
    arm, policy = rule11_randomization_fields(
        db,
        user_id=user.user_id,
        surface_id="analytics.insights",
        eligible_at=created_at + timedelta(days=3),
    )
    assert arm == RULE11_ACTIVE_ARM
    assert policy == RULE11_POLICY_VERSION


def test_render_ack_is_idempotent_and_owned_by_exposure_user(db):
    user_a = User(email=f"ack-a-{uuid4()}@example.com", timezone="Africa/Cairo")
    user_b = User(email=f"ack-b-{uuid4()}@example.com", timezone="Africa/Cairo")
    db.add_all([user_a, user_b])
    db.flush()

    emitted = emit_surface_render(
        db,
        surface_id="analytics.insights",
        user_id=user_a.user_id,
        content_snapshot={"kind": "insights"},
    )

    ack1, created1 = acknowledge_surface_render(
        db,
        exposure_id=emitted["exposure_id"],
        user_id=user_a.user_id,
        client_event_id="client-render-1",
    )
    ack2, created2 = acknowledge_surface_render(
        db,
        exposure_id=emitted["exposure_id"],
        user_id=user_a.user_id,
        client_event_id="client-render-retry",
    )

    assert created1 is True
    assert created2 is False
    assert ack2.ack_id == ack1.ack_id
    assert (
        db.query(ExposureAckEvent)
        .filter(ExposureAckEvent.exposure_id == emitted["exposure_id"])
        .count()
    ) == 1

    with pytest.raises(PermissionError, match="exposure_ack_wrong_user"):
        acknowledge_surface_render(
            db,
            exposure_id=emitted["exposure_id"],
            user_id=user_b.user_id,
        )


def test_render_ack_rejects_suppressed_exposures(db):
    user = User(email=f"ack-suppressed-{uuid4()}@example.com", timezone="Africa/Cairo")
    db.add(user)
    db.flush()

    suppressed = emit_surface_suppression(
        db,
        surface_id="analytics.insights",
        user_id=user.user_id,
        suppression_reason="insufficient_clean_samples",
    )

    with pytest.raises(ValueError, match="exposure_decision_not_rendered"):
        acknowledge_surface_render(
            db,
            exposure_id=suppressed["exposure_id"],
            user_id=user.user_id,
        )


def test_render_ack_endpoint_retries_without_duplicate_rows(db, client):
    user = User(email=f"ack-endpoint-{uuid4()}@example.com", timezone="Africa/Cairo")
    db.add(user)
    db.flush()
    emitted = emit_surface_render(
        db,
        surface_id="analytics.insights",
        user_id=user.user_id,
        content_snapshot={"kind": "endpoint"},
    )
    db.commit()

    path = f"/v1/exposures/{emitted['exposure_id']}/ack/render"
    first = client.post(path, json={"client_event_id": "render-1"}, headers=auth_headers(user.user_id))
    second = client.post(path, json={"client_event_id": "render-retry"}, headers=auth_headers(user.user_id))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert second.json()["ack_id"] == first.json()["ack_id"]
    assert (
        db.query(ExposureAckEvent)
        .filter(ExposureAckEvent.exposure_id == emitted["exposure_id"])
        .count()
    ) == 1


def test_render_ack_endpoint_rejects_cross_account_forgery(db, client):
    owner = User(email=f"ack-owner-{uuid4()}@example.com", timezone="Africa/Cairo")
    other = User(email=f"ack-other-{uuid4()}@example.com", timezone="Africa/Cairo")
    db.add_all([owner, other])
    db.flush()
    emitted = emit_surface_render(
        db,
        surface_id="analytics.insights",
        user_id=owner.user_id,
        content_snapshot={"kind": "owner"},
    )
    db.commit()

    response = client.post(
        f"/v1/exposures/{emitted['exposure_id']}/ack/render",
        json={},
        headers=auth_headers(other.user_id),
    )

    # Through the HTTP path, row-level scoping may hide the other user's
    # decision before the ownership check can return 403. Either way, the
    # cross-account ack is fail-closed and creates no row.
    assert response.status_code in {403, 404}
    assert (
        db.query(ExposureAckEvent)
        .filter(ExposureAckEvent.exposure_id == emitted["exposure_id"])
        .count()
    ) == 0


def test_existing_decision_suppression_is_idempotent(db):
    user = User(email=f"suppress-existing-{uuid4()}@example.com", timezone="Africa/Cairo")
    db.add(user)
    db.flush()
    old_stamp = datetime.utcnow() - timedelta(days=30)
    decision = create_output_surface_decision(
        db,
        surface_id="task.creation_nudge",
        user_id=user.user_id,
        decision_status="delivered",
        eligible_at=old_stamp,
        content_template_id="task_creation_nudge_lookup",
        trigger_source="analytics.bias_factor.lookup",
        delivered_at=old_stamp,
    )
    decision.created_at = old_stamp
    db.commit()

    first, first_created, first_status = suppress_existing_surface_decision(
        db,
        exposure_id=decision.exposure_id,
        user_id=user.user_id,
        suppression_reason="client_discarded_before_render",
        suppressed_at=old_stamp,
    )
    second, second_created, second_status = suppress_existing_surface_decision(
        db,
        exposure_id=decision.exposure_id,
        user_id=user.user_id,
        suppression_reason="client_discarded_before_render",
        suppressed_at=old_stamp,
    )
    db.commit()

    assert first is not None
    assert second is not None
    assert first_created is True
    assert second_created is False
    assert first_status == "suppressed"
    assert second_status == "already_suppressed"
    assert second.suppression_id == first.suppression_id
    assert (
        db.query(ExposureDecisionEvent)
        .filter(ExposureDecisionEvent.exposure_id == decision.exposure_id)
        .one()
        .decision_status
    ) == "suppressed"
    assert (
        db.query(SuppressionEvent)
        .filter(SuppressionEvent.exposure_id == decision.exposure_id)
        .count()
    ) == 1


def test_existing_decision_suppression_endpoint_rejects_rendered_decision(db, client):
    user = User(email=f"suppress-rendered-{uuid4()}@example.com", timezone="Africa/Cairo")
    db.add(user)
    db.flush()
    emitted = emit_surface_render(
        db,
        surface_id="task.creation_nudge",
        user_id=user.user_id,
        content_snapshot={"kind": "rendered"},
    )
    db.commit()

    response = client.post(
        f"/v1/exposures/{emitted['exposure_id']}/ack/suppress",
        json={"suppression_reason": "client_discarded_before_render"},
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200
    assert response.json()["created"] is False
    assert response.json()["status"] == "already_rendered"
    assert (
        db.query(SuppressionEvent)
        .filter(SuppressionEvent.exposure_id == emitted["exposure_id"])
        .count()
    ) == 0


def test_existing_decision_suppression_endpoint_rejects_cross_account(db, client):
    owner = User(email=f"suppress-owner-{uuid4()}@example.com", timezone="Africa/Cairo")
    other = User(email=f"suppress-other-{uuid4()}@example.com", timezone="Africa/Cairo")
    db.add_all([owner, other])
    db.flush()
    old_stamp = datetime.utcnow() - timedelta(days=30)
    decision = create_output_surface_decision(
        db,
        surface_id="task.creation_nudge",
        user_id=owner.user_id,
        decision_status="delivered",
        eligible_at=old_stamp,
        content_template_id="task_creation_nudge_lookup",
        trigger_source="analytics.bias_factor.lookup",
        delivered_at=old_stamp,
    )
    decision.created_at = old_stamp
    db.commit()

    response = client.post(
        f"/v1/exposures/{decision.exposure_id}/ack/suppress",
        json={"suppression_reason": "client_discarded_before_render"},
        headers=auth_headers(other.user_id),
    )

    assert response.status_code in {403, 404}
    assert (
        db.query(SuppressionEvent)
        .filter(SuppressionEvent.exposure_id == decision.exposure_id)
        .count()
    ) == 0


def test_unregistered_output_surface_hard_fails():
    with pytest.raises(ValueError, match="unregistered_output_surface"):
        get_output_surface_spec("missing.surface")


def test_missing_mixed_row_projection_fails_closed():
    with pytest.raises(ValueError, match="missing_projection_for_profile"):
        projection_class_for_profile("unknown_future_profile")


def test_unregistered_surface_cannot_emit_render_or_suppression(db):
    user = User(email=f"missing-surface-{uuid4()}@example.com", timezone="Africa/Cairo")
    db.add(user)
    db.flush()

    with pytest.raises(ValueError, match="unregistered_output_surface"):
        emit_surface_render(
            db,
            surface_id="missing.surface",
            user_id=user.user_id,
            content_snapshot={"kind": "missing"},
        )

    with pytest.raises(ValueError, match="unregistered_output_surface"):
        emit_surface_suppression(
            db,
            surface_id="missing.surface",
            user_id=user.user_id,
            suppression_reason="unregistered_surface",
        )


def test_emit_surface_suppression_writes_decision_and_suppression(db):
    user = User(email=f"suppressed-surface-{uuid4()}@example.com", timezone="Africa/Cairo")
    db.add(user)
    db.flush()

    emitted = emit_surface_suppression(
        db,
        surface_id="analytics.insights",
        user_id=user.user_id,
        suppression_reason="insufficient_clean_samples",
        content_template_id="insights_empty",
        randomization_arm=RULE11_CONTROL_ARM,
        randomization_policy_version=RULE11_POLICY_VERSION,
    )
    db.commit()

    decision = (
        db.query(ExposureDecisionEvent)
        .filter(ExposureDecisionEvent.exposure_id == emitted["exposure_id"])
        .one()
    )
    suppression = (
        db.query(SuppressionEvent)
        .filter(SuppressionEvent.suppression_id == emitted["suppression_id"])
        .one()
    )

    assert emitted["truth_class"] == "interpretation"
    assert emitted["usage_class"] == "product"
    assert emitted["fallback_mode"] == "empty"
    assert decision.decision_status == "suppressed"
    assert decision.delivered_at is None
    assert decision.exposure_category == "behavioral_insight"
    assert decision.randomization_arm == RULE11_CONTROL_ARM
    assert decision.randomization_policy_version == RULE11_POLICY_VERSION
    assert suppression.suppression_reason == "insufficient_clean_samples"
    assert suppression.would_have_rendered_template_id == "insights_empty"


def test_operator_only_surfaces_reject_non_operator_users(db, monkeypatch):
    user = User(email=f"non-operator-{uuid4()}@example.com", timezone="Africa/Cairo")
    db.add(user)
    db.flush()
    spec = OutputSurfaceSpec(
        surface_id="operator.diagnostic",
        truth_class="diagnostic_only",
        usage_class="operator",
        channel="dashboard_page",
        exposure_category="meta_inference",
        signal_targets=("operator_orchestration",),
        clean_profile=None,
        min_n=0,
        time_window_days=None,
        fallback_mode="suppress",
        operator_only=True,
        legacy_adapter=None,
        render_policy_version="output_surface_registry_v1",
        interruptiveness="passive",
        salience_level="low",
    )
    monkeypatch.setattr(
        output_surface_module,
        "load_output_surface_registry",
        lambda: {"operator.diagnostic": spec},
    )

    with pytest.raises(PermissionError, match="operator_only_output_surface"):
        emit_surface_render(
            db,
            surface_id="operator.diagnostic",
            user_id=user.user_id,
            content_snapshot={"kind": "diagnostic"},
        )


def test_app_code_does_not_bypass_output_surface_emitter():
    allowed_direct_exposure_writers = {
        Path("app/services/exposure_ledger.py"),
        Path("app/services/output_surfaces.py"),
    }
    forbidden_tokens = (
        "record_decision(",
        "record_render(",
        "record_suppression(",
    )

    offenders: list[str] = []
    for path in Path("app").rglob("*.py"):
        if path in allowed_direct_exposure_writers:
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                offenders.append(f"{path}:{token}")

    assert offenders == []


def test_app_code_does_not_create_legacy_reflection_rows_directly():
    allowed_legacy_writers = {
        Path("app/db/models.py"),
        Path("app/services/output_surfaces.py"),
    }

    offenders: list[str] = []
    for path in Path("app").rglob("*.py"):
        if path in allowed_legacy_writers:
            continue
        if "ReflectionViewLog(" in path.read_text(encoding="utf-8"):
            offenders.append(str(path))

    assert offenders == []


def test_product_surfaces_do_not_fall_back_to_operator_without_identity():
    """Regression for Wave 0: anonymous product reads must fail closed."""

    old_overrides = dict(app.dependency_overrides)
    app.dependency_overrides.pop(get_db, None)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            for path in (
                "/v1/users/me",
                "/v1/analytics/insights",
                "/v1/analytics/archetype/proximity?days=14",
                "/v1/analytics/bias_factor/lookup?category=development&tod=morning&planned_minutes=60",
            ):
                response = client.get(path)
                assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(old_overrides)


def test_task_creation_nudge_lookup_emits_exposure_when_it_will_render(db):
    user = User(
        email=f"creation-nudge-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        is_operator=False,
    )
    db.add(user)
    if db.query(Archetype).filter_by(archetype_id="diffuse_average").first() is None:
        db.add(
            Archetype(
                archetype_id="diffuse_average",
                name="Diffuse Average",
                prior_bias_factor=1.30,
                prior_sigma=0.30,
            )
        )
    db.commit()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/v1/analytics/bias_factor/lookup?category=study&tod=morning&planned_minutes=30",
            headers=auth_headers(user.user_id),
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cell"] is not None
    assert body["surface_id"] == "task.creation_nudge"
    assert body["truth_class"] == "intervention"
    assert body["signal_targets"] == ["planning_estimate", "pause_behavior"]
    assert body["clean_profile"] == "planning_calibration"
    assert body["fallback_mode"] == "suppress"
    assert body["exposure_id"]
    assert body["render_id"] is None
    assert body["execution_suggested_minutes"] >= 5
    assert body["pause_overhead_minutes"] == 0
    assert body["occupancy_suggested_minutes"] == body["execution_suggested_minutes"]

    decision = (
        db.query(ExposureDecisionEvent)
        .filter(ExposureDecisionEvent.exposure_id == body["exposure_id"])
        .one()
    )
    assert decision.user_id == user.user_id
    assert decision.decision_status == "delivered"
    assert decision.exposure_category == "scheduling_suggestion"
    assert decision.trigger_source == "analytics.bias_factor.lookup"

    assert (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.exposure_id == body["exposure_id"])
        .first()
        is None
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        ack_response = client.post(
            f"/v1/exposures/{body['exposure_id']}/ack/render",
            headers=auth_headers(user.user_id),
            json={
                "surface_id": "task.creation_nudge",
                "content_snapshot": {
                    "template": "task_creation_nudge_lookup",
                    "category": "study",
                    "planned_minutes": 30,
                    "suggested_minutes": body["occupancy_suggested_minutes"],
                    "execution_suggested_minutes": body["execution_suggested_minutes"],
                    "pause_overhead_minutes": body["pause_overhead_minutes"],
                    "occupancy_suggested_minutes": body["occupancy_suggested_minutes"],
                    "personal_weight": body["personal_weight"],
                    "prior_weight": body["prior_weight"],
                },
            },
        )

    assert ack_response.status_code == 200, ack_response.text
    render = (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.exposure_id == body["exposure_id"])
        .one()
    )
    assert render.surface == "task.creation_nudge"
    assert "task_creation_nudge_lookup" in render.content_snapshot
    assert "execution_suggested_minutes" in render.content_snapshot
    assert "pause_overhead_minutes" in render.content_snapshot
    assert "occupancy_suggested_minutes" in render.content_snapshot
    assert "personal_weight" in render.content_snapshot
    assert "prior_weight" in render.content_snapshot


def test_task_creation_nudge_lookup_prefilters_to_requested_category(db, monkeypatch):
    user = User(
        email=f"creation-nudge-prefilter-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        is_operator=False,
    )
    db.add(user)
    db.flush()

    base = datetime.utcnow() - timedelta(days=3)
    for idx in range(8):
        task = Task(
            task_id=str(uuid4()),
            title=f"work-history-{idx}",
            planned_start_utc=base + timedelta(hours=idx),
            planned_end_utc=base + timedelta(hours=idx, minutes=60),
            planned_duration_minutes=60,
            executed_start_utc=base + timedelta(hours=idx),
            executed_end_utc=base + timedelta(hours=idx, minutes=75),
            executed_duration_minutes=75,
            state=TaskState.EXECUTED,
            source=TaskSource.MANUAL,
            user_id=user.user_id,
            category="work",
        )
        db.add(task)
        db.flush()
        db.add(
            StopwatchSession(
                session_id=str(uuid4()),
                task_id=task.task_id,
                user_id=user.user_id,
                start_time_utc=task.executed_start_utc,
                end_time_utc=task.executed_end_utc,
                total_paused_minutes=0.0,
                auto_closed=False,
                data_quality_flag=None,
            )
        )
    db.commit()

    captured: dict[str, list[str]] = {}

    def fake_blend(_db, _user_id, tasks, category, _tod, planned_minutes):
        captured["categories"] = [task.category for task in tasks]
        return {
            "cell": {
                "bias_factor": 1.0,
                "bias_factor_mean": 1.0,
                "sessions": len(tasks),
                "confidence": "low",
                "interpretation": "on target",
                "category": category,
                "time_of_day": "morning",
                "citation": "test",
            },
            "sessions": len(tasks),
            "min_sessions": 3,
            "source": "research",
            "signal_level": "research",
            "signals": [],
            "bias_factor_final": 1.0,
            "personal_weight": 0.0,
            "prior_weight": 1.0,
            "archetype_id": "diffuse_average",
            "archetype_prior_bias_factor": 1.3,
            "archetype_prior_for_cell": 1.0,
            "archetype_scaling": 1.0,
            "archetype_prior_citation": "test",
            "execution_suggested_minutes": planned_minutes,
            "pause_overhead_minutes": 0,
            "pause_overhead_sample_size": 0,
            "occupancy_suggested_minutes": planned_minutes,
            "occupancy_strategy": "execution_only_research_prior",
            "occupancy_factor": 1.0,
        }

    monkeypatch.setattr("app.services.bias_factor_service.blend", fake_blend)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/v1/analytics/bias_factor/lookup?category=study&tod=morning&planned_minutes=30",
            headers=auth_headers(user.user_id),
        )

    assert response.status_code == 200, response.text
    assert captured["categories"] == []


def test_task_creation_nudge_lookup_dedupes_identical_rapid_calls(db):
    user = User(
        email=f"creation-nudge-dedupe-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        is_operator=False,
    )
    db.add(user)
    if db.query(Archetype).filter_by(archetype_id="diffuse_average").first() is None:
        db.add(
            Archetype(
                archetype_id="diffuse_average",
                name="Diffuse Average",
                prior_bias_factor=1.30,
                prior_sigma=0.30,
            )
        )
    db.commit()

    path = "/v1/analytics/bias_factor/lookup?category=study&tod=morning&planned_minutes=30"
    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.get(path, headers=auth_headers(user.user_id))
        second = client.get(path, headers=auth_headers(user.user_id))

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    first_body = first.json()
    second_body = second.json()
    assert first_body["exposure_id"] == second_body["exposure_id"]
    assert first_body["render_id"] == second_body["render_id"]
    assert (
        db.query(ExposureDecisionEvent)
        .filter(ExposureDecisionEvent.user_id == user.user_id)
        .count()
        == 1
    )
    assert (
        db.query(ExposureRenderEvent)
        .join(
            ExposureDecisionEvent,
            ExposureDecisionEvent.exposure_id == ExposureRenderEvent.exposure_id,
        )
        .filter(ExposureDecisionEvent.user_id == user.user_id)
        .count()
        == 0
    )


def test_task_creation_nudge_fast_lookup_can_hydrate_full_pause_overhead(db):
    user = User(
        email=f"creation-nudge-hydrate-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        is_operator=False,
    )
    db.add(user)
    if db.query(Archetype).filter_by(archetype_id="diffuse_average").first() is None:
        db.add(
            Archetype(
                archetype_id="diffuse_average",
                name="Diffuse Average",
                prior_bias_factor=1.30,
                prior_sigma=0.30,
            )
        )
    db.flush()

    base = datetime(2026, 6, 1, 6, 0)
    for idx, pause in enumerate([0.0, 20.0, 40.0]):
        start = base + timedelta(days=idx)
        task = Task(
            task_id=str(uuid4()),
            title=f"hydrate-study-{idx}",
            planned_start_utc=start,
            planned_end_utc=start + timedelta(minutes=60),
            planned_duration_minutes=60,
            executed_start_utc=start,
            executed_end_utc=start + timedelta(minutes=90),
            executed_duration_minutes=90,
            state=TaskState.EXECUTED,
            source=TaskSource.MANUAL,
            user_id=user.user_id,
            category="study",
            initiation_status="initiated",
        )
        db.add(task)
        db.flush()
        db.add(
            StopwatchSession(
                session_id=str(uuid4()),
                task_id=task.task_id,
                user_id=user.user_id,
                start_time_utc=task.executed_start_utc,
                end_time_utc=task.executed_start_utc
                + timedelta(minutes=90 + int(pause)),
                total_paused_minutes=pause,
                auto_closed=False,
                data_quality_flag=None,
            )
        )
    db.commit()

    exposure_id = str(uuid4())
    fast_path = (
        "/v1/analytics/bias_factor/lookup?category=study&tod=morning"
        f"&planned_minutes=60&fast=true&exposure_id={exposure_id}"
    )
    full_path = (
        "/v1/analytics/bias_factor/lookup?category=study&tod=morning"
        f"&planned_minutes=60&exposure_id={exposure_id}"
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        fast_response = client.get(fast_path, headers=auth_headers(user.user_id))
        full_response = client.get(full_path, headers=auth_headers(user.user_id))

    assert fast_response.status_code == 200, fast_response.text
    assert full_response.status_code == 200, full_response.text
    fast_body = fast_response.json()
    full_body = full_response.json()

    assert fast_body["source"] == "research"
    assert fast_body["pause_overhead_sample_size"] == 0
    assert fast_body["pause_overhead_minutes"] == 0
    assert full_body["source"] == "personal"
    assert full_body["pause_overhead_sample_size"] == 3
    assert full_body["pause_overhead_minutes"] == 20
    assert full_body["occupancy_suggested_minutes"] == (
        full_body["execution_suggested_minutes"] + 20
    )
    assert full_body["exposure_id"] == fast_body["exposure_id"] == exposure_id
    assert (
        db.query(ExposureDecisionEvent)
        .filter(ExposureDecisionEvent.exposure_id == exposure_id)
        .count()
        == 1
    )


def test_task_creation_nudge_lookup_excludes_dirty_personal_rows(db):
    user = User(
        email=f"creation-nudge-dirty-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        is_operator=False,
    )
    db.add(user)
    if db.query(Archetype).filter_by(archetype_id="diffuse_average").first() is None:
        db.add(
            Archetype(
                archetype_id="diffuse_average",
                name="Diffuse Average",
                prior_bias_factor=1.30,
                prior_sigma=0.30,
            )
        )
    db.flush()

    base = datetime.utcnow() - timedelta(days=2)
    for idx in range(5):
        task = Task(
            task_id=str(uuid4()),
            title=f"dirty-study-{idx}",
            planned_start_utc=base + timedelta(hours=idx),
            planned_end_utc=base + timedelta(hours=idx, minutes=30),
            planned_duration_minutes=30,
            executed_start_utc=base + timedelta(hours=idx),
            executed_end_utc=base + timedelta(hours=idx, minutes=180),
            executed_duration_minutes=180,
            state=TaskState.EXECUTED,
            source=TaskSource.MANUAL,
            user_id=user.user_id,
            category="study",
        )
        db.add(task)
        db.flush()
        db.add(
            StopwatchSession(
                session_id=str(uuid4()),
                task_id=task.task_id,
                user_id=user.user_id,
                start_time_utc=task.executed_start_utc,
                end_time_utc=task.executed_end_utc,
                total_paused_minutes=0.0,
                auto_closed=False,
                data_quality_flag="user_resolved_stale_pause",
            )
        )
    db.commit()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/v1/analytics/bias_factor/lookup?category=study&tod=morning&planned_minutes=30",
            headers=auth_headers(user.user_id),
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "research"
    assert body["cell"]["sessions"] == 0
    assert body["personal_weight"] == 0.0


def test_task_creation_nudge_lookup_suppresses_if_exposure_logging_fails(db, monkeypatch):
    user = User(
        email=f"creation-nudge-fail-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        is_operator=False,
    )
    db.add(user)
    if db.query(Archetype).filter_by(archetype_id="diffuse_average").first() is None:
        db.add(
            Archetype(
                archetype_id="diffuse_average",
                name="Diffuse Average",
                prior_bias_factor=1.30,
                prior_sigma=0.30,
            )
        )
    db.commit()

    def boom(*_args, **_kwargs):
        raise RuntimeError("ledger unavailable")

    monkeypatch.setattr("app.api.v1.endpoints.analytics.create_output_surface_decision", boom)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/v1/analytics/bias_factor/lookup?category=study&tod=morning&planned_minutes=30",
            headers=auth_headers(user.user_id),
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cell"] is None
    assert body["surface_id"] == "task.creation_nudge"
    assert body["suppressed_reason"] == "exposure_emit_failed"


def test_output_surface_diagnostics_reports_missing_terminal_event(db):
    user = User(
        email=f"surface-diagnostics-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        is_operator=True,
    )
    db.add(user)
    db.flush()

    rendered = emit_surface_render(
        db,
        surface_id="stopwatch.micro_mirror",
        user_id=user.user_id,
        content_snapshot={"kind": "micro_mirror"},
        create_legacy_view=True,
        legacy_payload={"kind": "micro_mirror"},
    )
    dangling = ExposureDecisionEvent(
        exposure_id=str(uuid4()),
        user_id=user.user_id,
        eligible_at=now_utc(),
        decision_status="rendered",
        initiative="system",
        exposure_category="behavioral_insight",
        content_template_id="analytics_insights",
        trigger_source="analytics.insights",
    )
    db.add(dangling)
    db.commit()

    diagnostics = output_surface_diagnostics(
        db,
        user_id=user.user_id,
        window_days=30,
    )

    assert diagnostics["schema_version"] == "output_surface_diagnostics_v1"
    assert diagnostics["registry"]["unregistered_render_surfaces"] == []
    assert diagnostics["dual_write"]["decision_without_terminal_event_count"] == 1
    assert dangling.exposure_id in diagnostics["dual_write"]["decision_without_terminal_event_ids"]
    assert diagnostics["dual_write"]["surface_activity"]["stopwatch.micro_mirror"]["renders"] == 1
    assert rendered["legacy_view_id"] is not None
    micro_mirror = {
        row["surface_id"]: row
        for row in diagnostics["legacy_adapter_reliance"]
    }["stopwatch.micro_mirror"]
    assert micro_mirror["legacy_rows"] == 1
    assert micro_mirror["v0_renders"] == 1
    assert micro_mirror["parity_delta"] == 0


def test_output_surface_diagnostics_reuses_eligibility_metrics(db, monkeypatch):
    user = User(
        email=f"surface-diagnostics-cache-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        is_operator=True,
    )
    db.add(user)
    db.commit()

    calls = []

    def fake_metrics(_db, *, clean_profile, signal_targets, user_id, cutoff):
        calls.append((clean_profile, tuple(signal_targets)))
        assert user_id == user.user_id
        assert cutoff is not None
        return {
            "projection_class": "fake_projection",
            "candidate_n": 42,
            "clean_n": 2,
            "contaminated_n": 40,
            "unknown_n": 0,
            "exposed_n": 0,
            "intervention_n": 0,
            "state_counts": {},
            "missing_projection": None,
        }

    monkeypatch.setattr(
        output_surface_module,
        "_eligibility_metrics_for_surface_inputs",
        fake_metrics,
    )

    diagnostics = output_surface_diagnostics(
        db,
        user_id=user.user_id,
        window_days=30,
    )

    registry = load_output_surface_registry()
    expected_keys = {
        (spec.clean_profile, tuple(spec.signal_targets))
        for spec in registry.values()
        if spec.truth_class in {"interpretation", "intervention"}
    }
    expected_surface_count = sum(
        1
        for spec in registry.values()
        if spec.truth_class in {"interpretation", "intervention"}
    )
    assert set(calls) == expected_keys
    assert len(calls) == len(expected_keys)
    assert len(diagnostics["current_data_eligibility"]) == expected_surface_count
    assert all(
        row["candidate_n"] == 42
        for row in diagnostics["current_data_eligibility"]
    )


def test_output_surface_diagnostics_endpoint_is_operator_only(db, client):
    operator = User(
        email=f"surface-operator-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        is_operator=True,
    )
    non_operator = User(
        email=f"surface-non-operator-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        is_operator=False,
    )
    db.add_all([operator, non_operator])
    db.commit()

    denied = client.get(
        "/v1/analytics/output_surfaces/diagnostics",
        headers=auth_headers(non_operator.user_id),
    )
    assert denied.status_code == 403

    allowed = client.get(
        "/v1/analytics/output_surfaces/diagnostics?window_days=30",
        headers=auth_headers(operator.user_id),
    )
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["schema_version"] == "output_surface_diagnostics_v1"
    assert body["registry"]["registered_surface_count"] >= 8
    assert "current_data_eligibility" in body
