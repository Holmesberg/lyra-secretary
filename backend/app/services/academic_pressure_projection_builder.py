"""Build the additive Pressure Map demand/coverage projection."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from app.db.models import Task
from app.schemas.academic import (
    AcademicDemandCoverageProjection,
    AcademicMinuteEnvelope,
    AcademicObligationDemandProjection,
    AcademicPressureItem,
    AcademicProjectionRole,
)
from app.services.academic_pressure_projection import (
    DemandCoverageScenario,
    MinuteEnvelope,
    TimeInterval,
    project_demand_coverage,
    union_interval_minutes,
)
from app.utils.time_utils import strip_tz


def _api_envelope(envelope: MinuteEnvelope) -> AcademicMinuteEnvelope:
    return AcademicMinuteEnvelope(
        low_minutes=envelope.low,
        high_minutes=envelope.high,
    )


def _scenarios(
    obligation_id: str,
    *,
    low_minutes: int,
    high_minutes: int,
    coverage_minutes: int,
) -> tuple[DemandCoverageScenario, ...]:
    values = [
        DemandCoverageScenario(
            scenario_id=f"{obligation_id}:low",
            total_estimate_minutes=low_minutes,
            completed_scope_credit_minutes=0,
            feasible_future_coverage_minutes=coverage_minutes,
        )
    ]
    if high_minutes != low_minutes:
        values.append(
            DemandCoverageScenario(
                scenario_id=f"{obligation_id}:high",
                total_estimate_minutes=high_minutes,
                completed_scope_credit_minutes=0,
                feasible_future_coverage_minutes=coverage_minutes,
            )
        )
    return tuple(values)


def _task_coverage(
    tasks: Iterable[Task],
    *,
    window_start: datetime,
    window_end: datetime,
) -> tuple[int, list[str], list[str], list[str]]:
    task_list = list(tasks)
    linked_ids = [task.task_id for task in task_list]
    if window_end <= window_start:
        return 0, linked_ids, [], linked_ids

    intervals: list[TimeInterval] = []
    invalid_ids: set[str] = set()
    for task in task_list:
        start = strip_tz(task.planned_start_utc)
        end = strip_tz(task.planned_end_utc)
        if start is None or end is None or end <= start:
            invalid_ids.add(task.task_id)
            continue
        intervals.append(
            TimeInterval(interval_id=task.task_id, start=start, end=end)
        )

    union = union_interval_minutes(
        intervals,
        window_start=window_start,
        window_end=window_end,
    )
    coverage_ids = list(union.contributing_interval_ids)
    noncontributing = [
        task_id
        for task_id in linked_ids
        if task_id not in coverage_ids or task_id in invalid_ids
    ]
    return union.total_minutes, linked_ids, coverage_ids, noncontributing


def _obligation_projection(
    item: AcademicPressureItem,
    *,
    tasks: list[Task],
    projection_role: AcademicProjectionRole,
    window_start: datetime,
    window_end: datetime,
) -> AcademicObligationDemandProjection:
    coverage, linked_ids, coverage_ids, noncontributing_ids = _task_coverage(
        tasks,
        window_start=window_start,
        window_end=window_end,
    )
    projection = project_demand_coverage(
        _scenarios(
            item.obligation_id,
            low_minutes=item.estimate.low_minutes,
            high_minutes=item.estimate.high_minutes,
            coverage_minutes=coverage,
        )
    )
    return AcademicObligationDemandProjection(
        obligation_id=item.obligation_id,
        projection_role=projection_role,
        source_class=item.source_class,
        total_estimate=_api_envelope(projection.total_estimate),
        completed_scope_credit=_api_envelope(
            projection.completed_scope_credit
        ),
        remaining_demand=_api_envelope(projection.remaining_demand),
        feasible_future_coverage=_api_envelope(
            projection.feasible_future_coverage
        ),
        applied_coverage=_api_envelope(projection.applied_coverage),
        unscheduled_demand=_api_envelope(projection.unscheduled_demand),
        overcoverage=_api_envelope(projection.overcoverage),
        linked_task_ids=linked_ids,
        coverage_task_ids=coverage_ids,
        noncontributing_linked_task_ids=noncontributing_ids,
        estimate_inconsistent=bool(projection.inconsistent_scenario_ids),
    )


def _sum_projection_envelopes(
    obligations: list[AcademicObligationDemandProjection],
) -> dict[str, AcademicMinuteEnvelope]:
    fields = (
        "total_estimate",
        "completed_scope_credit",
        "remaining_demand",
        "feasible_future_coverage",
        "applied_coverage",
        "unscheduled_demand",
        "overcoverage",
    )
    return {
        field: AcademicMinuteEnvelope(
            low_minutes=sum(
                getattr(obligation, field).low_minutes
                for obligation in obligations
            ),
            high_minutes=sum(
                getattr(obligation, field).high_minutes
                for obligation in obligations
            ),
        )
        for field in fields
    }


def _aggregate_projection(
    obligations: list[AcademicObligationDemandProjection],
) -> AcademicDemandCoverageProjection:
    totals = _sum_projection_envelopes(obligations)
    scenario_count = 1
    if any(
        obligation.total_estimate.low_minutes
        != obligation.total_estimate.high_minutes
        for obligation in obligations
    ):
        scenario_count = 2

    return AcademicDemandCoverageProjection(
        obligation_count=len(obligations),
        scenario_count=scenario_count,
        inconsistent_obligation_ids=[
            obligation.obligation_id
            for obligation in obligations
            if obligation.estimate_inconsistent
        ],
        obligations=obligations,
        **totals,
    )


def build_demand_coverage_projection(
    *,
    items: list[AcademicPressureItem],
    future_tasks: list[Task],
    window_start: datetime,
    window_end: datetime,
) -> AcademicDemandCoverageProjection:
    """Build a provider-blind projection without claiming capacity."""

    tasks_by_deadline: dict[str, list[Task]] = {}
    for task in future_tasks:
        if task.deadline_id:
            tasks_by_deadline.setdefault(task.deadline_id, []).append(task)

    obligations: list[AcademicObligationDemandProjection] = []
    for item in items:
        if item.source_class == "lyra_task":
            continue

        due_at = strip_tz(item.due_at_utc) or item.due_at_utc
        obligations.append(
            _obligation_projection(
                item,
                tasks=tasks_by_deadline.get(item.obligation_id, []),
                projection_role="deadline_obligation",
                window_start=window_start,
                window_end=min(window_end, due_at),
            )
        )

    return _aggregate_projection(obligations)
