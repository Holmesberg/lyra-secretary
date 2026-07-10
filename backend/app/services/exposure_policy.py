"""Pure exposure horizon policy helpers.

This module owns versioned exposure-policy config loading and category horizon
lookup. It does not read behavioral rows, write state, or decide exposure
contamination.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_HORIZON_POLICY_VERSION = "exposure_horizon_v0"

SIGNAL_TARGETS = {
    "duration_behavior",
    "planning_estimate",
    "readiness_self_report",
    "reflection_self_report",
    "pause_behavior",
    "deadline_behavior",
}


def load_horizon_policy(version: str = DEFAULT_HORIZON_POLICY_VERSION) -> dict[str, Any]:
    """Load a versioned exposure horizon policy from JSON config.

    Keeping policy in data, not code branches, makes policy drift visible and
    testable. Callers should fail closed if the policy cannot be loaded.
    """
    path = Path(__file__).resolve().parents[1] / "core" / "exposure_horizon_policies.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data["policies"][version]


def affected_categories_for_target(
    policy: dict[str, Any], signal_target: str
) -> dict[str, int]:
    """Return exposure categories and horizons that can affect a signal target."""
    horizons = policy.get("horizons_minutes", {})
    supported_targets = set(policy.get("all_supported_targets", []))
    out: dict[str, int] = {}
    for category, target_map in horizons.items():
        if signal_target in target_map:
            out[category] = int(target_map[signal_target])
        elif (
            "all_supported_targets" in target_map
            and signal_target in supported_targets
        ):
            out[category] = int(target_map["all_supported_targets"])
    return out
