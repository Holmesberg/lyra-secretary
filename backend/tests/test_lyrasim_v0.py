from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.lyrasim.generators.task_started_never_stopped import generate
from scripts.lyrasim.generators.baseet_resource_open_idle_45m import (
    generate as generate_baseet_idle,
)
from scripts.lyrasim.models import CleanDataAdmission, LyraOutput, TraceEvent
from scripts.lyrasim.reports.writer import build_report, write_report
from scripts.lyrasim.run import run_scenario, stubbed_lyra_output_for_v0
from scripts.lyrasim.scenarios import SCENARIOS, generate_scenario
from scripts.lyrasim.scorers import score_scenario
from scripts.lyrasim.scorers.core import _rate_metric


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
        "seed",
        "scorer_version",
        "authority_ladder_version",
        "stubbed",
        "product_seams_exercised",
        "synthetic_user_id",
        "hidden_state_summary",
        "observable_trace_sequence",
        "lyra_output",
        "metrics",
        "failed_invariants",
        "coverage_limitations",
        "generator_assumptions",
        "minimal_replay_command",
    ):
        assert key in parsed

    assert parsed["seed"] == 20260522
    assert parsed["scenario_origin"] == "synthetic"
    assert "--replay" in parsed["minimal_replay_command"]
    assert parsed["coverage_limitations"]
    assert parsed["generator_assumptions"]


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
    assert score.failed_invariants == ()
    assert score.metrics["authority_violation_rate"].status == "pass"
    assert score.metrics["clean_data_contamination_rate"].status == "pass"
    assert score.metrics["provider_truth_hallucination_rate"].status == "pass"
    assert score.metrics["safe_action_availability_rate"].value == 1.0
    assert score.metrics["uncertainty_paralysis_rate"].value == 0.0


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
