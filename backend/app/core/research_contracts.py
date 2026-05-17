"""Executable research/security contract vocabulary.

Docs explain why these invariants exist. This module gives tests and services
one place to import the canonical names so the boundary can fail closed.
"""
from __future__ import annotations

from typing import Final

EVIDENCE_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "external_obligation",
        "passive_activity",
        "planned_block",
        "user_confirmed_plan",
        "abandoned_candidate",
    }
)

CLEAN_DATA_PROFILES: Final[frozenset[str]] = frozenset(
    {
        "planning_calibration",
        "measured_execution",
        "pause_process",
        "descriptive_history",
    }
)

SUBSTRATE_PRIMITIVES: Final[frozenset[str]] = frozenset(
    {
        "obligation",
        "intention",
        "execution_event",
        "outcome",
        "interruption",
        "exposure",
        "drift",
        "recalibration",
    }
)

FORBIDDEN_INFERENCE_INPUTS: Final[frozenset[str]] = frozenset(
    {
        "SecurityAuditEvent",
        "raw_provider_auth_state",
        "passive_activity_without_confirmed_intention",
    }
)

PROVIDER_SPECIFIC_TERMS: Final[frozenset[str]] = frozenset(
    {
        "baseet",
        "blackboard",
        "calendar",
        "canvas",
        "google",
        "google_calendar",
        "jira",
        "moodle",
        "notion",
    }
)

PASSIVE_ACTIVITY_EVIDENCE_CLASS: Final[str] = "passive_activity"
PLANNING_CALIBRATION_PROFILE: Final[str] = "planning_calibration"
SECURITY_AUDIT_MODEL_NAME: Final[str] = "SecurityAuditEvent"
