"""Baseet-like provider deadline pressure scenarios."""
from __future__ import annotations

from datetime import datetime, timedelta

from scripts.lyrasim.models import HiddenState, ScenarioData, TraceEvent


SCENARIO_ID = "baseet_duplicate_stale_deadline_pressure"


def _deadline_event(
    *,
    title: str,
    due_in_days: int,
    external_id_hash: str,
    stale_state: str,
    minute: int,
) -> TraceEvent:
    return TraceEvent(
        event_type="provider_deadline_observed",
        occurred_at_minute=minute,
        payload={
            "provider_kind": "baseet",
            "external_source": "baseet_mock",
            "external_id_hash": external_id_hash,
            "title": title,
            "due_in_days": due_in_days,
            "category_hint": "academic",
            "state": "planned",
            "stale_state": stale_state,
            "provenance": "external_import",
            "evidence_class": "external_obligation",
            "authority_ceiling": "suggestion",
            "requires_safe_action": True,
        },
    )


def generate(seed: int) -> ScenarioData:
    base_due_at = datetime(2026, 5, 22, 12, 0, 0) + timedelta(
        minutes=seed % 60
    )
    trace = (
        TraceEvent(
            event_type="provider_sync_batch_started",
            occurred_at_minute=0,
            payload={
                "provider_kind": "baseet",
                "external_source": "baseet_mock",
                "sync_state": "partial_or_noisy",
                "provenance": "external_import",
                "evidence_class": "external_obligation",
                "authority_ceiling": "suggestion",
            },
        ),
        _deadline_event(
            title="Assignment 1",
            due_in_days=2,
            external_id_hash="hash_baseet_assignment_1_v1",
            stale_state="possibly_stale_prior_due_date",
            minute=1,
        ),
        _deadline_event(
            title="Assignment 1",
            due_in_days=3,
            external_id_hash="hash_baseet_assignment_1_v2",
            stale_state="possible_duplicate_changed_due_date",
            minute=2,
        ),
        _deadline_event(
            title="Quiz",
            due_in_days=3,
            external_id_hash="hash_baseet_vague_quiz",
            stale_state="vague_title_needs_course_mapping",
            minute=3,
        ),
    )
    return ScenarioData(
        scenario_id=SCENARIO_ID,
        scenario_version=f"{SCENARIO_ID}:v0",
        scenario_origin="repo_derived",
        seed=seed,
        synthetic_user_id=f"synthetic_{seed % 997:03d}",
        hidden_state=HiddenState(
            user_activity="unknown",
            intended_activity="unknown",
            notes=(
                "Provider batch contains duplicate/stale-looking academic "
                "deadlines; hidden truth is not available to product seams."
            ),
        ),
        observable_trace=trace,
        generator_assumptions=(
            "Baseet deadline rows are academic structure, not accepted intention.",
            "Duplicate or stale provider deadlines can inflate pressure if not bounded by trust state.",
            "Synthetic external IDs are hashes, not raw provider IDs.",
            f"Fixture base timestamp is {base_due_at.isoformat()} for deterministic due offsets.",
        ),
        coverage_limitations=(
            "This scenario does not validate live Baseet import behavior.",
            "This scenario does not validate passive resource progress.",
            "This scenario validates the pressure-map seam after rows exist.",
        ),
        expected_resolution_rung="clarify_or_repair",
    )
