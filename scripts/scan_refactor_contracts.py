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
    "docs/archive/legacy/planning/building_phases.md": (
        "R5a extraction rule:",
        "historical/parked",
        "Do not extract runtime work",
    ),
    "docs/archive/legacy/planning/phase_6_architecture_backlog.md": (
        "R5a extraction rule:",
        "parked design history",
        "not current implementation permission",
    ),
    "docs/archive/legacy/provider_academic/deadline_mechanism_design.md": (
        "R5a extraction rule:",
        "historical/parked",
        "work is not authorized",
    ),
    "docs/archive/legacy/provider_academic/academic_execution_substrate.md": (
        "R5a extraction rule:",
        "parked architecture notes",
        "must not be extracted into runtime code",
    ),
    "docs/archive/legacy/provider_academic/academic_asset_velocity_and_evidence_fusion_plan.md": (
        "R5a extraction rule:",
        "research/planning backlog only",
        "do not authorize runtime",
    ),
    "docs/archive/legacy/planning/core_product_loop_wave_plan.md": (
        "R5a extraction rule:",
        "historical/subordinate",
        "Use this file for context only",
    ),
    "docs/archive/AGENT_HANDOFF.md": (
        "R5a extraction rule:",
        "historical onboarding context",
        "not permission",
    ),
    "docs/archive/legacy/provider_academic/provider_adapter_contract.md": (
        "R5a extraction rule:",
        "future explicitly approved adapter",
        "does not authorize new provider-native UI",
    ),
}


ACTIVE_DOC_REMOVED_SURFACE_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "docs/deployment_architecture.md": (
        re.compile(r"\bNotion sync\b"),
        re.compile(r"\bNotion retry queue\b"),
    ),
    "docs/architecture.md": (
        re.compile(r"\boperator-only JARVIS/OpenClaw\b"),
        re.compile(r"\bPer-user Notion config\b"),
        re.compile(r"\bNotion sync format\b"),
    ),
    "docs/runbooks/post_wave_dogfood_loop.md": (
        re.compile(r"\bactive Jarvis\b", re.IGNORECASE),
    ),
    "docs/prodblueprint_security.md": (
        re.compile(r"\badmin dashboards\b"),
        re.compile(r"\balpha funnel\b"),
        re.compile(r"\bdegrade Notion sync\b"),
        re.compile(r"\bNotion unavailable\b"),
    ),
    "docs/integrations_architecture.md": (
        re.compile(r"\bnotion_connect\b"),
        re.compile(r"\bnotion_enabled\`\) is appropriate\b"),
    ),
}

NO_UNAPPROVED_REBRAND_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".ps1",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

NO_UNAPPROVED_REBRAND_ROOTS = (
    REPO_ROOT / "frontend",
    REPO_ROOT / "backend" / "app",
    REPO_ROOT / "scripts",
    REPO_ROOT / ".github",
)

NO_UNAPPROVED_REBRAND_FILES = (
    REPO_ROOT / "README.md",
)

NO_UNAPPROVED_REBRAND_PATTERN = re.compile(r"\b(?:Barzakh|barzakh)\b")

JARVIS_TOOLS_IMPORT_PATTERN = re.compile(
    r"(?:from\s+app\.services\.jarvis_tools\s+import|"
    r"import\s+app\.services\.jarvis_tools|"
    r"from\s+app\.services\s+import\s+jarvis_tools)"
)

JARVIS_TOOLS_IMPORT_ALLOWED_PATHS: set[str] = set()

LEGACY_NOTIFICATION_PENDING_PATTERN = re.compile(
    r"/v1/notifications/pending(?:\?channel=|['\"\s])|notifications/pending\?channel="
)

LEGACY_NOTIFICATION_PENDING_ALLOWED_PATHS = {
    "backend/app/api/v1/endpoints/notifications.py",
    "scripts/scan_refactor_contracts.py",
}


def legacy_notification_pending_callsite_findings(
    extra_files: dict[str, str] | None = None,
) -> list[Finding]:
    """Keep callers on explicit web/openclaw notification endpoints.

    The compatibility route remains mounted for now, but new runtime/browser
    code must call /web/pending, /web/ack, or /openclaw/pending so delivery
    authority stays visible and the old channel footgun cannot re-enter.
    """
    files: list[Path] = []
    for root in (
        REPO_ROOT / "frontend",
        REPO_ROOT / "scripts",
        REPO_ROOT / "backend" / "app",
    ):
        files.extend(iter_files(root, {".py", ".js", ".jsx", ".mjs", ".ts", ".tsx"}))
    findings = scan_lines(
        rule_id="runtime_must_not_call_legacy_notification_pending_bridge",
        severity="error",
        files=files,
        pattern=LEGACY_NOTIFICATION_PENDING_PATTERN,
        allowed_paths=LEGACY_NOTIFICATION_PENDING_ALLOWED_PATHS,
    )
    if extra_files:
        for doc_path, text in extra_files.items():
            if doc_path in LEGACY_NOTIFICATION_PENDING_ALLOWED_PATHS:
                continue
            for index, line in enumerate(text.splitlines(), start=1):
                if LEGACY_NOTIFICATION_PENDING_PATTERN.search(line):
                    findings.append(
                        Finding(
                            rule_id="runtime_must_not_call_legacy_notification_pending_bridge",
                            severity="error",
                            path=doc_path,
                            line=index,
                            excerpt=line.strip()[:220],
                        )
                    )
    return findings


def legacy_notification_pending_callsite_self_test_findings() -> list[Finding]:
    return legacy_notification_pending_callsite_findings(
        {
            "frontend/lib/notifications.ts": (
                "return fetch('/v1/notifications/pending?channel=web');"
            ),
            "scripts/old_openclaw_poll.mjs": (
                "await apiFetch('/v1/notifications/pending?channel=openclaw');"
            ),
        }
    )


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


def non_owner_jarvis_tools_import_findings(
    extra_files: dict[str, str] | None = None,
) -> list[Finding]:
    """Fail closed if code imports the retired Jarvis/NIM tool island."""
    findings = scan_lines(
        rule_id="non_owner_services_must_not_import_jarvis_tools",
        severity="error",
        files=iter_files(REPO_ROOT / "backend" / "app", {".py"}),
        pattern=JARVIS_TOOLS_IMPORT_PATTERN,
        allowed_paths=JARVIS_TOOLS_IMPORT_ALLOWED_PATHS,
    )
    if extra_files:
        for doc_path, text in extra_files.items():
            if doc_path in JARVIS_TOOLS_IMPORT_ALLOWED_PATHS:
                continue
            for index, line in enumerate(text.splitlines(), start=1):
                if JARVIS_TOOLS_IMPORT_PATTERN.search(line):
                    findings.append(
                        Finding(
                            rule_id="non_owner_services_must_not_import_jarvis_tools",
                            severity="error",
                            path=doc_path,
                            line=index,
                            excerpt=line.strip()[:220],
                        )
                    )
    return findings


def non_owner_jarvis_tools_import_self_test_findings() -> list[Finding]:
    return non_owner_jarvis_tools_import_findings(
        {
            "backend/app/services/inference_engine.py": (
                "from app.services.jarvis_tools import _exec_analyze_behavioral_signature"
            )
        }
    )


def no_unapproved_rebrand_findings(
    extra_files: dict[str, str] | None = None,
) -> list[Finding]:
    """Prevent accidental Barzakh copy during the current no-rebrand cycle.

    This intentionally scans app-facing/runtime/public paths rather than docs
    history. Planning notes may discuss the deferred rename, but the browser,
    runtime scripts, metadata, public files, and CI surfaces must stay LyraOS
    until a fresh rebrand branch is explicitly approved.
    """
    findings: list[Finding] = []
    files: list[Path] = []
    for root in NO_UNAPPROVED_REBRAND_ROOTS:
        files.extend(iter_files(root, NO_UNAPPROVED_REBRAND_SUFFIXES))
    files.extend(path for path in NO_UNAPPROVED_REBRAND_FILES if path.exists())
    findings.extend(
        scan_lines(
            rule_id="no_unapproved_barzakh_rebrand_in_app_surfaces",
            severity="error",
            files=files,
            pattern=NO_UNAPPROVED_REBRAND_PATTERN,
            allowed_paths={"scripts/scan_refactor_contracts.py"},
        )
    )
    if extra_files:
        for doc_path, text in extra_files.items():
            for index, line in enumerate(text.splitlines(), start=1):
                if NO_UNAPPROVED_REBRAND_PATTERN.search(line):
                    findings.append(
                        Finding(
                            rule_id="no_unapproved_barzakh_rebrand_in_app_surfaces",
                            severity="error",
                            path=doc_path,
                            line=index,
                            excerpt=line.strip()[:220],
                        )
                    )
    return findings


def no_unapproved_rebrand_self_test_findings() -> list[Finding]:
    return no_unapproved_rebrand_findings(
        {
            "frontend/app/page.tsx": "export const metadata = { title: 'Barzakh' };",
            "backend/app/main.py": "APP_NAME = 'barzakh'",
        }
    )


def removed_surface_active_doc_findings(
    extra_docs: dict[str, str] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    docs: dict[str, str] = {}
    for doc_path in ACTIVE_DOC_REMOVED_SURFACE_PATTERNS:
        path = REPO_ROOT / doc_path
        try:
            docs[doc_path] = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
    if extra_docs:
        docs.update(extra_docs)

    for doc_path, text in docs.items():
        patterns = ACTIVE_DOC_REMOVED_SURFACE_PATTERNS.get(doc_path, ())
        lines = text.splitlines()
        for pattern in patterns:
            for index, line in enumerate(lines, start=1):
                if pattern.search(line):
                    findings.append(
                        Finding(
                            rule_id="active_docs_must_not_reauthorize_removed_surfaces",
                            severity="error",
                            path=doc_path,
                            line=index,
                            excerpt=line.strip()[:220],
                        )
                    )
                    break
    return findings


def removed_surface_active_doc_self_test_findings() -> list[Finding]:
    return removed_surface_active_doc_findings(
        {
            "docs/deployment_architecture.md": "Backend owns Notion sync and Notion retry queue.",
            "docs/architecture.md": "Current stack includes operator-only JARVIS/OpenClaw and Per-user Notion config.",
            "docs/runbooks/post_wave_dogfood_loop.md": "The runbook proves active Jarvis.",
            "docs/prodblueprint_security.md": "admin dashboards, alpha funnel, and degrade Notion sync on Notion unavailable.",
            "docs/integrations_architecture.md": "Use future notion_connect because notion_enabled`) is appropriate.",
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-on-errors", action="store_true")
    parser.add_argument("--include-review", action="store_true")
    parser.add_argument("--self-test-removed-surface-docs", action="store_true")
    parser.add_argument("--self-test-no-rebrand", action="store_true")
    parser.add_argument("--self-test-jarvis-import-boundary", action="store_true")
    parser.add_argument("--self-test-legacy-notification-pending", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    if args.self_test_legacy_notification_pending:
        findings = legacy_notification_pending_callsite_self_test_findings()
        output = {
            "ok": len(findings) >= 2,
            "mode": "self_test_legacy_notification_pending",
            "expected_minimum_findings": 2,
            "finding_count": len(findings),
            "findings": [finding.__dict__ for finding in findings],
        }
        print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
        return 0 if output["ok"] else 1

    if args.self_test_jarvis_import_boundary:
        findings = non_owner_jarvis_tools_import_self_test_findings()
        output = {
            "ok": len(findings) >= 1,
            "mode": "self_test_jarvis_import_boundary",
            "expected_minimum_findings": 1,
            "finding_count": len(findings),
            "findings": [finding.__dict__ for finding in findings],
        }
        print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
        return 0 if output["ok"] else 1

    if args.self_test_no_rebrand:
        findings = no_unapproved_rebrand_self_test_findings()
        output = {
            "ok": len(findings) >= 2,
            "mode": "self_test_no_rebrand",
            "expected_minimum_findings": 2,
            "finding_count": len(findings),
            "findings": [finding.__dict__ for finding in findings],
        }
        print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
        return 0 if output["ok"] else 1

    if args.self_test_removed_surface_docs:
        findings = removed_surface_active_doc_self_test_findings()
        output = {
            "ok": len(findings) >= len(ACTIVE_DOC_REMOVED_SURFACE_PATTERNS),
            "mode": "self_test_removed_surface_docs",
            "expected_minimum_findings": len(ACTIVE_DOC_REMOVED_SURFACE_PATTERNS),
            "finding_count": len(findings),
            "findings": [finding.__dict__ for finding in findings],
        }
        print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
        return 0 if output["ok"] else 1

    findings: list[Finding] = []
    findings.extend(worker_render_truth_findings())
    findings.extend(provider_completion_authority_findings())
    findings.extend(analytics_direct_exposure_findings())
    findings.extend(app_direct_output_surface_helper_findings())
    findings.extend(app_direct_legacy_reflection_row_findings())
    findings.extend(frontend_jarvis_findings())
    findings.extend(non_owner_jarvis_tools_import_findings())
    findings.extend(stale_doc_authority_banner_findings())
    findings.extend(removed_surface_active_doc_findings())
    findings.extend(no_unapproved_rebrand_findings())
    findings.extend(legacy_notification_pending_callsite_findings())
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
