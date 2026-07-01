#!/usr/bin/env python3
"""Report mutation-capable files and their documented authority owner.

S1c may hard-fail selected precise findings once allowlists exist. The current
hard gates cover missing owner documentation and worker-job write drift.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "docs" / "registries" / "mutation_surface_authority_registry.json"

SCAN_ROOTS = [
    REPO_ROOT / "backend" / "app",
    REPO_ROOT / "openclaw",
    REPO_ROOT / "scripts",
]

INCLUDE_SUFFIXES = {".py", ".js", ".mjs", ".ts", ".tsx", ".json"}
SKIP_PARTS = {
    ".git",
    ".next",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "tmp",
}

MARKERS: dict[str, re.Pattern[str]] = {
    "db_commit": re.compile(r"\b(?:self\.)?db\.commit\s*\("),
    "db_delete": re.compile(r"\b(?:self\.)?db\.delete\s*\("),
    "query_delete": re.compile(r"\.delete\s*\(\s*synchronize_session"),
    "redis_delete": re.compile(r"\b(?:client|pipe)\.delete\s*\("),
    "redis_write": re.compile(r"\b(?:client|pipe)\.(?:set|setex|rpush|lpush|hset)\s*\("),
    "exposure_model_write": re.compile(
        r"\b(?:ExposureDecisionEvent|ExposureRenderEvent|ExposureAckEvent|SuppressionEvent)\s*\("
    ),
    "notification_model_write": re.compile(r"\bNotificationLifecycleEvent\s*\("),
    "provider_completion_model_write": re.compile(r"\bDeadlineCompletionEvent\s*\("),
    "calibration_model_write": re.compile(r"\bCalibrationNudgeEvent\s*\("),
}

WORKER_JOB_ALLOWED_MARKERS: dict[str, set[str]] = {
    "backend/app/workers/jobs/llm_enrichment.py": {"db_commit"},
    "backend/app/workers/jobs/moodle_submissions_sync.py": {"db_commit"},
    "backend/app/workers/jobs/notion_sync.py": {"db_commit"},
    "backend/app/workers/jobs/orphan_task_recovery.py": {"db_commit"},
    "backend/app/workers/jobs/overdue_tasks.py": {"db_commit"},
    "backend/app/workers/jobs/pause_prediction.py": {"db_commit"},
    "backend/app/workers/jobs/reconcile_deadline_outcomes.py": {"db_commit"},
    "backend/app/workers/jobs/reconcile_responses.py": {"db_commit"},
    "backend/app/workers/jobs/reminders.py": {"db_commit", "redis_write"},
    "backend/app/workers/jobs/resume_prediction.py": {"db_commit"},
    "backend/app/workers/jobs/stale_session_recovery.py": {"db_commit"},
    "backend/app/workers/jobs/sweep_missed_deadlines.py": {"db_commit"},
    "backend/app/workers/jobs/timer_overflow.py": {"db_commit", "redis_write"},
}


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def should_scan(path: Path) -> bool:
    if path.suffix not in INCLUDE_SUFFIXES:
        return False
    parts = set(path.parts)
    if parts & SKIP_PARTS:
        return False
    if path == Path(__file__).resolve():
        return False
    return True


def load_registry() -> list[dict[str, Any]]:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return list(data.get("surfaces", []))


def path_matches(pattern: str, candidate: str) -> bool:
    normalized = pattern.rstrip("/")
    if fnmatch.fnmatch(candidate, normalized):
        return True
    if candidate == normalized:
        return True
    return candidate.startswith(normalized + "/")


def owners_for(candidate: str, surfaces: list[dict[str, Any]]) -> list[dict[str, str]]:
    owners: list[dict[str, str]] = []
    for surface in surfaces:
        if any(path_matches(pattern, candidate) for pattern in surface.get("paths", [])):
            owners.append(
                {
                    "id": str(surface.get("id")),
                    "authority_level": str(surface.get("authority_level")),
                    "owner": str(surface.get("owner")),
                }
            )
    return owners


def scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    return [name for name, pattern in MARKERS.items() if pattern.search(text)]


def worker_write_drift(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    drift: list[dict[str, Any]] = []
    for item in findings:
        candidate = str(item["path"])
        if not candidate.startswith("backend/app/workers/jobs/"):
            continue
        markers = set(item["markers"])
        allowed = WORKER_JOB_ALLOWED_MARKERS.get(candidate)
        if allowed is None:
            drift.append({
                "path": candidate,
                "markers": sorted(markers),
                "allowed_markers": [],
                "reason": "worker job has mutation markers but is not in the S1c allowlist",
            })
            continue
        extra = sorted(markers - allowed)
        if extra:
            drift.append({
                "path": candidate,
                "markers": sorted(markers),
                "allowed_markers": sorted(allowed),
                "unexpected_markers": extra,
                "reason": "worker job gained mutation markers outside its S1c allowlist",
            })
    return drift


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-on-missing", action="store_true")
    parser.add_argument("--fail-on-worker-write-drift", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    surfaces = load_registry()
    findings: list[dict[str, Any]] = []

    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or not should_scan(path):
                continue
            markers = scan_file(path)
            if not markers:
                continue
            candidate = rel(path)
            owners = owners_for(candidate, surfaces)
            findings.append(
                {
                    "path": candidate,
                    "markers": markers,
                    "owners": owners,
                    "missing_owner": not owners,
                }
            )

    missing = [item for item in findings if item["missing_owner"]]
    worker_drift = worker_write_drift(findings)
    ok = not (
        (args.fail_on_missing and missing)
        or (args.fail_on_worker_write_drift and worker_drift)
    )
    modes = []
    if args.fail_on_missing:
        modes.append("fail_on_missing")
    if args.fail_on_worker_write_drift:
        modes.append("fail_on_worker_write_drift")
    output = {
        "ok": ok,
        "mode": "+".join(modes) if modes else "report_only",
        "registry": rel(REGISTRY_PATH),
        "scanned_roots": [rel(root) for root in SCAN_ROOTS if root.exists()],
        "marker_count": len(findings),
        "missing_owner_count": len(missing),
        "worker_write_drift_count": len(worker_drift),
        "worker_write_drift": worker_drift,
        "findings": findings,
    }
    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
    return 1 if not ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
