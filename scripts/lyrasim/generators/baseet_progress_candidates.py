"""Baseet-like provider-progress ambiguity scenarios."""
from __future__ import annotations

import random

from scripts.lyrasim.models import HiddenState, ScenarioData, TraceEvent


STALE_PROGRESS_SCENARIO_ID = "baseet_stale_task_progress_candidate"
BACKGROUND_VIDEO_SCENARIO_ID = "baseet_background_video_fakeout"
MULTIDEVICE_UPLOAD_SCENARIO_ID = "baseet_multidevice_upload_collision"
REVERSE_PROGRESS_SCENARIO_ID = "baseet_reverse_progress_signal"


def _ids(seed: int) -> tuple[str, str, str, str]:
    rng = random.Random(seed)
    return (
        f"synthetic_{rng.randrange(1, 999999):06d}",
        f"task_{rng.randrange(1, 999999):06d}",
        f"resource_{rng.randrange(1, 999999):06d}",
        f"course_{rng.randrange(1, 999999):06d}",
    )


def _common_assumptions() -> tuple[str, ...]:
    return (
        "Provider progress is represented as provider_progress_candidate, not execution_progress.",
        "Provider progress may support a recovery prompt, not task execution truth.",
        "Provider progress must not enter measured_execution or planning_calibration.",
    )


def _common_limitations() -> tuple[str, ...]:
    return (
        "This scenario does not validate live Baseet integration.",
        "This scenario does not capture real browser or device telemetry.",
        "This scenario does not authorize runtime task-state mutation.",
    )


def _progress_payload(
    *,
    resource_id_hash: str,
    course_id_hash: str,
    progress_kind: str,
    authority_ceiling: str = "suggestion",
) -> dict:
    return {
        "provider_kind": "baseet_like",
        "provider_item_type": "academic_resource",
        "resource_id_hash": resource_id_hash,
        "course_id_hash": course_id_hash,
        "evidence_class": "provider_progress_candidate",
        "provenance": "external_import",
        "trust_state": "ambiguous_provider_progress",
        "progress_kind": progress_kind,
        "authority_ceiling": authority_ceiling,
        "requires_safe_action": True,
    }


def generate_stale_task_progress_candidate(seed: int) -> ScenarioData:
    user_id, task_id, resource_id, course_id = _ids(seed)
    trace = (
        TraceEvent(
            event_type="task_created",
            occurred_at_minute=0,
            payload={
                "task_id_hash": task_id,
                "planned_duration_minutes": 90,
                "provenance": "user_planned",
            },
        ),
        TraceEvent(
            event_type="timer_started",
            occurred_at_minute=5,
            payload={"task_id_hash": task_id, "provenance": "observed"},
        ),
        TraceEvent(
            event_type="provider_progress_candidate_observed",
            occurred_at_minute=48,
            payload={
                **_progress_payload(
                    resource_id_hash=resource_id,
                    course_id_hash=course_id,
                    progress_kind="slide_progress",
                ),
                "slide_count": 42,
                "last_seen_slide": 27,
                "inferred_completion_percent_candidate": 64,
            },
        ),
        TraceEvent(
            event_type="stale_threshold_crossed",
            occurred_at_minute=60 * 13,
            payload={
                "task_id_hash": task_id,
                "stale_minutes": 60 * 12,
                "trust_state": "unknown",
                "requires_safe_action": True,
            },
        ),
    )
    return ScenarioData(
        scenario_id=STALE_PROGRESS_SCENARIO_ID,
        scenario_version=f"{STALE_PROGRESS_SCENARIO_ID}:v0",
        scenario_origin="synthetic",
        seed=seed,
        synthetic_user_id=user_id,
        hidden_state=HiddenState(
            user_activity="partially_worked_then_abandoned",
            intended_activity="review_lecture_resource",
            notes=(
                "The simulator knows the user made partial progress and then "
                "walked away; Lyra only sees stale timer plus provider progress."
            ),
        ),
        observable_trace=trace,
        generator_assumptions=_common_assumptions(),
        coverage_limitations=_common_limitations(),
        expected_resolution_rung="clarify_or_repair",
    )


def generate_background_video_fakeout(seed: int) -> ScenarioData:
    user_id, task_id, resource_id, course_id = _ids(seed)
    trace = (
        TraceEvent(
            event_type="task_created",
            occurred_at_minute=0,
            payload={"task_id_hash": task_id, "provenance": "user_planned"},
        ),
        TraceEvent(
            event_type="provider_progress_candidate_observed",
            occurred_at_minute=98,
            payload={
                **_progress_payload(
                    resource_id_hash=resource_id,
                    course_id_hash=course_id,
                    progress_kind="video_playback_progress",
                ),
                "video_played_percent": 98,
                "tab_state": "backgrounded",
                "muted": True,
                "mouse_idle_minutes": 98,
            },
        ),
    )
    return ScenarioData(
        scenario_id=BACKGROUND_VIDEO_SCENARIO_ID,
        scenario_version=f"{BACKGROUND_VIDEO_SCENARIO_ID}:v0",
        scenario_origin="synthetic",
        seed=seed,
        synthetic_user_id=user_id,
        hidden_state=HiddenState(
            user_activity="away_while_video_played",
            intended_activity="satisfy_provider_video_progress",
            notes=(
                "The simulator knows playback ran unattended; Lyra only sees "
                "high provider video progress with weak local activity."
            ),
        ),
        observable_trace=trace,
        generator_assumptions=_common_assumptions(),
        coverage_limitations=_common_limitations(),
        expected_resolution_rung="clarify_or_repair",
    )


def generate_multidevice_upload_collision(seed: int) -> ScenarioData:
    user_id, task_id, resource_id, course_id = _ids(seed)
    trace = (
        TraceEvent(
            event_type="timer_started",
            occurred_at_minute=0,
            payload={"task_id_hash": task_id, "device": "laptop"},
        ),
        TraceEvent(
            event_type="provider_progress_candidate_observed",
            occurred_at_minute=210,
            payload={
                **_progress_payload(
                    resource_id_hash=resource_id,
                    course_id_hash=course_id,
                    progress_kind="mobile_upload_observed",
                ),
                "task_id_hash": task_id,
                "upload_device": "mobile",
                "artifact_kind": "solution_pdf",
            },
        ),
        TraceEvent(
            event_type="stale_threshold_crossed",
            occurred_at_minute=60 * 12,
            payload={
                "task_id_hash": task_id,
                "desktop_timer_state": "stale_running",
                "trust_state": "unknown",
                "requires_safe_action": True,
            },
        ),
    )
    return ScenarioData(
        scenario_id=MULTIDEVICE_UPLOAD_SCENARIO_ID,
        scenario_version=f"{MULTIDEVICE_UPLOAD_SCENARIO_ID}:v0",
        scenario_origin="synthetic",
        seed=seed,
        synthetic_user_id=user_id,
        hidden_state=HiddenState(
            user_activity="finished_elsewhere_and_left_timer_running",
            intended_activity="submit_math_sheet",
            notes=(
                "The simulator knows the user uploaded from mobile after doing "
                "work elsewhere; Lyra sees a stale desktop timer collision."
            ),
        ),
        observable_trace=trace,
        generator_assumptions=_common_assumptions(),
        coverage_limitations=_common_limitations(),
        expected_resolution_rung="clarify_or_repair",
    )


def generate_reverse_progress_signal(seed: int) -> ScenarioData:
    user_id, _task_id, resource_id, course_id = _ids(seed)
    trace = (
        TraceEvent(
            event_type="provider_progress_candidate_observed",
            occurred_at_minute=0,
            payload={
                **_progress_payload(
                    resource_id_hash=resource_id,
                    course_id_hash=course_id,
                    progress_kind="non_monotonic_submission_state",
                ),
                "previous_provider_state": "submitted",
                "current_provider_state": "draft",
                "progress_direction": "reverse",
            },
        ),
    )
    return ScenarioData(
        scenario_id=REVERSE_PROGRESS_SCENARIO_ID,
        scenario_version=f"{REVERSE_PROGRESS_SCENARIO_ID}:v0",
        scenario_origin="synthetic",
        seed=seed,
        synthetic_user_id=user_id,
        hidden_state=HiddenState(
            user_activity="resubmission_or_portal_reopened",
            intended_activity="correct_assignment_submission",
            notes=(
                "The simulator knows provider progress moved backward due to "
                "resubmission/correction context; Lyra sees non-monotonic metadata."
            ),
        ),
        observable_trace=trace,
        generator_assumptions=_common_assumptions(),
        coverage_limitations=_common_limitations(),
        expected_resolution_rung="clarify_or_repair",
    )
