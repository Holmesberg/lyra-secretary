"""Shared read-only metric metadata helpers for operator dashboard packets."""
from __future__ import annotations

from typing import Any


def metric_meta(
    *,
    basis: str = "derived",
    confidence: str = "medium",
    readiness_impact: str = "informational",
    safe_to_ignore_when: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "basis": basis,
        "confidence": confidence,
        "readiness_impact": readiness_impact,
    }
    if safe_to_ignore_when:
        payload["safe_to_ignore_when"] = safe_to_ignore_when
    return payload
