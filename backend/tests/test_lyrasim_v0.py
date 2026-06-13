from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.lyrasim.generators.task_started_never_stopped import generate
from scripts.lyrasim.generators.baseet_deadline_pressure import (
    SCENARIO_ID as BASEET_DEADLINE_PRESSURE_SCENARIO_ID,
)
from scripts.lyrasim.generators.baseet_resource_open_idle_45m import (
    generate as generate_baseet_idle,
)
from scripts.lyrasim.generators.baseet_progress_candidates import (
    BACKGROUND_VIDEO_SCENARIO_ID,
    MULTIDEVICE_UPLOAD_SCENARIO_ID,
    REVERSE_PROGRESS_SCENARIO_ID,
    STALE_PROGRESS_SCENARIO_ID,
    generate_stale_task_progress_candidate,
)
from scripts.lyrasim.generators.execution_anomaly_generalization import (
    SCENARIO_ID as EXECUTION_OUTLIER_SCENARIO_ID,
    generate as generate_execution_outlier,
)
from scripts.lyrasim.models import (
    CleanDataAdmission,
    HypothesisCheckPrompt,
    LyraOutput,
    TraceEvent,
)
from scripts.lyrasim.reports.writer import (
    build_report,
    format_cli_findings,
    write_report,
)
from scripts.lyrasim.product_seams.academic_pressure import (
    lyra_output_from_pressure_map_response,
    seed_baseet_deadlines_from_scenario,
)
from scripts.lyrasim.product_seams.insights import (
    lyra_output_from_insights_response,
    seed_execution_tasks_from_scenario,
)
from scripts.lyrasim.run import run_scenario, stubbed_lyra_output_for_v0
from scripts.lyrasim.scenarios import SCENARIOS, generate_scenario
from scripts.lyrasim.scorers import score_scenario
from scripts.lyrasim.scorers.core import _rate_metric

from app.api.v1.endpoints import analytics as analytics_module
from app.db.models import ExposureRenderEvent, Task, User
from app.services import academic_pressure as academic_pressure_service
from tests.conftest import auth_headers


class _LyraSimFakeRedis:
    def __init__(self):
        self.client = self
        self.keys: set[str] = set()

    def exists(self, key, *_args, **_kwargs):
        return key in self.keys

    def setex(self, key, _ttl, value):
        self.keys.add(key)
        return value

    def sismember(self, *_args, **_kwargs):
        return False

    def sadd(self, *_args, **_kwargs):
        return None

    def expire(self, *_args, **_kwargs):
        return None


def test_generator_is_deterministic_by_seed():
    first = generate(20260522)
    second = generate(20260522)

    assert first == second
    assert first.synthetic_user_id.startswith("synthetic_")


def test_scenario_registry_has_a_scorer_backed_v0_scenario():
    assert "task_started_never_stopped" in SCENARIOS
    assert SCENARIOS["task_started_never_stopped"].scorer_names

    scenario = generate_scenario("task_started_never_stopped", 20260522)
    output = stubbed_lyra_output_for_v0()
    score = score_scenario(scenario, output)

    assert score.metrics
    assert "clean_data_contamination_rate" in score.metrics


def test_scorer_depends_on_generated_trace_data():
    scenario = generate(20260522)
    output = LyraOutput(
        stubbed=True,
        product_seams_exercised=(),
        authority_rung="interpretation",
        text_outputs=("This is descriptive history.",),
        clean_data_admissions=(
            CleanDataAdmission(
                profile="planning_calibration",
                admitted=True,
                reason="bad_stub",
            ),
        ),
    )

    score_with_stale_trace = score_scenario(scenario, output)
    assert score_with_stale_trace.metrics["clean_data_contamination_rate"].status == "fail"

    repaired_trace = tuple(
        event
        for event in scenario.observable_trace
        if event.event_type != "stale_threshold_crossed"
    ) + (
        TraceEvent(
            event_type="timer_stopped",
            occurred_at_minute=60,
            payload={"provenance": "observed"},
        ),
    )
    scenario_without_stale_condition = type(scenario)(
        scenario_id=scenario.scenario_id,
        scenario_version=scenario.scenario_version,
        scenario_origin=scenario.scenario_origin,
        seed=scenario.seed,
        synthetic_user_id=scenario.synthetic_user_id,
        hidden_state=scenario.hidden_state,
        observable_trace=repaired_trace,
        generator_assumptions=scenario.generator_assumptions,
        coverage_limitations=scenario.coverage_limitations,
    )

    score_without_stale_trace = score_scenario(scenario_without_stale_condition, output)
    assert score_without_stale_trace.metrics["clean_data_contamination_rate"].status == "pass"


def test_hidden_state_is_not_in_product_facing_trace():
    scenario = generate(20260522)
    trace_json = json.dumps(scenario.trace_dicts(), sort_keys=True)

    assert "hidden_state" not in trace_json
    assert scenario.hidden_state.user_activity == "unknown_after_timer_start"


def test_stubbed_outputs_are_labeled_and_do_not_validate_product_seams():
    output = stubbed_lyra_output_for_v0()

    assert output.stubbed is True
    assert output.product_seams_exercised == ()


def test_report_contract_and_replay_command(tmp_path):
    scenario = generate(20260522)
    output = stubbed_lyra_output_for_v0()
    score = score_scenario(scenario, output)
    report = build_report(scenario=scenario, output=output, score=score)
    output_path = tmp_path / "report.json"

    write_report(report, output_path)
    parsed = json.loads(output_path.read_text(encoding="utf-8"))

    for key in (
        "scenario_id",
        "scenario_version",
        "scenario_origin",
        "expected_resolution_rung",
        "seed",
        "scorer_version",
        "authority_ladder_version",
        "stubbed",
        "product_seams_exercised",
        "synthetic_user_id",
        "hidden_state_summary",
        "simulated_self_report_summary",
        "observable_trace_sequence",
        "lyra_output",
        "metrics",
        "failed_invariants",
        "findings_summary",
        "coverage_limitations",
        "generator_assumptions",
        "minimal_replay_command",
    ):
        assert key in parsed

    assert parsed["seed"] == 20260522
    assert parsed["scenario_origin"] == "synthetic"
    assert "--replay" in parsed["minimal_replay_command"]
    assert parsed["findings_summary"]["overall_status"] == "pass"
    assert parsed["findings_summary"]["resolution_rung"] == "suppress"
    assert parsed["findings_summary"]["safe_action_type"] == "none"
    assert parsed["coverage_limitations"]
    assert parsed["generator_assumptions"]


def test_cli_findings_summary_includes_replay_and_resolution():
    report = run_scenario(
        scenario_id="baseet_resource_open_idle_45m",
        seed=20260522,
        output_path=None,
    )
    lines = format_cli_findings(report)
    rendered = "\n".join(lines)

    assert "LyraSim findings:" in rendered
    assert "resolution_rung=clarify" in rendered
    assert "safe_action_type=ask_pause_continue_split" in rendered
    assert "replay=python scripts/lyrasim/run.py" in rendered
    assert "harness validation only, not product safety" in rendered


def test_baseet_deadline_pressure_stub_control_is_cli_safe():
    report = run_scenario(
        scenario_id=BASEET_DEADLINE_PRESSURE_SCENARIO_ID,
        seed=20260522,
        output_path=None,
    )

    assert report["stubbed"] is True
    assert report["findings_summary"]["overall_status"] == "pass"
    assert report["findings_summary"]["product_seam_validated"] is False
    assert report["findings_summary"]["safe_action_type"] == "confirm_coverage"


def test_metric_zero_denominator_is_not_applicable():
    metric = _rate_metric(
        name="provider_truth_hallucination_rate",
        numerator=0,
        denominator=0,
        formula="n/d",
        expected="zero",
    )

    assert metric.value is None
    assert metric.status == "not_applicable"


def test_run_scenario_is_deterministic_without_writing_repo_files():
    first = run_scenario(
        scenario_id="task_started_never_stopped",
        seed=20260522,
        output_path=None,
    )
    second = run_scenario(
        scenario_id="task_started_never_stopped",
        seed=20260522,
        output_path=None,
    )

    assert first == second
    assert first["stubbed"] is True


def test_baseet_idle_resource_scenario_is_registered_and_video_derived():
    assert "baseet_resource_open_idle_45m" in SCENARIOS
    assert SCENARIOS["baseet_resource_open_idle_45m"].scorer_names

    scenario = generate_scenario("baseet_resource_open_idle_45m", 20260522)

    assert scenario == generate_baseet_idle(20260522)
    assert scenario.scenario_origin == "video_derived"
    assert scenario.hidden_state.user_activity == "away_from_keyboard"
    assert scenario.expected_resolution_rung == "clarify_or_repair"
    assert scenario.simulated_self_reports
    assert scenario.simulated_self_reports[0].clean_data_eligible is False
    assert any(
        event.payload.get("requires_safe_action") is True
        for event in scenario.observable_trace
    )


def test_baseet_idle_resource_safe_stub_remains_low_authority():
    scenario = generate_baseet_idle(20260522)
    output = stubbed_lyra_output_for_v0(scenario.scenario_id)
    score = score_scenario(scenario, output)

    assert output.stubbed is True
    assert output.product_seams_exercised == ()
    assert output.safe_actions
    assert output.safe_action_type == "ask_pause_continue_split"
    assert output.resolution_rung == "clarify"
    assert output.hypothesis_checks
    assert output.hypothesis_checks[0].question_text.endswith("?")
    assert score.failed_invariants == ()
    assert score.metrics["authority_violation_rate"].status == "pass"
    assert score.metrics["clean_data_contamination_rate"].status == "pass"
    assert score.metrics["provider_truth_hallucination_rate"].status == "pass"
    assert score.metrics["safe_action_availability_rate"].value == 1.0
    assert score.metrics["uncertainty_paralysis_rate"].value == 0.0
    assert score.metrics["self_report_prompt_availability_rate"].value == 1.0


def test_baseet_idle_resource_requires_hypothesis_check_prompt():
    scenario = generate_baseet_idle(20260522)
    output = LyraOutput(
        stubbed=True,
        product_seams_exercised=(),
        authority_rung="suggestion",
        text_outputs=("Possible pause or inactive resource state detected.",),
        clean_data_admissions=(
            CleanDataAdmission(
                profile="planning_calibration",
                admitted=False,
                reason="passive_provider_idle_trace",
            ),
        ),
        safe_actions=("ask_pause_or_continue",),
    )

    score = score_scenario(scenario, output)

    assert score.metrics["self_report_prompt_availability_rate"].status == "fail"
    assert (
        "self_report_clarification:no_valid_hypothesis_check_prompt"
        in score.failed_invariants
    )


def test_hypothesis_check_prompt_must_not_create_clean_truth():
    scenario = generate_baseet_idle(20260522)
    output = LyraOutput(
        stubbed=True,
        product_seams_exercised=(),
        authority_rung="suggestion",
        text_outputs=("Possible pause or inactive resource state detected.",),
        clean_data_admissions=(
            CleanDataAdmission(
                profile="planning_calibration",
                admitted=False,
                reason="passive_provider_idle_trace",
            ),
        ),
        safe_actions=("ask_pause_or_continue",),
        hypothesis_checks=(
            HypothesisCheckPrompt(
                hypothesis_id="possible_pause_or_inactive_resource",
                question_text="Was this a pause or inactive resource moment?",
                options=("yes_pause_or_away", "no_i_was_working"),
                self_report_provenance="self_reported",
                calibration_use="clean_execution_truth",
                clean_data_eligible=True,
            ),
        ),
    )

    score = score_scenario(scenario, output)

    assert score.metrics["self_report_prompt_availability_rate"].status == "fail"
    assert (
        "self_report_clarification:no_valid_hypothesis_check_prompt"
        in score.failed_invariants
    )


def test_baseet_idle_resource_scorer_catches_surveillance_hallucination():
    scenario = generate_baseet_idle(20260522)
    output = LyraOutput(
        stubbed=True,
        product_seams_exercised=(),
        authority_rung="suggestion",
        text_outputs=("You studied and completed this lecture resource.",),
        clean_data_admissions=(
            CleanDataAdmission(
                profile="planning_calibration",
                admitted=True,
                reason="bad_stub",
            ),
        ),
        published_claim_tags=("completion_claim", "studied_claim"),
    )

    score = score_scenario(scenario, output)

    assert score.metrics["authority_violation_rate"].status == "fail"
    assert score.metrics["clean_data_contamination_rate"].status == "fail"
    assert score.metrics["provider_truth_hallucination_rate"].status == "fail"
    assert score.metrics["safe_action_availability_rate"].status == "fail"
    assert score.metrics["uncertainty_paralysis_rate"].status == "fail"
    assert any(
        failure.startswith("forbidden_cognition_or_identity_claim")
        for failure in score.failed_invariants
    )
    assert "provider_structure_treated_as_truth" in score.failed_invariants
    assert "uncertainty_paralysis:no_safe_action_available" in score.failed_invariants


@pytest.mark.parametrize(
    "scenario_id,expected_safe_action_type,expected_resolution",
    (
        (
            STALE_PROGRESS_SCENARIO_ID,
            "confirm_done_partial_discard",
            "clarify",
        ),
        (
            BACKGROUND_VIDEO_SCENARIO_ID,
            "confirm_done_partial_discard",
            "clarify",
        ),
        (
            MULTIDEVICE_UPLOAD_SCENARIO_ID,
            "adjust_session_duration",
            "repair",
        ),
        (
            REVERSE_PROGRESS_SCENARIO_ID,
            "mark_open_unconfirmed",
            "clarify",
        ),
    ),
)
def test_baseet_progress_candidate_scenarios_remain_low_authority(
    scenario_id,
    expected_safe_action_type,
    expected_resolution,
):
    scenario = generate_scenario(scenario_id, 20260522)
    output = stubbed_lyra_output_for_v0(scenario.scenario_id)
    score = score_scenario(scenario, output)
    trace_json = json.dumps(scenario.trace_dicts(), sort_keys=True)

    assert scenario.expected_resolution_rung == "clarify_or_repair"
    assert "provider_progress_candidate" in trace_json
    assert "execution_progress" not in trace_json
    assert output.safe_action_type == expected_safe_action_type
    assert output.resolution_rung == expected_resolution
    assert not output.mutations_attempted
    assert score.failed_invariants == ()
    assert score.metrics["safe_action_availability_rate"].value == 1.0
    assert score.metrics["uncertainty_paralysis_rate"].value == 0.0
    assert score.metrics["clean_data_contamination_rate"].status == "pass"
    assert score.metrics["provider_truth_hallucination_rate"].status == "pass"


def test_baseet_deadline_pressure_validates_real_pressure_map_product_seam(
    db,
    client,
    monkeypatch,
):
    user = User(
        email="lyrasim-pressure-seam@example.test",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    monkeypatch.setattr(
        academic_pressure_service,
        "baseet_pressure_input_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        academic_pressure_service,
        "recovery_nudges_enabled",
        lambda: True,
    )

    scenario = generate_scenario(BASEET_DEADLINE_PRESSURE_SCENARIO_ID, 20260522)
    rows = seed_baseet_deadlines_from_scenario(
        db,
        scenario,
        user_id=user.user_id,
        base_time=datetime.utcnow(),
    )

    response = client.get(
        "/v1/academic/pressure-map?horizon_days=14",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    data = response.json()
    output = lyra_output_from_pressure_map_response(data)
    score = score_scenario(scenario, output)
    report = build_report(scenario=scenario, output=output, score=score)

    assert len(rows) == 3
    assert output.stubbed is False
    assert output.product_seams_exercised == (
        "academic_pressure.pressure_map",
        "output_surfaces.exposure_ledger",
    )
    assert report["findings_summary"]["product_seam_validated"] is True
    assert score.failed_invariants == ()
    assert score.metrics["authority_violation_rate"].status == "pass"
    assert score.metrics["clean_data_contamination_rate"].status == "pass"
    assert score.metrics["provider_truth_hallucination_rate"].status == "pass"
    assert score.metrics["safe_action_availability_rate"].value == 1.0
    assert score.metrics["uncertainty_paralysis_rate"].value == 0.0

    assert data["clean_profile"] is None
    assert data["authority_rung"] == "suggestion"
    assert data["mutation_permission"] == "explicit_user_confirmation_required"
    assert "automatic_task_creation" in data["denied_authority"]
    assert "automatic_calendar_mutation" in data["denied_authority"]
    assert db.query(Task).filter(Task.user_id == user.user_id).count() == 0

    assert data["items"]
    assert {item["provider_kind"] for item in data["items"]} == {"baseet"}
    assert {item["evidence_class"] for item in data["items"]} == {
        "external_obligation"
    }
    assert {item["trust_state"] for item in data["items"]} == {
        "verified_reachable"
    }
    assert all(
        "coverage correctness" in " ".join(item["warnings"])
        for item in data["items"]
    )
    assert data["estimated_low_minutes"] < data["estimated_high_minutes"]
    assert data["coverage_questions"]
    assert any(
        option["action"] == "confirm_coverage"
        for option in data["recovery_options"]
    )
    assert "overloaded" not in data["headline"].lower()
    assert "overloaded" not in data["pressure_summary"].lower()

    render = (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.render_id == data["render_id"])
        .one()
    )
    snapshot = render.content_snapshot
    assert "Assignment 1" not in snapshot
    assert "hash_baseet" not in snapshot
    assert "baseet_mock" not in snapshot
    assert "lyrasim-pressure-seam" not in snapshot
    assert "external_obligation_count" in snapshot


def test_execution_outlier_scenario_is_registered_and_repo_derived():
    assert EXECUTION_OUTLIER_SCENARIO_ID in SCENARIOS
    assert SCENARIOS[EXECUTION_OUTLIER_SCENARIO_ID].scorer_names

    scenario = generate_scenario(EXECUTION_OUTLIER_SCENARIO_ID, 20260522)

    assert scenario == generate_execution_outlier(20260522)
    assert scenario.scenario_origin == "repo_derived"
    assert scenario.expected_resolution_rung == "suppress"
    assert any(
        event.payload.get("generalization_probe") == "single_outlier"
        for event in scenario.observable_trace
    )
    assert any(
        event.payload.get("clean_data_eligible") is False
        for event in scenario.observable_trace
    )


def test_execution_outlier_stub_control_is_cli_safe():
    report = run_scenario(
        scenario_id=EXECUTION_OUTLIER_SCENARIO_ID,
        seed=20260522,
        output_path=None,
    )

    assert report["stubbed"] is True
    assert report["findings_summary"]["overall_status"] == "pass"
    assert report["findings_summary"]["product_seam_validated"] is False
    assert report["findings_summary"]["resolution_rung"] == "suppress"


def test_single_outlier_overgeneralization_invariant_fails():
    scenario = generate_scenario(EXECUTION_OUTLIER_SCENARIO_ID, 20260522)
    output = LyraOutput(
        stubbed=True,
        product_seams_exercised=(),
        authority_rung="interpretation",
        text_outputs=(
            "You usually take far longer on study tasks; this is your baseline.",
        ),
        clean_data_admissions=(
            CleanDataAdmission(
                profile="planning_calibration",
                admitted=False,
                reason="corrected_execution_anomaly",
            ),
        ),
        resolution_rung="suppress",
    )

    score = score_scenario(scenario, output)

    assert score.metrics["authority_violation_rate"].status == "fail"
    assert any(
        failure.startswith("single_outlier_overgeneralized")
        for failure in score.failed_invariants
    )


def test_dirty_execution_outlier_admission_fails_clean_data_gate():
    scenario = generate_scenario(EXECUTION_OUTLIER_SCENARIO_ID, 20260522)
    output = lyra_output_from_insights_response(
        {
            "sessions_analyzed": 11,
            "insights": [],
            "authority_rung": "interpretation",
            "suppressed_reason": "test_dirty_admission",
        },
        scenario=scenario,
    )

    score = score_scenario(scenario, output)

    assert score.metrics["clean_data_contamination_rate"].status == "fail"
    assert (
        "unsafe_trace_admitted_to_clean_profile:planning_calibration"
        in score.failed_invariants
    )


def test_execution_outlier_validates_real_insights_product_seam(
    db,
    client,
    monkeypatch,
):
    user = User(
        email="lyrasim-insights-outlier-seam@example.test",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    scenario = generate_scenario(EXECUTION_OUTLIER_SCENARIO_ID, 20260522)
    seeded = seed_execution_tasks_from_scenario(
        db,
        scenario,
        user_id=user.user_id,
        base_time=datetime.utcnow() - timedelta(days=30),
    )
    monkeypatch.setattr(
        analytics_module,
        "RedisClient",
        lambda: _LyraSimFakeRedis(),
    )

    response = client.get(
        "/v1/analytics/insights",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    data = response.json()
    output = lyra_output_from_insights_response(data, scenario=scenario)
    score = score_scenario(scenario, output)
    report = build_report(scenario=scenario, output=output, score=score)

    assert len(seeded["tasks"]) == 11
    assert len(seeded["corrections"]) == 1
    assert data["sessions_analyzed"] == 10
    assert data["insights"] == []
    assert data["suppressed_reason"] == "no_contract_safe_insights"
    assert output.stubbed is False
    assert output.product_seams_exercised == (
        "analytics.insights",
        "output_surfaces.exposure_ledger",
    )
    assert report["findings_summary"]["product_seam_validated"] is True
    assert score.failed_invariants == ()
    assert score.metrics["authority_violation_rate"].status == "pass"
    assert score.metrics["clean_data_contamination_rate"].status == "pass"


def test_provider_progress_candidate_cannot_auto_execute_or_enter_clean_data():
    scenario = generate_stale_task_progress_candidate(20260522)
    output = LyraOutput(
        stubbed=True,
        product_seams_exercised=(),
        authority_rung="suggestion",
        text_outputs=("This task is executed and completed from provider progress.",),
        clean_data_admissions=(
            CleanDataAdmission(
                profile="planning_calibration",
                admitted=True,
                reason="provider_progress_candidate",
            ),
            CleanDataAdmission(
                profile="measured_execution",
                admitted=True,
                reason="provider_progress_candidate",
            ),
        ),
        mutations_attempted=("task_state:EXECUTED",),
        published_claim_tags=("completion_claim",),
        safe_actions=(),
        safe_action_type="none",
        resolution_rung="adapt",
    )

    score = score_scenario(scenario, output)

    assert score.metrics["authority_violation_rate"].status == "fail"
    assert score.metrics["clean_data_contamination_rate"].status == "fail"
    assert score.metrics["provider_truth_hallucination_rate"].status == "fail"
    assert score.metrics["safe_action_availability_rate"].status == "fail"
    assert score.metrics["uncertainty_paralysis_rate"].status == "fail"
    assert "unauthorized_mutation_attempt" in score.failed_invariants
    assert "provider_structure_treated_as_truth" in score.failed_invariants


def test_safe_action_prevents_paralysis_for_unknown_progress_candidate():
    scenario = generate_stale_task_progress_candidate(20260522)
    output = stubbed_lyra_output_for_v0(scenario.scenario_id)
    score = score_scenario(scenario, output)

    assert score.metrics["safe_action_availability_rate"].value == 1.0
    assert score.metrics["uncertainty_paralysis_rate"].value == 0.0
    assert "uncertainty_paralysis:no_safe_action_available" not in score.failed_invariants


def test_missing_safe_action_is_paralysis_for_unknown_progress_candidate():
    scenario = generate_stale_task_progress_candidate(20260522)
    output = LyraOutput(
        stubbed=True,
        product_seams_exercised=(),
        authority_rung="suggestion",
        text_outputs=("Provider progress is ambiguous.",),
        clean_data_admissions=(
            CleanDataAdmission(
                profile="planning_calibration",
                admitted=False,
                reason="provider_progress_candidate",
            ),
        ),
        resolution_rung="suppress",
    )

    score = score_scenario(scenario, output)

    assert score.metrics["safe_action_availability_rate"].status == "fail"
    assert score.metrics["uncertainty_paralysis_rate"].status == "fail"
    assert "uncertainty_paralysis:no_safe_action_available" in score.failed_invariants


def test_safe_action_spam_rate_catches_tiny_ambiguity_prompt():
    scenario = generate_stale_task_progress_candidate(20260522)
    tiny_trace = (
        TraceEvent(
            event_type="provider_progress_candidate_observed",
            occurred_at_minute=1,
            payload={
                "evidence_class": "provider_progress_candidate",
                "provenance": "external_import",
                "low_severity_ambiguity": True,
                "requires_safe_action": False,
            },
        ),
    )
    low_severity = type(scenario)(
        scenario_id="baseet_low_severity_activity_blip",
        scenario_version="baseet_low_severity_activity_blip:v0",
        scenario_origin=scenario.scenario_origin,
        seed=scenario.seed,
        synthetic_user_id=scenario.synthetic_user_id,
        hidden_state=scenario.hidden_state,
        observable_trace=tiny_trace,
        generator_assumptions=scenario.generator_assumptions,
        coverage_limitations=scenario.coverage_limitations,
        expected_resolution_rung="suppress",
    )
    output = LyraOutput(
        stubbed=True,
        product_seams_exercised=(),
        authority_rung="suggestion",
        text_outputs=("Tiny provider blip recorded.",),
        clean_data_admissions=(),
        safe_actions=("confirm_done_partial_discard",),
        safe_action_type="confirm_done_partial_discard",
        resolution_rung="clarify",
    )

    score = score_scenario(low_severity, output)

    assert score.metrics["safe_action_spam_rate"].status == "fail"
    assert "safe_action_spam:low_severity_action_offered" in score.failed_invariants


def test_production_code_does_not_import_lyrasim():
    roots = [Path("backend/app"), Path("frontend")]
    forbidden = ("scripts.lyrasim", "lyrasim.")
    skipped_dirs = {"node_modules", ".next", "dist", "build", ".turbo"}
    offenders: list[str] = []

    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if any(part in skipped_dirs for part in path.parts):
                continue
            if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for token in forbidden:
                if token in text:
                    offenders.append(f"{path}:{token}")

    assert offenders == []
