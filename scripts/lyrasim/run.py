"""Run LyraSim scenarios and emit deterministic reports."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from scripts.lyrasim.models import CleanDataAdmission, LyraOutput
from scripts.lyrasim.reports.writer import build_report, write_report
from scripts.lyrasim.scenarios import generate_scenario
from scripts.lyrasim.scorers import score_scenario


DEFAULT_SCENARIO = "task_started_never_stopped"
DEFAULT_REPORT_DIR = Path(__file__).resolve().parent / "reports"


def stubbed_lyra_output_for_v0() -> LyraOutput:
    return LyraOutput(
        stubbed=True,
        product_seams_exercised=(),
        authority_rung="interpretation",
        text_outputs=(
            "Timer has no stop event after the stale threshold; keep this as descriptive history.",
        ),
        clean_data_admissions=(
            CleanDataAdmission(
                profile="planning_calibration",
                admitted=False,
                reason="stale_unclosed_timer",
            ),
        ),
    )


def run_scenario(
    *,
    scenario_id: str,
    seed: int,
    output_path: Path | None = None,
) -> dict:
    scenario = generate_scenario(scenario_id, seed)
    lyra_output = stubbed_lyra_output_for_v0()
    score = score_scenario(scenario, lyra_output)
    report = build_report(scenario=scenario, output=lyra_output, score=score)
    if output_path is not None:
        write_report(report, output_path)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LyraSim V0 scenarios.")
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO)
    parser.add_argument("--seed", type=int, default=20260522)
    parser.add_argument("--replay", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional report path. Defaults to scripts/lyrasim/reports/<scenario>.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = args.output
    if output_path is None:
        output_path = DEFAULT_REPORT_DIR / f"{args.scenario}_seed_{args.seed}.json"
    report = run_scenario(
        scenario_id=args.scenario,
        seed=args.seed,
        output_path=output_path,
    )
    print(f"LyraSim report written: {output_path}")
    print(f"scenario={report['scenario_id']} seed={report['seed']} stubbed={report['stubbed']}")


if __name__ == "__main__":
    main()
