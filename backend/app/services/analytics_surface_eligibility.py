"""Surface metadata and clean-task eligibility helpers for analytics routes."""

from typing import Optional

from sqlalchemy.orm import Session

from app.core.authority import authority_for_surface
from app.services.cortex import planning_calibration_query
from app.services.exposure_ledger import baseline_clean_task_ids
from app.services.output_surfaces import get_output_surface_spec


def surface_metadata(
    surface_id: str,
    *,
    eligible_sample_count: int = 0,
    suppressed_reason: Optional[str] = None,
) -> dict:
    spec = get_output_surface_spec(surface_id)
    authority = authority_for_surface(spec).as_dict()
    return {
        "surface_id": surface_id,
        "truth_class": spec.truth_class,
        "usage_class": spec.usage_class,
        "clean_profile": spec.clean_profile,
        "eligible_sample_count": eligible_sample_count,
        "min_n_required": spec.min_n,
        "suppressed_reason": suppressed_reason,
        "fallback_mode": spec.fallback_mode,
        "legacy_adapter": spec.legacy_adapter,
        **authority,
    }


def eligible_tasks_for_surface(
    db: Session,
    tasks: list,
    surface_id: str,
    eligibility_cache: Optional[dict[tuple, set[str]]] = None,
) -> list:
    spec = get_output_surface_spec(surface_id)
    if spec.clean_profile == "descriptive_history":
        return tasks
    eligibility_cache = eligibility_cache if eligibility_cache is not None else {}
    if spec.clean_profile == "planning_calibration":
        if not tasks:
            return []
        user_id = getattr(tasks[0], "user_id", None)
        if user_id is None:
            return []
        cache_key = ("planning_calibration", int(user_id))
        if cache_key not in eligibility_cache:
            candidates = planning_calibration_query(db, user_id=int(user_id)).all()
            eligibility_cache[cache_key] = baseline_clean_task_ids(
                db,
                tasks=candidates,
                signal_targets=["planning_estimate", "duration_behavior"],
            )
        clean_ids = eligibility_cache[cache_key]
        return [
            task
            for task in tasks
            if task.task_id in clean_ids and not getattr(task, "is_anchor", False)
        ]
    cache_key = (
        "surface",
        spec.clean_profile,
        tuple(sorted(spec.signal_targets)),
        tuple(task.task_id for task in tasks if task.task_id),
    )
    if cache_key not in eligibility_cache:
        eligibility_cache[cache_key] = baseline_clean_task_ids(
            db,
            tasks=tasks,
            signal_targets=list(spec.signal_targets),
        )
    clean_ids = eligibility_cache[cache_key]
    return [
        task
        for task in tasks
        if task.task_id in clean_ids and not getattr(task, "is_anchor", False)
    ]


def eligible_tasks_for_surface_cached(
    db: Session,
    tasks: list,
    surface_id: str,
    eligibility_cache: dict[tuple, set[str]],
    *,
    eligible_tasks_fn=eligible_tasks_for_surface,
) -> list:
    """Call the eligibility filter with a shared request cache.

    Some endpoint tests monkeypatch the historical 3-argument helper shape.
    Keep that seam intact while letting production calls pass the cache.
    """
    code = getattr(eligible_tasks_fn, "__code__", None)
    if code is not None and code.co_argcount < 4:
        return eligible_tasks_fn(db, tasks, surface_id)
    return eligible_tasks_fn(db, tasks, surface_id, eligibility_cache)
