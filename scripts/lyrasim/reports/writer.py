"""Deterministic JSON report writer for LyraSim."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.lyrasim.contracts import AUTHORITY_LADDER_VERSION, SCORER_VERSION
from scripts.lyrasim.models import LyraOutput, ScenarioData, ScoreResult


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
    return {
        "scenario_id": scenario.scenario_id,
        "scenario_version": scenario.scenario_version,
        "scenario_origin": scenario.scenario_origin,
        "seed": scenario.seed,
        "scorer_version": SCORER_VERSION,
        "authority_ladder_version": AUTHORITY_LADDER_VERSION,
        "stubbed": output.stubbed,
        "product_seams_exercised": list(output.product_seams_exercised),
        "synthetic_user_id": scenario.synthetic_user_id,
        "hidden_state_summary": scenario.hidden_state.to_summary(),
        "observable_trace_sequence": scenario.trace_dicts(),
        "expected_output_contract": scenario.expected_output_contract(),
        "lyra_output": output.to_dict(),
        **score.to_report_dict(),
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
