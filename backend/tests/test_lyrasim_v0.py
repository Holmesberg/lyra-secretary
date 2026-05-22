from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.lyrasim.generators.task_started_never_stopped import generate
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

    repaired_trace = scenario.observable_trace + (
        TraceEvent(
            event_type="timer_stopped",
            occurred_at_minute=60,
            payload={"provenance": "observed"},
        ),
    )
    scenario_without_stale_condition = type(scenario)(
        scenario_id=scenario.scenario_id,
        scenario_version=scenario.scenario_version,
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
