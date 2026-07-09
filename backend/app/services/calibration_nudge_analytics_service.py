"""Read-only calibration nudge analytics projection."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import CalibrationNudgeEvent

PRIMARY_METRIC = "delta_difference_accepted_minus_dismissed (Loop 1, pre-registered)"


def _mean_delta(events: list) -> Optional[float]:
    """Mean user_planned - executed_duration for events with outcome."""
    deltas = [
        event.user_planned_duration_minutes - event.executed_duration_minutes
        for event in events
        if event.executed_duration_minutes is not None
    ]
    return round(sum(deltas) / len(deltas), 2) if deltas else None


def calibration_nudge_snapshot(db: Session, *, user_id: int, days: int) -> dict:
    """Build calibration nudge effectiveness metrics for one user."""

    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(CalibrationNudgeEvent)
        .filter(
            CalibrationNudgeEvent.user_id == user_id,
            CalibrationNudgeEvent.voided_at.is_(None),
            CalibrationNudgeEvent.decided_at >= cutoff,
        )
        .all()
    )

    accepted = [row for row in rows if row.user_decision == "accepted"]
    dismissed = [row for row in rows if row.user_decision == "dismissed"]
    resolved = [row for row in rows if row.executed_duration_minutes is not None]
    unresolved = [row for row in rows if row.executed_duration_minutes is None]

    total = len(rows)
    accepted_delta = _mean_delta(accepted)
    dismissed_delta = _mean_delta(dismissed)
    delta_difference = (
        round(accepted_delta - dismissed_delta, 2)
        if accepted_delta is not None and dismissed_delta is not None
        else None
    )

    return {
        "summary": {
            "total_nudges": total,
            "accepted": len(accepted),
            "dismissed": len(dismissed),
            "resolved": len(resolved),
            "unresolved": len(unresolved),
            "acceptance_rate": round(len(accepted) / total, 3) if total else 0.0,
        },
        "delta_by_decision": {
            "accepted_mean_delta_minutes": accepted_delta,
            "accepted_resolved_n": sum(
                1 for event in accepted if event.executed_duration_minutes is not None
            ),
            "dismissed_mean_delta_minutes": dismissed_delta,
            "dismissed_resolved_n": sum(
                1 for event in dismissed if event.executed_duration_minutes is not None
            ),
            "delta_difference_accepted_minus_dismissed": delta_difference,
        },
        "lookback_days": days,
        "primary_metric": PRIMARY_METRIC,
    }
