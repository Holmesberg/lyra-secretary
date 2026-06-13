"""Deterministic JSON report writer for LyraSim."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.lyrasim.contracts import AUTHORITY_LADDER_VERSION, SCORER_VERSION
from scripts.lyrasim.models import LyraOutput, ScenarioData, ScoreResult


def _failed_metric_names(score: ScoreResult) -> list[str]:
    return [
        name
        for name, metric in sorted(score.metrics.items())
        if metric.status == "fail"
    ]


def build_findings_summary(
    *,
    scenario: ScenarioData,
    output: LyraOutput,
    score: ScoreResult,
    minimal_replay_command: str,
) -> dict[str, Any]:
    failed_metrics = _failed_metric_names(score)
    failed_invariants = list(score.failed_invariants)
    overall_status = "fail" if failed_metrics or failed_invariants else "pass"
    product_seam_validated = (not output.stubbed) and bool(output.product_seams_exercised)

    summary_lines = [
        (
            f"status={overall_status} scenario={scenario.scenario_id} "
            f"seed={scenario.seed}"
        ),
        (
            f"resolution_rung={output.resolution_rung} "
            f"safe_action_type={output.safe_action_type}"
        ),
    ]
    if output.stubbed:
        summary_lines.append(
            "stubbed=true; harness validation only, not product safety"
        )
    if failed_metrics:
        summary_lines.append("failed_metrics=" + ",".join(failed_metrics))
    if failed_invariants:
        summary_lines.append("failed_invariants=" + ",".join(failed_invariants))
    summary_lines.append("replay=" + minimal_replay_command)

    return {
        "overall_status": overall_status,
        "finding_count": len(failed_metrics) + len(failed_invariants),
        "failed_metrics": failed_metrics,
        "failed_invariants": failed_invariants,
        "stubbed": output.stubbed,
        "product_seam_validated": product_seam_validated,
        "resolution_rung": output.resolution_rung,
        "expected_resolution_rung": scenario.expected_resolution_rung,
        "safe_action_type": output.safe_action_type,
        "summary_lines": summary_lines,
    }


def build_report(
    *,
    scenario: ScenarioData,
    output: LyraOutput,
    score: ScoreResult,
) -> dict[str, Any]:
    minimal_replay_command = (
        "python scripts/lyrasim/run.py "
        f"--scenario {scenario.scenario_id} --seed {scenario.seed} --replay"
    )
    findings_summary = build_findings_summary(
        scenario=scenario,
        output=output,
        score=score,
        minimal_replay_command=minimal_replay_command,
    )
    return {
        "scenario_id": scenario.scenario_id,
        "scenario_version": scenario.scenario_version,
        "scenario_origin": scenario.scenario_origin,
        "expected_resolution_rung": scenario.expected_resolution_rung,
        "seed": scenario.seed,
        "scorer_version": SCORER_VERSION,
        "authority_ladder_version": AUTHORITY_LADDER_VERSION,
        "stubbed": output.stubbed,
        "product_seams_exercised": list(output.product_seams_exercised),
        "synthetic_user_id": scenario.synthetic_user_id,
        "hidden_state_summary": scenario.hidden_state.to_summary(),
        "simulated_self_report_summary": [
            self_report.to_summary()
            for self_report in scenario.simulated_self_reports
        ],
        "observable_trace_sequence": scenario.trace_dicts(),
        "lyra_output": output.to_dict(),
        **score.to_report_dict(),
        "findings_summary": findings_summary,
        "coverage_limitations": list(scenario.coverage_limitations),
        "generator_assumptions": list(scenario.generator_assumptions),
        "minimal_replay_command": minimal_replay_command,
    }


def write_report(report: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def format_cli_findings(report: dict[str, Any]) -> list[str]:
    summary = report["findings_summary"]
    lines = ["LyraSim findings:"]
    lines.extend(f"  {line}" for line in summary["summary_lines"])
    safe_action = report["metrics"].get("safe_action_availability_rate")
    paralysis = report["metrics"].get("uncertainty_paralysis_rate")
    if safe_action is not None:
        lines.append(
            "  safe_action_availability_rate="
            f"{safe_action['value']} ({safe_action['status']})"
        )
    if paralysis is not None:
        lines.append(
            "  uncertainty_paralysis_rate="
            f"{paralysis['value']} ({paralysis['status']})"
        )
    return lines
