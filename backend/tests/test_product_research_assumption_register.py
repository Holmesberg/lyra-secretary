"""Product/research assumption-register contract checks."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "product_research_assumption_register.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_assumption_register_names_validation_and_falsification_contract():
    text = _read(DOC)

    required = [
        "assumption",
        "operational hypothesis",
        "observable variables",
        "validation path",
        "falsification signal",
        "No assumption becomes a product claim",
        "investor diligence",
    ]
    for phrase in required:
        assert phrase in text


def test_assumption_register_preserves_core_product_research_boundaries():
    text = _read(DOC)

    required = [
        "Accepted intention matters.",
        "Passive activity is weak evidence",
        "`planning_calibration`",
        "Exposure contaminates future behavior.",
        "Provider data is structure, not execution truth.",
        "Provider failure must degrade functionality, not auth or scoping.",
        "`SecurityAuditEvent`",
        "BCI signals become more useful when grounded in longitudinal behavioral traces.",
        "BCI is complementary evidence, not truth authority.",
    ]
    for phrase in required:
        assert phrase in text


def test_assumption_register_supports_investor_review_without_overclaiming():
    text = _read(DOC)

    required = [
        "The investor-relevant thesis is not that every assumption is true today.",
        "Potential moat candidates if validated:",
        "Primary risks:",
        "Current mitigation strategy:",
        "trusted-alpha research-instrument mode",
    ]
    for phrase in required:
        assert phrase in text


def test_manifesto_links_assumption_register_as_active_governance():
    manifesto = _read(ROOT / "MANIFESTO.md")

    assert "docs/product_research_assumption_register.md" in manifesto
    assert "assumption, hypothesis, validation, falsification" in manifesto
