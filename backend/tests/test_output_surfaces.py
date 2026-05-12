import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.db.models import (
    ExposureDecisionEvent,
    ExposureRenderEvent,
    ReflectionViewLog,
    SuppressionEvent,
    User,
)
from app.main import app
from app.services import output_surfaces as output_surface_module
from app.services.output_surfaces import (
    OutputSurfaceSpec,
    emit_surface_render,
    emit_surface_suppression,
    get_output_surface_spec,
    load_output_surface_registry,
    output_surface_diagnostics,
    projection_class_for_profile,
)
from app.utils.time_utils import now_utc
from tests.conftest import auth_headers


def test_output_surface_registry_declares_required_runtime_fields():
    registry = load_output_surface_registry()
    first_wave_surfaces = {
        "stopwatch.micro_mirror",
        "stopwatch.calibration_nudge",
        "task.creation_nudge",
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

    assert emitted["truth_class"] == "metric"
    assert emitted["usage_class"] == "product"
    assert emitted["fallback_mode"] == "empty"
    assert decision.decision_status == "suppressed"
    assert decision.delivered_at is None
    assert decision.exposure_category == "behavioral_insight"
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
