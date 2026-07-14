"""Exposure Ledger v0 contract tests.

The ledger is a causal firewall for baseline inference. These tests protect
the fail-closed rule: missing or incomplete exposure context must never become
clean baseline by accident.
"""
from datetime import datetime, timedelta

from app.db.models import (
    CalibrationNudgeEvent,
    ExposureDecisionEvent,
    ExposurePolicyEffectLog,
    ExposureRenderEvent,
    PausePredictionLog,
    ReflectionViewLog,
    ResumePredictionLog,
    SuppressionEvent,
    Task,
    TaskState,
    User,
)
from app.services.cortex import measured_execution_baseline_tasks
from app.services import exposure_ledger
from app.services.exposure_ledger import (
    affected_categories_for_target,
    baseline_clean_task,
    baseline_clean_task_ids,
    classify_exposure_terminal_state,
    is_exposed,
    load_horizon_policy,
    record_decision,
    record_policy_effect_snapshot,
    record_render,
    record_suppression,
)


def _clean(db):
    for model in (
        ExposurePolicyEffectLog,
        SuppressionEvent,
        ExposureRenderEvent,
        ExposureDecisionEvent,
        ReflectionViewLog,
        CalibrationNudgeEvent,
        PausePredictionLog,
        ResumePredictionLog,
        Task,
        User,
    ):
        db.query(model).delete()
    db.commit()


def _user(db, user_id: int = 7101):
    user = User(user_id=user_id, email=f"exposure-{user_id}@example.test")
    db.add(user)
    db.commit()
    return user


def test_exposure_terminal_classifier_preserves_diagnostic_boundaries():
    rendered = classify_exposure_terminal_state(
        decision_status="shown",
        has_render=True,
        has_suppression=False,
    )
    suppressed = classify_exposure_terminal_state(
        decision_status="shown",
        has_render=False,
        has_suppression=True,
    )
    queued = classify_exposure_terminal_state(
        decision_status="queued",
        has_render=False,
        has_suppression=False,
    )
    suppressed_status_without_row = classify_exposure_terminal_state(
        decision_status="suppressed",
        has_render=False,
        has_suppression=False,
    )
    failed = classify_exposure_terminal_state(
        decision_status="failed",
        has_render=False,
        has_suppression=False,
    )
    reserved = classify_exposure_terminal_state(
        decision_status="reserved",
        has_render=False,
        has_suppression=False,
    )
    actionable = classify_exposure_terminal_state(
        decision_status="shown",
        has_render=False,
        has_suppression=False,
    )

    assert rendered.state == "rendered"
    assert rendered.has_terminal_event is True
    assert rendered.is_actionable_missing_render is False

    assert suppressed.state == "suppressed"
    assert suppressed.has_terminal_event is True
    assert suppressed.is_actionable_missing_render is False

    assert queued.state == "queued_without_render"
    assert queued.has_terminal_event is False
    assert queued.is_actionable_missing_render is False

    assert suppressed_status_without_row.state == "suppressed"
    assert suppressed_status_without_row.has_terminal_event is False
    assert suppressed_status_without_row.is_actionable_missing_render is False

    assert failed.state == "non_actionable_without_render"
    assert failed.has_terminal_event is False
    assert failed.is_actionable_missing_render is False

    assert reserved.state == "non_actionable_without_render"
    assert reserved.has_terminal_event is False
    assert reserved.is_actionable_missing_render is False

    assert actionable.state == "actionable_missing_render"
    assert actionable.has_terminal_event is False
    assert actionable.is_actionable_missing_render is True


def test_horizon_policy_loaded_from_versioned_config(db):
    _clean(db)
    policy = load_horizon_policy("exposure_horizon_v0")

    assert policy["version"] == "exposure_horizon_v0"
    assert affected_categories_for_target(policy, "planning_estimate") == {
        "behavioral_insight": 4320,
        "scheduling_suggestion": 1440,
        "repair_prompt": 1440,
        "onboarding": 20160,
    }


def test_no_relevant_exposure_returns_none(db):
    _clean(db)
    user = _user(db)
    event_time = datetime(2026, 5, 9, 12, 0, 0)

    result = is_exposed(
        db,
        user_id=user.user_id,
        event_time=event_time,
        signal_target="duration_behavior",
    )

    assert result.state == "NONE"
    assert result.baseline_clean is True
    assert result.unknown_reason is None


def test_rendered_relevant_exposure_returns_exposed(db):
    _clean(db)
    user = _user(db)
    event_time = datetime(2026, 5, 9, 12, 0, 0)
    decision = record_decision(
        db,
        user_id=user.user_id,
        eligible_at=event_time - timedelta(hours=1),
        decision_status="shown",
        exposure_category="behavioral_insight",
        content_template_id="overrun-summary",
    )
    record_render(
        db,
        exposure_id=decision.exposure_id,
        rendered_at=event_time - timedelta(hours=1),
        surface="insights",
        channel="web",
        content_snapshot="You overran similar tasks by 47.3 minutes.",
        render_policy_version="render_v0",
        interruptiveness="inline",
        salience_level="medium",
    )
    db.commit()

    result = is_exposed(
        db,
        user_id=user.user_id,
        event_time=event_time,
        signal_target="duration_behavior",
    )

    assert result.state == "EXPOSED"
    assert result.baseline_clean is False
    assert result.exposure_ids == [decision.exposure_id]
    assert result.policy_effect_reason == "render_event_in_policy_horizon_attention_unconfirmed"


def test_decision_without_render_or_suppression_returns_unknown(db):
    _clean(db)
    user = _user(db)
    event_time = datetime(2026, 5, 9, 12, 0, 0)
    record_decision(
        db,
        user_id=user.user_id,
        eligible_at=event_time - timedelta(hours=1),
        decision_status="shown",
        exposure_category="behavioral_insight",
        content_template_id="overrun-summary",
    )
    db.commit()

    result = is_exposed(
        db,
        user_id=user.user_id,
        event_time=event_time,
        signal_target="duration_behavior",
    )

    assert result.state == "UNKNOWN"
    assert result.unknown_reason == "ledger_incomplete"
    assert result.baseline_clean is False


def test_suppressed_decision_does_not_count_as_user_exposure(db):
    _clean(db)
    user = _user(db)
    event_time = datetime(2026, 5, 9, 12, 0, 0)
    decision = record_decision(
        db,
        user_id=user.user_id,
        eligible_at=event_time - timedelta(hours=1),
        decision_status="suppressed",
        exposure_category="behavioral_insight",
        content_template_id="overrun-summary",
    )
    record_suppression(
        db,
        exposure_id=decision.exposure_id,
        suppressed_at=event_time - timedelta(hours=1),
        suppression_reason="cooldown",
        would_have_rendered_template_id="overrun-summary",
    )
    db.commit()

    result = is_exposed(
        db,
        user_id=user.user_id,
        event_time=event_time,
        signal_target="duration_behavior",
    )

    assert result.state == "NONE"
    assert result.policy_effect_reason == "no_relevant_exposure_within_policy_horizon"


def test_meta_system_does_not_pretend_to_gate_unmeasured_system_trust(db):
    _clean(db)
    user = _user(db)

    result = is_exposed(
        db,
        user_id=user.user_id,
        event_time=datetime(2026, 5, 9, 12, 0, 0),
        signal_target="system_trust",
    )

    assert result.state == "UNKNOWN"
    assert result.unknown_reason == "unsupported_or_unmeasured_signal_target"


def test_policy_unavailable_fails_closed(monkeypatch, db):
    _clean(db)
    user = _user(db)

    def broken_policy(_version):
        raise FileNotFoundError("policy missing")

    monkeypatch.setattr(exposure_ledger, "load_horizon_policy", broken_policy)

    result = is_exposed(
        db,
        user_id=user.user_id,
        event_time=datetime(2026, 5, 9, 12, 0, 0),
        signal_target="duration_behavior",
    )

    assert result.state == "UNKNOWN"
    assert result.unknown_reason == "policy_unavailable"


def test_legacy_reflection_impression_maps_to_exposure(db):
    _clean(db)
    user = _user(db)
    event_time = datetime(2026, 5, 9, 12, 0, 0)
    db.add(
        ReflectionViewLog(
            view_id="legacy-view-1",
            user_id=user.user_id,
            reflection_type="micro_mirror",
            event_class="impression",
            payload="You usually overrun development tasks.",
            fired_at=event_time - timedelta(hours=2),
            viewed_at=event_time - timedelta(hours=2),
        )
    )
    db.commit()

    result = is_exposed(
        db,
        user_id=user.user_id,
        event_time=event_time,
        signal_target="duration_behavior",
    )

    assert result.state == "EXPOSED"
    assert result.exposure_ids == ["legacy_reflection:legacy-view-1"]
    assert result.exposure_categories == ["behavioral_insight"]


def test_unviewed_legacy_reflection_does_not_map_to_exposure(db):
    _clean(db)
    user = _user(db)
    event_time = datetime(2026, 5, 9, 12, 0, 0)
    db.add(
        ReflectionViewLog(
            view_id="legacy-unviewed-1",
            user_id=user.user_id,
            reflection_type="micro_mirror",
            event_class="impression",
            payload="Candidate never mounted.",
            fired_at=event_time - timedelta(hours=2),
            viewed_at=None,
        )
    )
    db.commit()

    result = is_exposed(
        db,
        user_id=user.user_id,
        event_time=event_time,
        signal_target="duration_behavior",
    )

    assert result.state == "NONE"
    assert result.baseline_clean is True


def test_legacy_calibration_nudge_acceptance_maps_to_intervention(db):
    _clean(db)
    user = _user(db)
    event_time = datetime(2026, 5, 9, 12, 0, 0)
    db.add(
        CalibrationNudgeEvent(
            event_id="legacy-nudge-1",
            user_id=user.user_id,
            task_id="task-x",
            suggested_duration_minutes=90,
            user_planned_duration_minutes=60,
            bias_factor=1.5,
            sample_size=12,
            user_decision="accepted",
            decided_at=event_time - timedelta(minutes=20),
        )
    )
    db.commit()

    result = is_exposed(
        db,
        user_id=user.user_id,
        event_time=event_time,
        signal_target="planning_estimate",
    )

    assert result.state == "INTERVENTION"
    assert result.exposure_ids == ["legacy_calibration_nudge:legacy-nudge-1"]


def test_legacy_pause_prediction_maps_to_predictive_alert(db):
    _clean(db)
    user = _user(db)
    event_time = datetime(2026, 5, 9, 12, 0, 0)
    db.add(
        PausePredictionLog(
            firing_id="legacy-pause-1",
            user_id=user.user_id,
            fired_at=event_time - timedelta(minutes=10),
            predicted_at=event_time - timedelta(minutes=8),
            mechanism="clock_anchor",
            confidence=0.8,
            lead_minutes=2,
            sample_size=10,
        )
    )
    db.commit()

    result = is_exposed(
        db,
        user_id=user.user_id,
        event_time=event_time,
        signal_target="pause_behavior",
    )

    assert result.state == "EXPOSED"
    assert result.exposure_ids == ["legacy_pause_prediction:legacy-pause-1"]
    assert result.exposure_categories == ["predictive_alert"]


def test_cortex_baseline_helper_excludes_exposed_task(db):
    _clean(db)
    user = _user(db)
    start = datetime(2026, 5, 9, 12, 0, 0)
    task = Task(
        task_id="task-exposed",
        user_id=user.user_id,
        title="Exposed task",
        planned_start_utc=start,
        planned_end_utc=start + timedelta(minutes=60),
        planned_duration_minutes=60,
        executed_start_utc=start,
        executed_end_utc=start + timedelta(minutes=90),
        executed_duration_minutes=90,
        state=TaskState.EXECUTED,
        initiation_status="initiated",
    )
    db.add(task)
    decision = record_decision(
        db,
        user_id=user.user_id,
        eligible_at=start - timedelta(minutes=30),
        decision_status="shown",
        exposure_category="behavioral_insight",
        content_template_id="overrun-summary",
    )
    record_render(
        db,
        exposure_id=decision.exposure_id,
        rendered_at=start - timedelta(minutes=30),
        surface="insights",
        channel="web",
        content_snapshot="You overrun this category.",
        render_policy_version="render_v0",
        interruptiveness="inline",
        salience_level="medium",
    )
    db.commit()

    assert measured_execution_baseline_tasks(db, user_id=user.user_id) == []


def test_bulk_baseline_clean_task_ids_matches_single_row_helper(db):
    _clean(db)
    user = _user(db)
    clean_start = datetime(2026, 5, 9, 9, 0, 0)
    exposed_start = datetime(2026, 5, 9, 12, 0, 0)
    clean_task = Task(
        task_id="bulk-clean",
        user_id=user.user_id,
        title="Clean task",
        planned_start_utc=clean_start,
        planned_end_utc=clean_start + timedelta(minutes=60),
        planned_duration_minutes=60,
        executed_start_utc=clean_start,
        executed_end_utc=clean_start + timedelta(minutes=70),
        executed_duration_minutes=70,
        state=TaskState.EXECUTED,
        initiation_status="initiated",
        created_at=clean_start,
    )
    exposed_task = Task(
        task_id="bulk-exposed",
        user_id=user.user_id,
        title="Exposed task",
        planned_start_utc=exposed_start,
        planned_end_utc=exposed_start + timedelta(minutes=60),
        planned_duration_minutes=60,
        executed_start_utc=exposed_start,
        executed_end_utc=exposed_start + timedelta(minutes=80),
        executed_duration_minutes=80,
        state=TaskState.EXECUTED,
        initiation_status="initiated",
        created_at=exposed_start,
    )
    db.add_all([clean_task, exposed_task])
    record_decision(
        db,
        user_id=user.user_id,
        eligible_at=clean_start - timedelta(minutes=30),
        decision_status="reserved",
        exposure_category="scheduling_suggestion",
        content_template_id="academic-pressure-map",
    )
    decision = record_decision(
        db,
        user_id=user.user_id,
        eligible_at=exposed_start - timedelta(minutes=30),
        decision_status="shown",
        exposure_category="behavioral_insight",
        content_template_id="overrun-summary",
    )
    record_render(
        db,
        exposure_id=decision.exposure_id,
        rendered_at=exposed_start - timedelta(minutes=30),
        surface="insights",
        channel="web",
        content_snapshot="You overrun this category.",
        render_policy_version="render_v0",
        interruptiveness="inline",
        salience_level="medium",
    )
    db.commit()

    tasks = [clean_task, exposed_task]
    targets = ["planning_estimate", "duration_behavior"]
    bulk_clean = baseline_clean_task_ids(db, tasks=tasks, signal_targets=targets)
    single_clean = {
        task.task_id
        for task in tasks
        if baseline_clean_task(db, task=task, signal_targets=targets)
    }

    assert bulk_clean == single_clean == {"bulk-clean"}


def test_policy_effect_snapshot_records_unknown_ledger_incomplete_rate(db):
    _clean(db)
    user = _user(db)
    start = datetime(2026, 5, 9, 12, 0, 0)
    task = Task(
        task_id="task-policy-effect",
        user_id=user.user_id,
        title="Policy effect task",
        planned_start_utc=start,
        planned_end_utc=start + timedelta(minutes=60),
        planned_duration_minutes=60,
        executed_start_utc=start,
        executed_end_utc=start + timedelta(minutes=90),
        executed_duration_minutes=90,
        state=TaskState.EXECUTED,
        initiation_status="initiated",
    )
    db.add(task)
    record_decision(
        db,
        user_id=user.user_id,
        eligible_at=start - timedelta(minutes=30),
        decision_status="shown",
        exposure_category="behavioral_insight",
        content_template_id="overrun-summary",
    )
    db.commit()

    rows = record_policy_effect_snapshot(
        db,
        user_id=user.user_id,
        tasks=[task],
        signal_targets=["duration_behavior"],
        window_start=start - timedelta(days=1),
        window_end=start + timedelta(days=1),
    )
    db.commit()

    assert len(rows) == 1
    row = rows[0]
    assert row.policy_version == "exposure_horizon_v0"
    assert row.signal_target == "duration_behavior"
    assert row.exposure_category == "all"
    assert row.state_distribution_counts == {"UNKNOWN": 1}
    assert row.unknown_rate == 1.0
    assert row.ledger_incomplete_rate == 1.0
    assert row.sample_count == 1
