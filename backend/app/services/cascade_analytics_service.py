"""Read-only cascade analytics snapshot builders."""

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db.models import Task, TaskState
from app.services.analytics_insight_helpers import time_of_day as _time_of_day
from app.utils.time_utils import now_utc, to_local


def cascade_snapshot(db: Session, *, days: int) -> dict:
    """Return cascade analytics for the requested look-back window."""
    cutoff = now_utc() - timedelta(days=days)

    tasks = (
        db.query(Task)
        .filter(
            Task.planned_start_utc >= cutoff,
            Task.initiation_status != "system_error",
            Task.voided_at.is_(None),
        )
        .order_by(Task.planned_start_utc)
        .all()
    )

    days_map: dict[date, list[Task]] = defaultdict(list)
    for task in tasks:
        local_day = to_local(task.planned_start_utc).date()
        days_map[local_day].append(task)

    daily_cascades = []
    total_skip_followed_by_skip = 0
    total_skip_followed_by_any = 0
    morning_anchor_executed_days = 0
    morning_anchor_skips = 0
    morning_anchor_cascade_days = 0
    total_days_with_morning = 0
    category_skip_counts: dict[str, int] = defaultdict(int)
    category_total_counts: dict[str, int] = defaultdict(int)
    tod_skip_counts: dict[str, int] = defaultdict(int)
    tod_total_counts: dict[str, int] = defaultdict(int)
    all_cascade_scores: list[float] = []

    def _is_skip(task: Task) -> bool:
        return task.state == TaskState.SKIPPED or task.initiation_status == "abandoned"

    for local_day in sorted(days_map.keys()):
        day_tasks = [task for task in days_map[local_day] if task.state != TaskState.DELETED]
        chain = []
        current_streak = 0
        first_skip_time = None
        first_skip_category = None
        consecutive_sequences: list[list[str]] = []
        current_seq: list[str] = []

        for index, task in enumerate(day_tasks):
            skip = _is_skip(task)
            tod = _time_of_day(to_local(task.planned_start_utc))

            if task.category:
                category_total_counts[task.category] += 1
                if skip:
                    category_skip_counts[task.category] += 1
            tod_total_counts[tod] += 1
            if skip:
                tod_skip_counts[tod] += 1

            if skip:
                current_streak += 1
                current_seq.append(task.title)
                if first_skip_time is None:
                    first_skip_time = to_local(task.planned_start_utc).strftime("%H:%M")
                    first_skip_category = task.category
            else:
                if current_seq:
                    consecutive_sequences.append(current_seq)
                current_seq = []
                current_streak = 0

            if index > 0:
                previous = day_tasks[index - 1]
                if _is_skip(previous):
                    total_skip_followed_by_any += 1
                    if skip:
                        total_skip_followed_by_skip += 1

            chain.append({
                "task_id": task.task_id,
                "title": task.title,
                "category": task.category,
                "state": task.state.value if hasattr(task.state, "value") else str(task.state),
                "initiation_status": task.initiation_status,
                "is_skip": skip,
                "streak": current_streak,
            })

        if current_seq:
            consecutive_sequences.append(current_seq)

        morning_anchor_executed = False
        if day_tasks:
            first = day_tasks[0]
            local_hour = to_local(first.planned_start_utc).hour
            if local_hour < 9:
                total_days_with_morning += 1
                if _is_skip(first):
                    morning_anchor_skips += 1
                    rest_skips = sum(1 for task in day_tasks[1:] if _is_skip(task))
                    if len(day_tasks) > 1 and rest_skips / (len(day_tasks) - 1) > 0.5:
                        morning_anchor_cascade_days += 1
                else:
                    morning_anchor_executed = True
                    morning_anchor_executed_days += 1

        executed_count = sum(1 for task in day_tasks if task.state == TaskState.EXECUTED)
        skipped_count = sum(1 for task in day_tasks if _is_skip(task))
        max_streak = max((entry["streak"] for entry in chain), default=0)

        day_skip_pairs = sum(
            1 for index in range(1, len(day_tasks))
            if _is_skip(day_tasks[index - 1])
        )
        day_skip_skip = sum(
            1 for index in range(1, len(day_tasks))
            if _is_skip(day_tasks[index - 1]) and _is_skip(day_tasks[index])
        )
        day_cascade = round(day_skip_skip / day_skip_pairs, 3) if day_skip_pairs > 0 else 0.0
        all_cascade_scores.append(day_cascade)

        daily_cascades.append({
            "date": local_day.isoformat(),
            "total_tasks": len(day_tasks),
            "total_planned": len(day_tasks),
            "total_executed": executed_count,
            "total_skipped": skipped_count,
            "cascade_score": day_cascade,
            "morning_anchor_executed": morning_anchor_executed,
            "first_skip_time": first_skip_time,
            "first_skip_category": first_skip_category,
            "consecutive_skip_sequences": consecutive_sequences,
            "max_streak": max_streak,
            "chain": chain,
        })

    cascade_score = (
        round(total_skip_followed_by_skip / total_skip_followed_by_any, 3)
        if total_skip_followed_by_any > 0 else 0.0
    )

    most_prone_category = max(
        (category for category in category_total_counts if category_total_counts[category] >= 3),
        key=lambda category: category_skip_counts.get(category, 0) / category_total_counts[category],
        default=None,
    )
    most_prone_tod = max(
        (tod for tod in tod_total_counts if tod_total_counts[tod] >= 3),
        key=lambda tod: tod_skip_counts.get(tod, 0) / tod_total_counts[tod],
        default=None,
    )

    return {
        "days_analyzed": len(daily_cascades),
        "cascade_score": cascade_score,
        "cascade_score_label": "P(skip N+1 | skip N)",
        "total_skip_followed_by_skip": total_skip_followed_by_skip,
        "total_skip_followed_by_any": total_skip_followed_by_any,
        "summary": {
            "avg_cascade_score": round(sum(all_cascade_scores) / len(all_cascade_scores), 3) if all_cascade_scores else 0.0,
            "skip_propagation_probability": cascade_score,
            "morning_anchor_execution_rate": (
                round(morning_anchor_executed_days / total_days_with_morning, 3)
                if total_days_with_morning > 0 else 0.0
            ),
            "most_cascade_prone_category": most_prone_category,
            "most_cascade_prone_time_of_day": most_prone_tod,
        },
        "morning_anchor": {
            "days_with_morning_task": total_days_with_morning,
            "morning_anchor_executed_days": morning_anchor_executed_days,
            "morning_skips": morning_anchor_skips,
            "cascade_days": morning_anchor_cascade_days,
            "cascade_rate": (
                round(morning_anchor_cascade_days / morning_anchor_skips, 3)
                if morning_anchor_skips > 0 else 0.0
            ),
        },
        "daily": daily_cascades,
    }
