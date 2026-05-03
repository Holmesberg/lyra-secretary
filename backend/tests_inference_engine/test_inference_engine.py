"""Unit tests for inference_engine — no DB/conftest (runs without full backend stack)."""

from app.services.inference_engine import (
    SIGNAL_THRESHOLDS,
    classify_disagreement,
    classify_task_valence,
    confidence_tier_from_n,
)
from app.db.models import Task


def test_default_confidence_tiers():
    assert confidence_tier_from_n(0) == "cold_start"
    assert confidence_tier_from_n(4) == "cold_start"
    assert confidence_tier_from_n(5) == "tentative"
    assert confidence_tier_from_n(29) == "tentative"
    assert confidence_tier_from_n(30) == "confirmed"


def test_override_thresholds_cascade():
    assert confidence_tier_from_n(2, "cascade_recovery_latency") == "cold_start"
    assert confidence_tier_from_n(3, "cascade_recovery_latency") == "tentative"
    assert confidence_tier_from_n(9, "cascade_recovery_latency") == "tentative"
    assert confidence_tier_from_n(10, "cascade_recovery_latency") == "confirmed"


def test_signal_thresholds_has_defaults_and_overrides():
    assert "_default" in SIGNAL_THRESHOLDS
    assert "cascade_recovery_latency" in SIGNAL_THRESHOLDS


def test_valence_flow_and_friction():
    t = Task()
    t.planned_duration_minutes = 10
    t.executed_duration_minutes = 20
    t.post_task_reflection = 5
    t.pause_count = 0
    assert classify_task_valence(t) == "flow"

    t2 = Task()
    t2.planned_duration_minutes = 10
    t2.executed_duration_minutes = 20
    t2.post_task_reflection = 2
    t2.pause_count = 4
    assert classify_task_valence(t2) == "friction"


def test_disagreement_optimism_collapse():
    t = Task()
    t.pre_task_readiness = 5
    t.post_task_reflection = 1
    assert classify_disagreement(t) == "optimism_collapse"
