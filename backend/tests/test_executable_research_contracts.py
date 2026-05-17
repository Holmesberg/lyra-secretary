from pathlib import Path

from app.core.research_contracts import (
    CLEAN_DATA_PROFILES,
    EVIDENCE_CLASSES,
    FORBIDDEN_INFERENCE_INPUTS,
    PASSIVE_ACTIVITY_EVIDENCE_CLASS,
    PLANNING_CALIBRATION_PROFILE,
    PROVIDER_SPECIFIC_TERMS,
    SECURITY_AUDIT_MODEL_NAME,
    SUBSTRATE_PRIMITIVES,
)


APP_DIR = Path(__file__).resolve().parents[1] / "app"


def test_research_contract_vocabulary_names_core_boundaries():
    assert PASSIVE_ACTIVITY_EVIDENCE_CLASS in EVIDENCE_CLASSES
    assert PLANNING_CALIBRATION_PROFILE in CLEAN_DATA_PROFILES
    assert SECURITY_AUDIT_MODEL_NAME in FORBIDDEN_INFERENCE_INPUTS
    assert {
        "obligation",
        "intention",
        "execution_event",
        "outcome",
        "interruption",
        "exposure",
        "drift",
        "recalibration",
    } <= SUBSTRATE_PRIMITIVES


def test_cortex_and_clean_data_paths_do_not_branch_on_provider_names():
    """Provider-specific adapters may normalize data; Cortex stays provider-blind."""
    guarded_paths = [
        APP_DIR / "services" / "cortex.py",
    ]
    offenders: list[str] = []
    for path in guarded_paths:
        text = path.read_text(encoding="utf-8").lower()
        for term in PROVIDER_SPECIFIC_TERMS:
            if term in text:
                offenders.append(f"{path.relative_to(APP_DIR)}:{term}")

    assert offenders == []


def test_security_audit_model_is_forbidden_as_inference_input():
    """The audit table is governance-only, never behavioral telemetry."""
    behavioral_roots = [
        APP_DIR / "services",
        APP_DIR / "workers",
    ]
    allowed = {
        APP_DIR / "services" / "security_audit.py",
    }
    offenders: list[str] = []
    for root in behavioral_roots:
        for path in root.rglob("*.py"):
            if path in allowed:
                continue
            if SECURITY_AUDIT_MODEL_NAME in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(APP_DIR)))

    assert offenders == []
