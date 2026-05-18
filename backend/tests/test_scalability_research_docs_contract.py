"""Scalability/research doctrine contract checks."""
from __future__ import annotations

from pathlib import Path

from app.core.research_contracts import SCALABILITY_RISK_PRIORITIES


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_scalability_risk_priorities_are_named_in_executable_contracts():
    assert SCALABILITY_RISK_PRIORITIES == (
        "provider_adapter_contract",
        "drift_rollup_contract",
    )


def test_provider_adapter_contract_freezes_core_leakage_boundary():
    text = _read(DOCS / "provider_adapter_contract.md")

    required = [
        "Adapters translate local dialects.",
        "Core reasons in provider-blind primitives.",
        "Provider failure must degrade functionality, not weaken authentication or user",
        "Provider outage paths must not create trusted execution evidence.",
        "planning calibration unless the user accepted or confirmed an",
    ]
    for phrase in required:
        assert phrase in text


def test_drift_rollup_contract_requires_runtime_trigger_before_materialization():
    text = _read(DOCS / "drift_rollup_contract.md")

    required = [
        "Do not materialize drift rollups until runtime evidence shows read-time",
        "Materialized rollups are derived values, not observed truth.",
        "Rollup existence does not authorize",
        "metric version must change",
        "Redis may cache rollup reads for product latency, but it is not the source of",
    ]
    for phrase in required:
        assert phrase in text


def test_friction_methodology_doc_preserves_research_product_breakthroughs():
    text = _read(DOCS / "research_optionality_and_friction_methodology.md")

    required = [
        "The architecture was shaped by friction, not isolated theorizing.",
        "reality collision",
        "validity threat",
        "architectural response",
        "executable invariant",
        "Product friction reveals measurement threats.",
        "Research constraints harden product behavior.",
        "longitudinal behavioral traces can semantically ground noisy cognitive-state",
        "No new features unless they fix a boundary, test an invariant, or reduce",
    ]
    for phrase in required:
        assert phrase in text


def test_manifesto_links_new_scalability_and_methodology_docs():
    text = _read(ROOT / "MANIFESTO.md")

    required = [
        "Friction-Tested Instrument Methodology",
        "docs/provider_adapter_contract.md",
        "docs/drift_rollup_contract.md",
        "docs/research_optionality_and_friction_methodology.md",
        "reality collision",
        "validity threat",
        "executable invariant",
    ]
    for phrase in required:
        assert phrase in text
