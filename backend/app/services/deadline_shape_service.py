"""Read-only deadline-shape analytics projection.

This service backs GET /v1/analytics/deadline-shape. It keeps the
pre-registered Rule 14/15 computation out of the analytics route without
changing the endpoint response shape.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import (
    Deadline,
    StopwatchSession,
    Task,
    TaskDeadlineOutcome,
    TaskExecutionCorrection,
    TaskState,
)

PRIMARY_METRIC = "delay_minutes_distribution (MANIFESTO Rule 14, pre-registered)"


def _mean(xs):
    return round(sum(xs) / len(xs), 2) if xs else None


def _median(xs):
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 == 1 else int((xs[n // 2 - 1] + xs[n // 2]) / 2)


def _rate(num: int, denom: int) -> float:
    return round(num / denom, 3) if denom else 0.0


def _scope_bullet_band(count):
    if count is None:
        return "0"
    if count == 0:
        return "0"
    if count <= 3:
        return "1-3"
    if count <= 6:
        return "4-6"
    return "7+"


def deadline_shape_snapshot(
    db: Session,
    *,
    user_id: Optional[int],
    include_external: bool = False,
) -> dict:
    """Build the per-user deadline-met distribution snapshot.

    Reads task_deadline_outcome rows written by the reconciliation job and
    filters voided rows across outcome, task, and deadline. Third-party
    imported deadlines are excluded by default because this surface measures
    user-specified deadline behavior.
    """

    clean_stopwatch_exists = (
        db.query(StopwatchSession.session_id)
        .filter(
            StopwatchSession.task_id == Task.task_id,
            StopwatchSession.user_id == TaskDeadlineOutcome.user_id,
            StopwatchSession.end_time_utc.isnot(None),
            StopwatchSession.auto_closed.is_(False),
            StopwatchSession.data_quality_flag.is_(None),
        )
        .exists()
    )
    dirty_stopwatch_exists = (
        db.query(StopwatchSession.session_id)
        .filter(
            StopwatchSession.task_id == Task.task_id,
            StopwatchSession.user_id == TaskDeadlineOutcome.user_id,
            (
                StopwatchSession.auto_closed.is_(True)
                | StopwatchSession.data_quality_flag.isnot(None)
            ),
        )
        .exists()
    )
    corrected_task_exists = (
        db.query(TaskExecutionCorrection.correction_id)
        .filter(TaskExecutionCorrection.task_id == Task.task_id)
        .exists()
    )

    rows = (
        db.query(
            TaskDeadlineOutcome,
            Task,
            Deadline,
        )
        .join(Task, Task.task_id == TaskDeadlineOutcome.task_id)
        .join(Deadline, Deadline.deadline_id == Task.deadline_id)
        .filter(
            TaskDeadlineOutcome.voided_at.is_(None),
            Task.voided_at.is_(None),
            Deadline.voided_at.is_(None),
            Task.state == TaskState.EXECUTED,
            Task.initiation_status != "system_error",
            Task.initiation_status != "retroactive",
            Task.executed_start_utc.isnot(None),
            Task.executed_end_utc.isnot(None),
            Task.executed_duration_minutes.isnot(None),
            Task.planned_duration_minutes >= 5,
            clean_stopwatch_exists,
            ~dirty_stopwatch_exists,
            ~corrected_task_exists,
        )
    )
    if user_id is not None:
        rows = rows.filter(TaskDeadlineOutcome.user_id == user_id)
    if not include_external:
        rows = rows.filter(Deadline.external_source.is_(None))
    results = rows.all()

    total = len(results)
    if total == 0:
        return {
            "summary": {
                "total_outcomes": 0,
                "deadline_met_count": 0,
                "deadline_missed_count": 0,
                "deadline_met_rate": 0.0,
                "mean_delay_minutes": None,
                "median_delay_minutes": None,
            },
            "by_match_source": [],
            "by_scope_bullet_count_band": [],
            "per_deadline": [],
            "primary_metric": PRIMARY_METRIC,
            "note": "no deadline-bound EXECUTED tasks reconciled for this user yet",
        }

    met = [r for r in results if r[0].deadline_met]
    delays = sorted([r[0].delay_minutes for r in results])
    summary = {
        "total_outcomes": total,
        "deadline_met_count": len(met),
        "deadline_missed_count": total - len(met),
        "deadline_met_rate": _rate(len(met), total),
        "mean_delay_minutes": _mean(delays),
        "median_delay_minutes": _median(delays),
    }

    by_match_source: dict[str, list] = defaultdict(list)
    for outcome, task, _ in results:
        key = task.deadline_match_source or "unknown"
        by_match_source[key].append(outcome)

    by_match_source_out = []
    for source in sorted(by_match_source.keys()):
        bucket = by_match_source[source]
        bucket_met = [o for o in bucket if o.deadline_met]
        by_match_source_out.append({
            "source": source,
            "n": len(bucket),
            "met_rate": _rate(len(bucket_met), len(bucket)),
            "mean_delay_minutes": _mean([o.delay_minutes for o in bucket]),
        })

    by_band: dict[str, list] = defaultdict(list)
    for outcome, task, _ in results:
        by_band[_scope_bullet_band(task.scope_bullet_count_at_plan)].append(outcome)

    band_order = ["0", "1-3", "4-6", "7+"]
    by_band_out = []
    for band in band_order:
        bucket = by_band.get(band, [])
        bucket_met = [o for o in bucket if o.deadline_met]
        by_band_out.append({
            "band": band,
            "n": len(bucket),
            "met_rate": _rate(len(bucket_met), len(bucket)),
            "mean_delay_minutes": _mean([o.delay_minutes for o in bucket]),
        })

    per_deadline_groups: dict[str, list] = defaultdict(list)
    for outcome, task, deadline in results:
        per_deadline_groups[deadline.deadline_id].append((outcome, task, deadline))

    per_deadline_out = []
    for deadline_id, group in per_deadline_groups.items():
        group_outcomes = [g[0] for g in group]
        group_tasks = [g[1] for g in group]
        deadline_obj = group[0][2]
        deltas = [
            (t.planned_duration_minutes - t.executed_duration_minutes)
            for t in group_tasks
            if t.planned_duration_minutes and t.executed_duration_minutes
        ]
        planned_minutes = [
            t.planned_duration_minutes
            for t in group_tasks
            if t.planned_duration_minutes
        ]
        planned_mean = _mean(planned_minutes)
        bias_factor_observed = (
            round(_mean(deltas) / planned_mean, 3)
            if deltas and planned_minutes and planned_mean
            else None
        )
        met_in_group = [o for o in group_outcomes if o.deadline_met]
        per_deadline_out.append({
            "deadline_id": deadline_id,
            "title": deadline_obj.title,
            "state": deadline_obj.state,
            "n": len(group_outcomes),
            "met_rate": _rate(len(met_in_group), len(group_outcomes)),
            "mean_delay_minutes": _mean([o.delay_minutes for o in group_outcomes]),
            "bias_factor_observed": bias_factor_observed,
        })

    return {
        "summary": summary,
        "by_match_source": by_match_source_out,
        "by_scope_bullet_count_band": by_band_out,
        "per_deadline": per_deadline_out,
        "primary_metric": PRIMARY_METRIC,
    }
