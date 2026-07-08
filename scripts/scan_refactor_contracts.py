#!/usr/bin/env python3
"""Static checks for S1c refactor authority contracts.

This is intentionally narrower than a generic lint pass. Each hard-fail rule
maps to a freeze/refactor contract that is precise enough to enforce without
human judgment. Broader product-copy questions stay report-only.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]

SKIP_PARTS = {
    ".git",
    ".next",
    ".next-public",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "tmp",
}


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    path: str
    line: int
    excerpt: str


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def should_scan(path: Path, suffixes: set[str]) -> bool:
    if path.suffix not in suffixes:
        return False
    return not (set(path.parts) & SKIP_PARTS)


def iter_files(root: Path, suffixes: set[str]) -> Iterable[Path]:
    if not root.exists():
        return
    for path in root.rglob("*"):
        if path.is_file() and should_scan(path, suffixes):
            yield path


def scan_lines(
    *,
    rule_id: str,
    severity: str,
    files: Iterable[Path],
    pattern: re.Pattern[str],
    allowed_paths: set[str] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    allowed_paths = allowed_paths or set()
    for path in files:
        candidate = rel(path)
        if candidate in allowed_paths:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for index, line in enumerate(lines, start=1):
            if pattern.search(line):
                findings.append(
                    Finding(
                        rule_id=rule_id,
                        severity=severity,
                        path=candidate,
                        line=index,
                        excerpt=line.strip()[:220],
                    )
                )
    return findings


def worker_render_truth_findings() -> list[Finding]:
    return scan_lines(
        rule_id="worker_must_not_emit_render_truth",
        severity="error",
        files=iter_files(REPO_ROOT / "backend" / "app" / "workers" / "jobs", {".py"}),
        pattern=re.compile(r"\bemit_surface_render\s*\("),
    )


def provider_completion_authority_findings() -> list[Finding]:
    return scan_lines(
        rule_id="provider_completion_event_constructor_owned_by_deadline_manager",
        severity="error",
        files=iter_files(REPO_ROOT / "backend" / "app", {".py"}),
        pattern=re.compile(r"\bDeadlineCompletionEvent\s*\("),
        allowed_paths={
            "backend/app/db/models.py",
            "backend/app/services/deadline_manager.py",
        },
    )


def analytics_direct_exposure_findings() -> list[Finding]:
    return scan_lines(
        rule_id="analytics_must_not_instantiate_exposure_rows_directly",
        severity="error",
        files=[REPO_ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "analytics.py"],
        pattern=re.compile(
            r"\b(?:ExposureDecisionEvent|ExposureRenderEvent|ExposureAckEvent|SuppressionEvent)\s*\("
        ),
    )


def app_direct_output_surface_helper_findings() -> list[Finding]:
    return scan_lines(
        rule_id="app_must_not_bypass_output_surface_emitter",
        severity="error",
        files=iter_files(REPO_ROOT / "backend" / "app", {".py"}),
        pattern=re.compile(r"\b(?:record_decision|record_render|record_suppression)\s*\("),
        allowed_paths={
            "backend/app/services/exposure_ledger.py",
            "backend/app/services/output_surfaces.py",
        },
    )


def app_direct_legacy_reflection_row_findings() -> list[Finding]:
    return scan_lines(
        rule_id="app_must_not_create_legacy_reflection_rows_directly",
        severity="error",
        files=iter_files(REPO_ROOT / "backend" / "app", {".py"}),
        pattern=re.compile(r"\bReflectionViewLog\s*\("),
        allowed_paths={
            "backend/app/db/models.py",
            "backend/app/services/output_surfaces.py",
        },
    )


def frontend_jarvis_findings() -> list[Finding]:
    return scan_lines(
        rule_id="frontend_must_not_call_jarvis_runtime",
        severity="error",
        files=iter_files(REPO_ROOT / "frontend", {".ts", ".tsx", ".js", ".jsx"}),
        pattern=re.compile(r"(?:/v1/jarvis|\bJarvis\b|\bjarvis\b)"),
    )


def frontend_behavioral_claim_review_findings() -> list[Finding]:
    """Review-only signal for copy that may need ClaimCompiler scrutiny.

    This intentionally does not fail. Some matches are comments, survey item
    wording, or bounded existing UI. The value is a stable list to inspect
    before frontend extraction and future ClaimCompiler work.
    """
    return scan_lines(
        rule_id="frontend_behavioral_claim_copy_review",
        severity="warning",
        files=iter_files(REPO_ROOT / "frontend", {".ts", ".tsx"}),
        pattern=re.compile(
            r"(you are|you usually|your pattern|archetype|discipline|avoidance|motivation|"
            r"because you|behavioral|insight|claim)",
            re.IGNORECASE,
        ),
    )


STALE_DOC_AUTHORITY_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "docs/building_phases.md": (
        "R5a extraction rule:",
        "historical/parked",
        "Do not extract runtime work",
    ),
    "docs/phase_6_architecture_backlog.md": (
        "R5a extraction rule:",
        "parked design history",
        "not current implementation permission",
    ),
    "docs/deadline_mechanism_design.md": (
        "R5a extraction rule:",
        "historical/parked",
        "work is not authorized",
    ),
    "docs/academic_execution_substrate.md": (
        "R5a extraction rule:",
        "parked architecture notes",
        "must not be extracted into runtime code",
    ),
    "docs/academic_asset_velocity_and_evidence_fusion_plan.md": (
        "R5a extraction rule:",
        "research/planning backlog only",
        "do not authorize runtime",
    ),
    "docs/core_product_loop_wave_plan.md": (
        "R5a extraction rule:",
        "historical/subordinate",
        "Use this file for context only",
    ),
    "docs/AGENT_HANDOFF.md": (
        "R5a extraction rule:",
        "historical onboarding context",
        "not permission",
    ),
    "docs/provider_adapter_contract.md": (
        "R5a extraction rule:",
        "future explicitly approved adapter",
        "does not authorize new provider-native UI",
    ),
}


def stale_doc_authority_banner_findings() -> list[Finding]:
    findings: list[Finding] = []
    for doc_path, snippets in STALE_DOC_AUTHORITY_REQUIREMENTS.items():
        path = REPO_ROOT / doc_path
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            findings.append(
                Finding(
                    rule_id="stale_docs_must_preserve_freeze_authority_banner",
                    severity="error",
                    path=doc_path,
                    line=1,
                    excerpt="required stale authority doc is missing",
                )
            )
            continue
        for snippet in snippets:
            if snippet not in text:
                findings.append(
                    Finding(
                        rule_id="stale_docs_must_preserve_freeze_authority_banner",
                        severity="error",
                        path=doc_path,
                        line=1,
                        excerpt=f"missing required freeze/subordination phrase: {snippet}",
                    )
                )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-on-errors", action="store_true")
    parser.add_argument("--include-review", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    findings: list[Finding] = []
    findings.extend(worker_render_truth_findings())
    findings.extend(provider_completion_authority_findings())
    findings.extend(analytics_direct_exposure_findings())
    findings.extend(app_direct_output_surface_helper_findings())
    findings.extend(app_direct_legacy_reflection_row_findings())
    findings.extend(frontend_jarvis_findings())
    findings.extend(stale_doc_authority_banner_findings())
    if args.include_review:
        findings.extend(frontend_behavioral_claim_review_findings())

    errors = [finding for finding in findings if finding.severity == "error"]
    output = {
        "ok": not (args.fail_on_errors and errors),
        "mode": "fail_on_errors" if args.fail_on_errors else "report_only",
        "review_included": args.include_review,
        "error_count": len(errors),
        "warning_count": sum(1 for item in findings if item.severity == "warning"),
        "findings": [finding.__dict__ for finding in findings],
    }
    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
    return 1 if args.fail_on_errors and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
