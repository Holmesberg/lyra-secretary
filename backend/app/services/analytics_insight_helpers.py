"""Pure helpers shared by analytics insight generators."""

from typing import Any, Optional

from app.db.models import TaskState
from app.utils.time_utils import now_utc, strip_tz

LEGACY_CATEGORY_INSIGHT_QUARANTINE = {"work"}


def time_of_day(local_dt: Any) -> str:
    hour = local_dt.hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def average(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def confidence_for_sample_size(sample_size: int) -> str:
    if sample_size >= 11:
        return "high"
    if sample_size >= 6:
        return "medium"
    return "low"


def build_insight_candidate(
    id: str,
    observation: str,
    data_points: int,
    strength: float = 0.0,
    *,
    facts: Optional[dict] = None,
    evidence: Optional[list[dict]] = None,
) -> dict:
    result = {
        "id": id,
        "observation": observation,
        "data_points": data_points,
        "confidence": confidence_for_sample_size(data_points),
        "strength": round(strength, 3),
    }
    if facts:
        result["_facts"] = facts
    if evidence:
        result["evidence"] = evidence
    return result


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    count = len(sorted_values)
    mid = count // 2
    return (
        sorted_values[mid]
        if count % 2
        else (sorted_values[mid - 1] + sorted_values[mid]) / 2
    )


def abs_minutes(value: float) -> int:
    return int(round(abs(value)))


def is_historical_task(task: Any) -> bool:
    return strip_tz(task.planned_start_utc) <= strip_tz(now_utc())


def category_for_insight(task: Any) -> Optional[str]:
    """Return a category only when it is safe for category-level claims."""
    category = (task.category or "").strip()
    if not category:
        return None
    if category.lower() in LEGACY_CATEGORY_INSIGHT_QUARANTINE:
        return None
    if category.lower() == "uncategorized":
        return None
    return category


def not_started(task: Any) -> bool:
    return task.state == TaskState.SKIPPED or task.initiation_status == "abandoned"
