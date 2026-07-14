"""Read-only deadline completion analytics projection.

Completion events are append-only submission/completion traces. They are not
stopwatch execution truth, so this service keeps completion behavior reporting
separate from deadline outcome reconciliation.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Deadline, DeadlineCompletionEvent
from app.utils.time_utils import strip_tz

PRIMARY_METRIC = "deadline_completion_delay_distribution"


def _mean(xs):
    return round(sum(xs) / len(xs), 2) if xs else None


def _median(xs):
    if not xs:
        return None
    sorted_xs = sorted(xs)
    n = len(sorted_xs)
    return (
        sorted_xs[n // 2]
        if n % 2 == 1
        else int((sorted_xs[n // 2 - 1] + sorted_xs[n // 2]) / 2)
    )


def _rate(num: int, denom: int) -> float:
    return round(num / denom, 3) if denom else 0.0


def _empty_snapshot() -> dict:
    return {
        "summary": {
            "completion_behavior_count": 0,
            "distinct_completed_deadlines": 0,
            "late_completion_behavior_count": 0,
            "late_distinct_completed_deadlines": 0,
            "late_completion_rate_by_behavior": 0.0,
            "late_completion_rate_by_deadline": 0.0,
            "mean_delay_minutes": None,
            "median_delay_minutes": None,
        },
        "by_source": [],
        "by_time_provenance": [],
        "per_deadline": [],
        "primary_metric": PRIMARY_METRIC,
        "note": "no deadline completion events for this user yet",
    }


def _event_sort_key(pair):
    event, _deadline = pair
    return (
        strip_tz(event.completed_at_utc),
        strip_tz(event.recorded_at_utc),
        event.event_id,
    )


def deadline_completion_snapshot(
    db: Session,
    *,
    user_id: Optional[int],
    include_external: bool = False,
) -> dict:
    """Build completion/submission behavior analytics for one user."""

    rows = (
        db.query(DeadlineCompletionEvent, Deadline)
        .join(Deadline, Deadline.deadline_id == DeadlineCompletionEvent.deadline_id)
        .filter(
            DeadlineCompletionEvent.voided_at.is_(None),
            Deadline.voided_at.is_(None),
        )
    )
    if user_id is not None:
        rows = rows.filter(DeadlineCompletionEvent.user_id == user_id)
    if not include_external:
        rows = rows.filter(Deadline.external_source.is_(None))
    results = rows.all()

    if not results:
        return _empty_snapshot()

    total = len(results)
    late_events = [event for event, _ in results if event.completed_after_due]
    delays = [event.delay_minutes for event, _ in results]

    earliest_by_deadline = {}
    events_by_deadline: dict[str, list] = defaultdict(list)
    for pair in sorted(results, key=_event_sort_key):
        event, _deadline = pair
        events_by_deadline[event.deadline_id].append(pair)
        earliest_by_deadline.setdefault(event.deadline_id, pair)

    distinct_total = len(earliest_by_deadline)
    late_distinct = [
        event
        for event, _deadline in earliest_by_deadline.values()
        if event.completed_after_due
    ]

    def _bucketed(label: str, key_fn):
        grouped: dict[str, list] = defaultdict(list)
        for event, _deadline in results:
            grouped[key_fn(event)].append(event)
        out = []
        for key in sorted(grouped.keys()):
            bucket = grouped[key]
            late_bucket = [event for event in bucket if event.completed_after_due]
            distinct_ids = {event.deadline_id for event in bucket}
            out.append({
                label: key,
                "n": len(bucket),
                "distinct_deadlines": len(distinct_ids),
                "late_count": len(late_bucket),
                "late_rate": _rate(len(late_bucket), len(bucket)),
                "mean_delay_minutes": _mean([event.delay_minutes for event in bucket]),
            })
        return out

    per_deadline = []
    for deadline_id, group in events_by_deadline.items():
        earliest_event, deadline = sorted(group, key=_event_sort_key)[0]
        events = [event for event, _ in group]
        per_deadline.append({
            "deadline_id": deadline_id,
            "title": deadline.title,
            "state": deadline.state,
            "event_count": len(events),
            "earliest_completed_at_utc": earliest_event.completed_at_utc,
            "earliest_delay_minutes": earliest_event.delay_minutes,
            "earliest_completed_after_due": earliest_event.completed_after_due,
            "sources": sorted({event.completion_source for event in events}),
            "time_provenances": sorted({event.time_provenance for event in events}),
        })
    per_deadline.sort(key=lambda row: row["earliest_completed_at_utc"])

    return {
        "summary": {
            "completion_behavior_count": total,
            "distinct_completed_deadlines": distinct_total,
            "late_completion_behavior_count": len(late_events),
            "late_distinct_completed_deadlines": len(late_distinct),
            "late_completion_rate_by_behavior": _rate(len(late_events), total),
            "late_completion_rate_by_deadline": _rate(len(late_distinct), distinct_total),
            "mean_delay_minutes": _mean(delays),
            "median_delay_minutes": _median(delays),
        },
        "by_source": _bucketed("source", lambda event: event.completion_source),
        "by_time_provenance": _bucketed(
            "time_provenance",
            lambda event: event.time_provenance,
        ),
        "per_deadline": per_deadline,
        "primary_metric": PRIMARY_METRIC,
    }
