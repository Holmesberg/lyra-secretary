from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_operator_readonly_verifier_uses_state_evidence_over_screenshot():
    script = (REPO_ROOT / "scripts" / "browser_stress_operator_readonly.mjs").read_text(
        encoding="utf-8"
    )

    assert "page.waitForFunction" in script
    assert "document.body?.innerText" in script
    assert "dashboard_snapshot_diffs" in script
    assert "route_count_diffs" in script
    assert "count_diffs" in script
