#!/usr/bin/env python3
"""Hard gate for the shipped-feature preservation registry."""
from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "docs/registries/shipped_feature_preservation_registry.json"
OUTPUT_REGISTRY_PATH = REPO_ROOT / "backend/app/core/output_surface_registry.json"

ALLOWED_STATUSES = {"shipped", "partial", "dead_code", "historical", "parked"}
ALLOWED_FACET_STATUSES = {
    "shipped",
    "partial",
    "dead_code",
    "historical",
    "parked",
    "absent",
    "not_applicable",
}
FACETS = {"computation", "delivery", "ui", "mutation"}
NON_AUTHORIZING_CONTRACT_PREFIXES = (
    "docs/archive/",
    "docs/parked/",
    "docs/concepts/",
)
NON_AUTHORIZING_CONTRACT_FILES = {"docs/parked_ideas.md"}

REQUIRED_FEATURE_IDS = {
    "account.delete",
    "account.export",
    "ai.direct_model_runtime",
    "capture.minimal_quick_add",
    "execution.future_task_warning_ui",
    "execution.stop_result_outputs",
    "execution.stopwatch_lifecycle",
    "insights.archetype_profile_reveal",
    "insights.deterministic_page",
    "integrations.freshness",
    "integrations.google_calendar",
    "integrations.moodle_ical",
    "integrations.moodle_ws_submissions",
    "integrations.provider_expansion",
    "notifications.reminders",
    "notifications.timer_overflow",
    "notifications.web_lifecycle",
    "onboarding.archetype_survey",
    "onboarding.brain_dump",
    "onboarding.consent",
    "onboarding.tutorial_revival",
    "operator.new_dashboards",
    "operator.readiness_cockpit",
    "planning.adaptive_scheduling",
    "planning.pressure_map",
    "planning.task_dependency_graph",
    "predictions.next_task_readiness",
    "predictions.pause",
    "predictions.pause_action_banner",
    "predictions.resume",
    "predictions.resume_action_banner",
    "predictions.task_end",
    "recovery.interruption_chain_visualization",
    "recovery.reentry_queue",
    "recovery.retroactive_confirmation",
    "research.passive_capture",
    "settings.control_surface",
    "tasks.conflict_override",
    "tasks.deterministic_deadline_suggestion",
    "tasks.new_task_capture",
    "views.calendar_schedule",
    "views.deadlines_workspace",
    "views.pulse_hub",
    "views.table_audit",
    "views.today_execution",
}


@dataclass(frozen=True)
class Finding:
    rule_id: str
    feature_id: str
    detail: str


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add(findings: list[Finding], rule_id: str, feature_id: str, detail: str) -> None:
    findings.append(Finding(rule_id=rule_id, feature_id=feature_id, detail=detail))


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def referenced_path_findings(
    paths: Any,
    *,
    feature_id: str,
    field: str,
) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(paths, list):
        add(findings, "invalid_path_list", feature_id, f"{field} must be a list")
        return findings
    for raw_path in paths:
        if not is_nonempty_string(raw_path):
            add(findings, "invalid_path", feature_id, f"{field} contains a blank path")
            continue
        if not (REPO_ROOT / raw_path).is_file():
            add(findings, "referenced_path_missing", feature_id, f"{field}: {raw_path}")
    return findings


def validate_registry(
    registry: dict[str, Any],
    *,
    output_surface_ids: set[str],
) -> list[Finding]:
    findings: list[Finding] = []
    if registry.get("schema_version") != "shipped_feature_preservation_registry_v1":
        add(findings, "invalid_schema_version", "<registry>", str(registry.get("schema_version")))

    features = registry.get("features")
    if not isinstance(features, list):
        add(findings, "features_must_be_list", "<registry>", "features is not a list")
        return findings

    seen: set[str] = set()
    for index, feature in enumerate(features):
        if not isinstance(feature, dict):
            add(findings, "feature_must_be_object", f"<index:{index}>", repr(feature))
            continue
        feature_id = feature.get("id")
        if not is_nonempty_string(feature_id):
            add(findings, "feature_id_required", f"<index:{index}>", "missing id")
            continue
        if feature_id in seen:
            add(findings, "duplicate_feature_id", feature_id, "id appears more than once")
        seen.add(feature_id)

        status = feature.get("status")
        if status not in ALLOWED_STATUSES:
            add(findings, "invalid_status", feature_id, repr(status))

        facets = feature.get("facets")
        if not isinstance(facets, dict) or set(facets) != FACETS:
            add(findings, "invalid_facets", feature_id, f"expected {sorted(FACETS)}")
        else:
            for facet, facet_status in facets.items():
                if facet_status not in ALLOWED_FACET_STATUSES:
                    add(findings, "invalid_facet_status", feature_id, f"{facet}: {facet_status!r}")
            if status == "partial" and all(value == "shipped" for value in facets.values()):
                add(
                    findings,
                    "partial_feature_must_expose_partial_facet",
                    feature_id,
                    "all facets are shipped",
                )

        preservation_required = feature.get("preservation_required")
        if not isinstance(preservation_required, bool):
            add(findings, "preservation_required_must_be_boolean", feature_id, repr(preservation_required))
        elif status in {"shipped", "partial"} and not preservation_required:
            add(findings, "active_feature_must_be_preserved", feature_id, status)
        elif status in {"dead_code", "historical", "parked"} and preservation_required:
            add(findings, "inactive_feature_must_not_claim_preservation", feature_id, status)

        for field in ("name", "owner", "user_effect", "exposure_class", "rollback"):
            if not is_nonempty_string(feature.get(field)):
                add(findings, "required_text_missing", feature_id, field)
        for field in ("writes", "output_surface_ids", "historical_sources", "known_gaps"):
            if not isinstance(feature.get(field), list):
                add(findings, "required_list_missing", feature_id, field)

        active_contracts = feature.get("active_contracts")
        findings.extend(
            referenced_path_findings(active_contracts, feature_id=feature_id, field="active_contracts")
        )
        if status in {"shipped", "partial"} and not active_contracts:
            add(findings, "active_contract_required", feature_id, status)
        for contract in active_contracts or []:
            if contract in NON_AUTHORIZING_CONTRACT_FILES or contract.startswith(
                NON_AUTHORIZING_CONTRACT_PREFIXES
            ):
                add(findings, "active_contract_must_not_be_historical", feature_id, contract)

        runtime_paths = feature.get("runtime_paths")
        findings.extend(
            referenced_path_findings(runtime_paths, feature_id=feature_id, field="runtime_paths")
        )
        if status in {"shipped", "partial"} and not runtime_paths:
            add(findings, "active_runtime_path_required", feature_id, status)

        proof = feature.get("proof")
        if not isinstance(proof, dict):
            add(findings, "proof_required", feature_id, repr(proof))
            continue
        tests = proof.get("tests")
        browser = proof.get("browser")
        gated = proof.get("gated")
        findings.extend(referenced_path_findings(tests, feature_id=feature_id, field="proof.tests"))
        if not isinstance(browser, list):
            add(findings, "browser_proof_must_be_list", feature_id, repr(browser))
            browser = []
        if not isinstance(gated, list):
            add(findings, "gated_paths_must_be_list", feature_id, repr(gated))
            gated = []
        if status in {"shipped", "partial"} and not tests:
            add(findings, "active_characterization_test_required", feature_id, status)
        if status in {"shipped", "partial"} and not browser and not gated:
            add(findings, "browser_path_or_gate_required", feature_id, status)

        for entry in browser:
            if not isinstance(entry, dict):
                add(findings, "browser_proof_must_be_object", feature_id, repr(entry))
                continue
            script = entry.get("script")
            check = entry.get("check")
            if not is_nonempty_string(script) or not is_nonempty_string(check):
                add(findings, "browser_proof_fields_required", feature_id, repr(entry))
                continue
            script_path = REPO_ROOT / script
            if not script_path.is_file():
                add(findings, "referenced_path_missing", feature_id, f"proof.browser: {script}")
                continue
            if check not in script_path.read_text(encoding="utf-8", errors="ignore"):
                add(findings, "browser_check_missing", feature_id, f"{script}: {check}")

        for surface_id in feature.get("output_surface_ids") or []:
            if surface_id not in output_surface_ids:
                add(findings, "unknown_output_surface", feature_id, str(surface_id))
        if status in {"dead_code", "historical", "parked"} and feature.get("output_surface_ids"):
            add(findings, "inactive_feature_must_not_claim_output_surface", feature_id, status)

        historical_sources = feature.get("historical_sources") or []
        for source in historical_sources:
            if not isinstance(source, dict):
                add(findings, "historical_source_must_be_object", feature_id, repr(source))
                continue
            path = source.get("path")
            use = source.get("use")
            if not is_nonempty_string(path) or not is_nonempty_string(use):
                add(findings, "historical_source_fields_required", feature_id, repr(source))
            elif not (REPO_ROOT / path).is_file():
                add(findings, "referenced_path_missing", feature_id, f"historical_sources: {path}")

    for missing_id in sorted(REQUIRED_FEATURE_IDS - seen):
        add(findings, "required_feature_missing", missing_id, "required Wave 1 coverage")
    return findings


def output_surface_ids() -> set[str]:
    registry = load_json(OUTPUT_REGISTRY_PATH)
    surfaces = registry.get("surfaces")
    if not isinstance(surfaces, dict):
        raise ValueError("output surface registry must contain an object named surfaces")
    return set(surfaces)


def run_self_test() -> None:
    registry = load_json(REGISTRY_PATH)
    surfaces = output_surface_ids()
    baseline = validate_registry(registry, output_surface_ids=surfaces)
    if baseline:
        raise AssertionError(f"real registry is not a valid self-test baseline: {baseline!r}")

    cases: list[tuple[str, dict[str, Any], str]] = []

    missing = copy.deepcopy(registry)
    missing["features"] = [row for row in missing["features"] if row["id"] != "onboarding.consent"]
    cases.append(("missing required row", missing, "required_feature_missing"))

    bad_contract = copy.deepcopy(registry)
    bad_contract["features"][0]["active_contracts"] = ["docs/archive/AGENT_HANDOFF.md"]
    cases.append(("historical active contract", bad_contract, "active_contract_must_not_be_historical"))

    bad_status = copy.deepcopy(registry)
    bad_status["features"][0]["status"] = "probably_shipped"
    cases.append(("invalid status", bad_status, "invalid_status"))

    bad_surface = copy.deepcopy(registry)
    bad_surface["features"][0]["output_surface_ids"] = ["missing.surface"]
    cases.append(("unknown surface", bad_surface, "unknown_output_surface"))

    bad_browser = copy.deepcopy(registry)
    target = next(row for row in bad_browser["features"] if row["proof"]["browser"])
    target["proof"]["browser"][0]["check"] = "definitely-not-a-real-browser-check"
    cases.append(("missing browser check", bad_browser, "browser_check_missing"))

    bad_partial = copy.deepcopy(registry)
    target = next(row for row in bad_partial["features"] if row["status"] == "partial")
    target["facets"] = {facet: "shipped" for facet in FACETS}
    cases.append(("partial without partial facet", bad_partial, "partial_feature_must_expose_partial_facet"))

    bad_path = copy.deepcopy(registry)
    bad_path["features"][0]["runtime_paths"] = ["missing/runtime/path.py"]
    cases.append(("missing runtime path", bad_path, "referenced_path_missing"))

    for name, candidate, expected_rule in cases:
        rules = {finding.rule_id for finding in validate_registry(candidate, output_surface_ids=surfaces)}
        if expected_rule not in rules:
            raise AssertionError(f"{name} did not trigger {expected_rule}: {sorted(rules)}")


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

    findings = validate_registry(load_json(REGISTRY_PATH), output_surface_ids=output_surface_ids())
    payload = {
        "ok": not findings,
        "finding_count": len(findings),
        "findings": [asdict(finding) for finding in findings],
        "required_feature_count": len(REQUIRED_FEATURE_IDS),
    }
    print(json.dumps(payload, indent=2 if args.pretty else None))
    if args.fail_on_errors and findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
