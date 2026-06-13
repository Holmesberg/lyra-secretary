from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "client_shadow_export_readonly.js"
PROTOCOL = ROOT / "docs" / "client_shadow_data_recovery_protocol.md"


def test_client_shadow_export_script_exists() -> None:
    assert SCRIPT.exists()
    assert PROTOCOL.exists()


def test_client_shadow_export_script_avoids_storage_mutation_calls() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    forbidden_fragments = [
        ".clear(",
        ".removeItem(",
        ".setItem(",
        "indexedDB.deleteDatabase",
        ".deleteDatabase(",
        "chrome.storage.local.clear",
        "chrome.storage.sync.clear",
        "chrome.storage.local.remove",
        "chrome.storage.sync.remove",
        "chrome.storage.local.set",
        "chrome.storage.sync.set",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in source


def test_client_shadow_recovery_protocol_points_to_canonical_script() -> None:
    text = PROTOCOL.read_text(encoding="utf-8")

    assert "scripts/client_shadow_export_readonly.js" in text
    assert "Do not ask an LLM to rewrite" in text
    assert "read-only" in text
