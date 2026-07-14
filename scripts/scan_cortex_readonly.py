#!/usr/bin/env python3
"""Hard gate for the Cortex read-only boundary.

Cortex is a read-time projection layer. This scanner intentionally enforces
only stable, mechanical rules that are clean today: no ORM write primitives,
no Redis/Notion writes, and no imports of known writer managers.
"""
from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]

CORTEX_PATHS = (
    "backend/app/services/cortex.py",
    "backend/app/services/cortex_clean_profiles.py",
    "backend/app/services/cortex",
)

FORBIDDEN_CALL_ATTRS = {
    "add",
    "add_all",
    "bulk_save_objects",
    "commit",
    "delete",
    "execute",
    "flush",
    "merge",
    "set",
    "setex",
}

WRITE_RECEIVER_ROOTS = {
    "cache",
    "client",
    "db",
    "notion",
    "notion_client",
    "redis",
    "redis_client",
    "session",
}

FORBIDDEN_IMPORT_PREFIXES = (
    "app.services.calendar_sync",
    "app.services.deadline_manager",
    "app.services.moodle_ics_sync",
    "app.services.moodle_submissions_sync",
    "app.services.notion",
    "app.services.task_manager",
    "app.services.stopwatch_manager",
    "notion_client",
    "redis",
)


@dataclass(frozen=True)
class Finding:
    rule_id: str
    path: str
    line: int
    symbol: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def cortex_files() -> Iterable[Path]:
    for raw in CORTEX_PATHS:
        path = REPO_ROOT / raw
        if path.is_file() and path.suffix == ".py":
            yield path
        elif path.is_dir():
            yield from sorted(path.rglob("*.py"))


def forbidden_import_match(import_name: str) -> str | None:
    for prefix in FORBIDDEN_IMPORT_PREFIXES:
        if import_name == prefix or import_name.startswith(prefix + "."):
            return prefix
    return None


def imported_names(tree: ast.AST) -> Iterable[tuple[int, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.lineno, node.module


def receiver_root(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return receiver_root(node.value)
    if isinstance(node, ast.Call):
        return receiver_root(node.func)
    return None


def scan_source(path: str, text: str) -> list[Finding]:
    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError as exc:
        return [
            Finding(
                rule_id="python_parse_error",
                path=path,
                line=exc.lineno or 0,
                symbol=exc.msg,
                detail="parse_error",
            )
        ]

    findings: list[Finding] = []

    for line, import_name in imported_names(tree):
        prefix = forbidden_import_match(import_name)
        if prefix is None:
            continue
        findings.append(
            Finding(
                rule_id="cortex_forbidden_writer_import",
                path=path,
                line=line,
                symbol=import_name,
                detail=f"matched forbidden import prefix {prefix}",
            )
        )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        name = node.func.attr
        root = receiver_root(node.func.value)
        if name not in FORBIDDEN_CALL_ATTRS or root not in WRITE_RECEIVER_ROOTS:
            continue
        findings.append(
            Finding(
                rule_id="cortex_forbidden_write_call",
                path=path,
                line=getattr(node, "lineno", 0),
                symbol=f"{root}.{name}",
                detail="Cortex must remain read-only",
            )
        )

    return findings


def scan_repo() -> list[Finding]:
    findings: list[Finding] = []
    for path in cortex_files():
        candidate = rel(path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                Finding(
                    rule_id="read_error",
                    path=candidate,
                    line=0,
                    symbol=str(exc),
                    detail="read_error",
                )
            )
            continue
        findings.extend(scan_source(candidate, text))
    return findings


def finding_dict(finding: Finding) -> dict[str, object]:
    return {
        "rule_id": finding.rule_id,
        "path": finding.path,
        "line": finding.line,
        "symbol": finding.symbol,
        "detail": finding.detail,
    }


def run_self_test() -> None:
    good = scan_source(
        "backend/app/services/cortex.py",
        "from app.db.models import Task\n"
        "def project(db):\n"
        "    labels = set()\n"
        "    labels.add('unknown')\n"
        "    return db.query(Task).all()\n",
    )
    write_bad = scan_source(
        "backend/app/services/cortex.py",
        "def repair(db, task):\n"
        "    db.add(task)\n"
        "    db.commit()\n",
    )
    import_bad = scan_source(
        "backend/app/services/cortex.py",
        "from app.services.task_manager import create_task\n",
    )
    if good:
        raise AssertionError(f"self-test good source produced findings: {good!r}")
    if len(write_bad) != 2:
        raise AssertionError(f"self-test failed to catch write calls: {write_bad!r}")
    if len(import_bad) != 1 or import_bad[0].rule_id != "cortex_forbidden_writer_import":
        raise AssertionError(f"self-test failed to catch writer import: {import_bad!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-on-errors", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        print(json.dumps({"ok": True, "self_test": True}, indent=2 if args.pretty else None))
        return 0

    findings = scan_repo()
    payload = {
        "ok": not findings,
        "finding_count": len(findings),
        "findings": [finding_dict(finding) for finding in findings],
        "scanned_paths": list(CORTEX_PATHS),
        "forbidden_call_attrs": sorted(FORBIDDEN_CALL_ATTRS),
        "forbidden_import_prefixes": list(FORBIDDEN_IMPORT_PREFIXES),
    }
    print(json.dumps(payload, indent=2 if args.pretty else None))
    if args.fail_on_errors and findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
