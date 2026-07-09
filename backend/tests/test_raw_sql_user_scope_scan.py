"""Static guard for raw SQL user scoping.

The ORM scoping hook cannot rewrite db.execute(text(...)) calls. Raw SQL that
touches user-owned tables must therefore carry an explicit user predicate or
be deliberately allowlisted with a reason.
"""
from __future__ import annotations

from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "app"

USER_OWNED_TABLES = {
    "archetype_assignment",
    "calibration_nudge_event",
    "deadline",
    "deadline_completion_event",
    "exposure_ack_event",
    "exposure_decision_event",
    "exposure_policy_effect_log",
    "exposure_render_event",
    "external_event_outcome",
    "feedback",
    "jarvis_invocation",
    "pause_event",
    "pause_prediction_log",
    "reflection_view_log",
    "resume_prediction_log",
    "stopwatch_session",
    "suppression_event",
    "task",
    "task_deadline_outcome",
    "task_execution_correction",
    "user",
}

ALLOWLIST = {
    # Environment probes only; they do not read/write user-owned tables.
    ("main.py", "SELECT 1"),
    ("api/v1/endpoints/health.py", "SELECT now() AT TIME ZONE 'UTC'"),
    ("api/v1/endpoints/health.py", "information_schema.columns"),
}


def _raw_sql_blocks(path: Path) -> list[tuple[int, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        window = "\n".join(lines[idx : idx + 35])
        if "execute(" not in line:
            continue
        if "text(" not in window[:240]:
            continue
        blocks.append((idx + 1, window))
    return blocks


def _is_allowlisted(rel: str, block: str) -> bool:
    return any(rel == path and marker in block for path, marker in ALLOWLIST)


def test_raw_sql_touching_user_owned_tables_is_explicitly_scoped():
    offenders: list[str] = []
    for path in APP_DIR.rglob("*.py"):
        rel = path.relative_to(APP_DIR).as_posix()
        for line_no, block in _raw_sql_blocks(path):
            lowered = block.lower()
            if _is_allowlisted(rel, block):
                continue
            touched = sorted(
                table for table in USER_OWNED_TABLES if table in lowered
            )
            if not touched:
                continue
            scoped = (
                "user_id = :u" in lowered
                or "user_id=:u" in lowered
                or "where user_id" in lowered
                or "current_user_id" in lowered
            )
            if not scoped:
                offenders.append(
                    f"{rel}:{line_no} touches {touched} without explicit user scope"
                )

    assert offenders == []
