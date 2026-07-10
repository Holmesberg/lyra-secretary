"""Read-only stopwatch reflection helpers."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Task, TaskState
from app.utils.time_utils import now_utc, strip_tz


def _format_micro_duration(minutes: Optional[int]) -> str:
    if minutes is None:
        return "unknown"
    if minutes >= 60:
        hours, mins = divmod(int(minutes), 60)
        return f"{hours}h {mins:02d}m"
    return f"{int(minutes)} min"


def _compute_micro_mirror(task: Task, interruption_metrics=None) -> Optional[str]:
    """One-line behavioral observation on stop. Priority: initiation > delta > pauses."""
    delay = task.initiation_delay_minutes
    delta = task.duration_delta_minutes
    duration = task.executed_duration_minutes or 0
    pauses = task.pause_count or 0

    if interruption_metrics is not None:
        pause_overhead = interruption_metrics.pause_overhead_minutes or 0
        execution = interruption_metrics.execution_time_minutes or duration
        span = interruption_metrics.session_span_minutes
        if pause_overhead >= 30 and execution > 0 and pause_overhead >= execution:
            return (
                f"Active work: {int(execution)} min. "
                f"Session span: {_format_micro_duration(span)}. "
                f"Pause overhead: {_format_micro_duration(pause_overhead)}."
            )

    if delay is not None and delay > 10:
        return f"Started {delay} min late."
    if delay is not None and delay <= 0:
        return "Started on time."
    if delta is not None and delta < -20:
        return f"Ran {abs(delta)} min over plan."
    if delta is not None and delta > 20:
        return f"Finished {delta} min early."
    if pauses == 0 and duration > 30:
        return "0 pauses this session."
    if pauses >= 3:
        return f"{pauses} pauses this session."

    planned = task.planned_duration_minutes
    executed = task.executed_duration_minutes
    if planned and executed and planned > 0:
        ratio = round(executed / planned, 2)
        if ratio >= 1.05:
            return f"Planned {planned} min, took {executed} — {ratio}× your estimate."
        if ratio <= 0.95:
            return f"Planned {planned} min, finished in {executed}."
        return f"Planned {planned} min, took {executed} — right on target."
    return None


def _compute_calibration_nudge(task: Task, db: Session) -> Optional[str]:
    """Reference-class forecast for same-category EXECUTED history."""
    if not task.category:
        return None
    delta = task.duration_delta_minutes
    if delta is None:
        return None
    history = (
        db.query(Task)
        .filter(
            Task.category == task.category,
            Task.state == TaskState.EXECUTED,
            Task.initiation_status != "system_error",
            Task.voided_at.is_(None),
            Task.executed_duration_minutes.is_not(None),
            Task.task_id != task.task_id,
        )
        .all()
    )
    n = len(history)
    if n < 3:
        return None
    avg_delta = sum(t.duration_delta_minutes for t in history) / n
    underestimate_count = sum(1 for t in history if t.duration_delta_minutes < 0)
    direction = "over" if delta < 0 else "under"
    return (
        f"{task.title} ran {abs(delta)} min {direction} plan. "
        f"Your '{task.category}' category avg: {avg_delta:+.0f} min across {n} sessions. "
        f"Prior '{task.category}' sessions ran over plan {underestimate_count}/{n} times."
    )


def _derive_current_pause_anchor(
    pause_state: Optional[dict],
) -> tuple[int, Optional[str]]:
    """Return current pause age plus the original pause timestamp string."""
    if not pause_state or not pause_state.get("paused_at"):
        return 0, None
    try:
        paused_at_dt = strip_tz(datetime.fromisoformat(pause_state["paused_at"]))
        delta = (now_utc() - paused_at_dt).total_seconds()
        return max(0, int(delta)), pause_state["paused_at"]
    except (ValueError, TypeError):
        return 0, None
