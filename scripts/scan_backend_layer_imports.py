#!/usr/bin/env python3
"""Hard gate for backend layer import direction.

This is intentionally small. It enforces only stable dependency-direction
rules that are currently clean, so the gate protects future refactors without
turning architecture work into broad lint ceremony.
"""
from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]

SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "tmp",
}


@dataclass(frozen=True)
class Rule:
    rule_id: str
    root: str
    forbidden_prefixes: tuple[str, ...]
    allowed_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class Finding:
    rule_id: str
    path: str
    line: int
    import_name: str
    forbidden_prefix: str


RULES: tuple[Rule, ...] = (
    Rule(
        "db_must_not_import_upper_layers",
        "backend/app/db",
        ("app.api", "app.services", "app.workers", "app.main"),
    ),
    Rule(
        "schemas_must_not_import_runtime_layers",
        "backend/app/schemas",
        ("app.api", "app.services", "app.workers", "app.main"),
    ),
    Rule(
        "services_must_not_import_api_or_main",
        "backend/app/services",
        ("app.api", "app.main"),
    ),
    Rule(
        "utils_must_not_import_api_or_workers",
        "backend/app/utils",
        ("app.api", "app.workers", "app.main"),
    ),
)


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def should_scan(path: Path) -> bool:
    return (
        path.suffix == ".py"
        and path.is_file()
        and not (set(path.parts) & SKIP_PARTS)
    )


def iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    for path in root.rglob("*.py"):
        if should_scan(path):
            yield path


def path_matches_root(candidate: str, root: str) -> bool:
    return candidate == root or candidate.startswith(root.rstrip("/") + "/")


def forbidden_match(import_name: str, prefixes: tuple[str, ...]) -> str | None:
    for prefix in prefixes:
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


def scan_source(candidate: str, text: str, rules: tuple[Rule, ...] = RULES) -> list[Finding]:
    findings: list[Finding] = []
    try:
        tree = ast.parse(text, filename=candidate)
    except SyntaxError as exc:
        findings.append(
            Finding(
                rule_id="python_parse_error",
                path=candidate,
                line=exc.lineno or 0,
                import_name=exc.msg,
                forbidden_prefix="parse_error",
            )
        )
        return findings

    applicable = [
        rule
        for rule in rules
        if path_matches_root(candidate, rule.root) and candidate not in rule.allowed_paths
    ]
    if not applicable:
        return []

    for line, import_name in imported_names(tree):
        for rule in applicable:
            prefix = forbidden_match(import_name, rule.forbidden_prefixes)
            if prefix is None:
                continue
            findings.append(
                Finding(
                    rule_id=rule.rule_id,
                    path=candidate,
                    line=line,
                    import_name=import_name,
                    forbidden_prefix=prefix,
                )
            )
    return findings


def scan_repo() -> list[Finding]:
    findings: list[Finding] = []
    for rule in RULES:
        root = REPO_ROOT / rule.root
        for path in iter_files(root):
            candidate = rel(path)
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                findings.append(
                    Finding(
                        rule_id="read_error",
                        path=candidate,
                        line=0,
                        import_name=str(exc),
                        forbidden_prefix="read_error",
                    )
                )
                continue
            findings.extend(scan_source(candidate, text, (rule,)))
    return findings


def finding_dict(finding: Finding) -> dict[str, object]:
    return {
        "rule_id": finding.rule_id,
        "path": finding.path,
        "line": finding.line,
        "import_name": finding.import_name,
        "forbidden_prefix": finding.forbidden_prefix,
    }


def run_self_test() -> None:
    good = scan_source(
        "backend/app/services/good.py",
        "from app.db import models\nfrom app.services import cortex\n",
        RULES,
    )
    bad = scan_source(
        "backend/app/services/bad.py",
        "from app.api.v1.endpoints import tasks\n",
        RULES,
    )
    db_bad = scan_source(
        "backend/app/db/bad_model.py",
        "import app.services.task_manager\n",
        RULES,
    )
    if good:
        raise AssertionError(f"self-test good source produced findings: {good!r}")
    if len(bad) != 1 or bad[0].rule_id != "services_must_not_import_api_or_main":
        raise AssertionError(f"self-test failed to catch service->api import: {bad!r}")
    if len(db_bad) != 1 or db_bad[0].rule_id != "db_must_not_import_upper_layers":
        raise AssertionError(f"self-test failed to catch db->services import: {db_bad!r}")


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
        "rules": [
            {
                "rule_id": rule.rule_id,
                "root": rule.root,
                "forbidden_prefixes": list(rule.forbidden_prefixes),
                "allowed_paths": list(rule.allowed_paths),
            }
            for rule in RULES
        ],
    }
    print(json.dumps(payload, indent=2 if args.pretty else None))
    if args.fail_on_errors and findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
