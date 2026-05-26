"""Analytics insights product seam adapter for LyraSim."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping

from scripts.lyrasim.models import CleanDataAdmission, LyraOutput, ScenarioData


def seed_execution_tasks_from_scenario(
    db,
    scenario: ScenarioData,
    *,
    user_id: int,
    base_time: datetime | None = None,
) -> dict[str, list[Any]]:
    """Create synthetic Task rows from a LyraSim execution-anomaly scenario.

    This is a test-only product seam. Hidden state is deliberately ignored.
    The product receives observable execution rows and repair provenance only.
    """
    from app.db.models import Task, TaskExecutionCorrection, TaskState

    base_time = base_time or datetime.utcnow() - timedelta(days=30)
    tasks: list[Any] = []
    corrections: list[Any] = []
    for event in scenario.observable_trace:
        if event.event_type not in {
            "execution_session_observed",
            "execution_anomaly_observed",
        }:
            continue
        payload = event.payload
        planned_start = (
            base_time
            + timedelta(days=int(payload.get("day_offset") or 0))
        ).replace(
            hour=int(payload.get("hour") or 9),
            minute=0,
            second=0,
            microsecond=0,
        )
        planned_duration = int(payload["planned_duration_minutes"])
        executed_duration = int(payload["executed_duration_minutes"])
        executed_start = planned_start
        executed_end = executed_start + timedelta(minutes=executed_duration)
        task = Task(
            user_id=user_id,
            title=str(payload["task_key"]),
            category=str(payload.get("category") or "study"),
            planned_start_utc=planned_start,
            planned_end_utc=planned_start + timedelta(minutes=planned_duration),
            planned_duration_minutes=planned_duration,
            executed_start_utc=executed_start,
            executed_end_utc=executed_end,
            executed_duration_minutes=executed_duration,
            state=TaskState.EXECUTED,
            initiation_status=str(payload.get("initiation_status") or "started"),
            initiation_delay_minutes=0,
            created_at=planned_start - timedelta(days=1),
        )
        db.add(task)
        db.flush()
        tasks.append(task)

        if payload.get("clean_data_eligible") is False:
            corrected_duration = int(
                payload.get("corrected_executed_duration_minutes")
                or executed_duration
            )
            correction = TaskExecutionCorrection(
                task_id=task.task_id,
                user_id=user_id,
                provenance="retroactive",
                reason=str(payload.get("correction_reason") or "forgot_to_stop_timer"),
                note="LyraSim repaired anomaly fixture",
                original_executed_start_utc=executed_start,
                original_executed_end_utc=executed_end,
                original_executed_duration_minutes=executed_duration,
                corrected_executed_end_utc=(
                    executed_start + timedelta(minutes=corrected_duration)
                ),
                corrected_executed_duration_minutes=corrected_duration,
                observed_paused_minutes=0.0,
                vt17_eligible=False,
            )
            db.add(correction)
            corrections.append(correction)

    db.commit()
    for task in tasks:
        db.refresh(task)
    for correction in corrections:
        db.refresh(correction)
    return {"tasks": tasks, "corrections": corrections}


def _clean_eligible_trace_count(scenario: ScenarioData) -> int:
    return sum(
        1
        for event in scenario.observable_trace
        if event.payload.get("clean_data_eligible") is True
        and event.payload.get("state") == "executed"
    )


def _has_dirty_trace(scenario: ScenarioData) -> bool:
    return any(
        event.payload.get("clean_data_eligible") is False
        for event in scenario.observable_trace
    )


def lyra_output_from_insights_response(
    response: Mapping[str, Any],
    *,
    scenario: ScenarioData,
) -> LyraOutput:
    """Convert actual insights output into LyraSim scorer input."""
    insights = response.get("insights") or []
    text_outputs = tuple(
        str(
            insight.get("body")
            or insight.get("observation")
            or insight.get("title")
            or ""
        )
        for insight in insights
        if (insight.get("body") or insight.get("observation") or insight.get("title"))
    )
    seams = ["analytics.insights"]
    if (
        response.get("exposure_id")
        or response.get("render_id")
        or response.get("suppressed_reason")
    ):
        seams.append("output_surfaces.exposure_ledger")

    clean_trace_count = _clean_eligible_trace_count(scenario)
    dirty_trace_admitted = (
        _has_dirty_trace(scenario)
        and int(response.get("sessions_analyzed") or 0) > clean_trace_count
    )

    return LyraOutput(
        stubbed=False,
        product_seams_exercised=tuple(seams),
        authority_rung=str(response.get("authority_rung") or "interpretation"),
        text_outputs=text_outputs,
        clean_data_admissions=(
            CleanDataAdmission(
                profile="planning_calibration",
                admitted=dirty_trace_admitted,
                reason="analytics_insights_sessions_analyzed",
            ),
        ),
        published_claim_tags=(
            ("bounded_pattern",) if insights else ("no_contract_safe_insight",)
        ),
        safe_actions=(),
        safe_action_type="none",
        resolution_rung="recommend" if insights else "suppress",
    )
