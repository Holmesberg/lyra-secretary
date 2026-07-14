"""Read-only output-surface diagnostics for operator instrumentation."""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import (
    Deadline,
    ExposureDecisionEvent,
    ExposureRenderEvent,
    PauseEvent,
    ReflectionViewLog,
    StopwatchSession,
    SuppressionEvent,
    Task,
    TaskState,
    User,
)
from app.services.exposure_ledger import (
    baseline_clean_task_ids,
    classify_exposure_terminal_state,
    exposure_results_for_task,
)
from app.services.output_surfaces import (
    OutputSurfaceSpec,
    load_output_surface_registry,
    projection_class_for_profile,
)
from app.utils.time_utils import now_utc, strip_tz


def _candidate_tasks_for_profile(
    db: Session,
    *,
    user_id: int,
    clean_profile: Optional[str],
    cutoff,
) -> list[Task]:
    if clean_profile is None:
        return []

    q = db.query(Task).filter(
        Task.user_id == user_id,
        Task.voided_at.is_(None),
        or_(Task.planned_start_utc.is_(None), Task.planned_start_utc >= cutoff),
    )

    if clean_profile in {"measured_execution", "planning_calibration"}:
        clean_stopwatch_exists = (
            db.query(StopwatchSession.session_id)
            .filter(
                StopwatchSession.task_id == Task.task_id,
                StopwatchSession.user_id == user_id,
                StopwatchSession.end_time_utc.isnot(None),
                StopwatchSession.auto_closed.is_(False),
                StopwatchSession.data_quality_flag.is_(None),
            )
            .exists()
        )
        auto_closed_stopwatch_exists = (
            db.query(StopwatchSession.session_id)
            .filter(
                StopwatchSession.task_id == Task.task_id,
                StopwatchSession.user_id == user_id,
                StopwatchSession.auto_closed.is_(True),
            )
            .exists()
        )
        q = q.filter(
            Task.state == TaskState.EXECUTED,
            Task.is_anchor.is_(False),
            Task.initiation_status != "system_error",
            Task.initiation_status != "retroactive",
            Task.executed_duration_minutes.isnot(None),
            Task.planned_duration_minutes >= 5,
            clean_stopwatch_exists,
            ~auto_closed_stopwatch_exists,
        )
        if clean_profile == "planning_calibration":
            q = (
                q.outerjoin(Deadline, Task.deadline_id == Deadline.deadline_id)
                .filter(or_(Task.deadline_id.is_(None), Deadline.external_source.is_(None)))
            )
    elif clean_profile == "pause_process":
        q = (
            q.join(StopwatchSession, StopwatchSession.task_id == Task.task_id)
            .join(PauseEvent, PauseEvent.session_id == StopwatchSession.session_id)
            .filter(
                Task.state == TaskState.EXECUTED,
                PauseEvent.self_reported_retroactively.is_(False),
                StopwatchSession.auto_closed.is_(False),
                StopwatchSession.data_quality_flag.is_(None),
            )
            .distinct()
        )
    elif clean_profile == "descriptive_history":
        pass
    elif clean_profile == "deadline_completion_behavior":
        q = q.filter(Task.deadline_id.isnot(None))
    else:
        return []

    return q.all()


def _surface_activity_counts(
    *,
    spec: OutputSurfaceSpec,
    decisions: list[ExposureDecisionEvent],
    render_counts: Counter[str],
    render_exposure_ids: set[str],
    suppression_exposure_ids: set[str],
) -> dict[str, Any]:
    spec_decisions = [
        row for row in decisions
        if row.trigger_source == spec.surface_id
        or row.content_template_id == spec.surface_id.replace(".", "_")
    ]
    decision_ids = {row.exposure_id for row in spec_decisions}
    rendered = render_counts.get(spec.surface_id, 0)
    suppressed = len(decision_ids & suppression_exposure_ids)
    missing_terminal = sum(
        1
        for row in spec_decisions
        if not classify_exposure_terminal_state(
            decision_status=row.decision_status,
            has_render=row.exposure_id in render_exposure_ids,
            has_suppression=row.exposure_id in suppression_exposure_ids,
        ).has_terminal_event
    )
    return {
        "decisions": len(spec_decisions),
        "renders": rendered,
        "suppressions": suppressed,
        "missing_terminal_events": missing_terminal,
    }


def _eligibility_audit_for_surface(
    db: Session,
    *,
    spec: OutputSurfaceSpec,
    user: User,
    cutoff,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metrics = metrics or _eligibility_metrics_for_surface_inputs(
        db,
        clean_profile=spec.clean_profile,
        signal_targets=tuple(spec.signal_targets),
        user_id=user.user_id,
        cutoff=cutoff,
    )

    clean_n = int(metrics["clean_n"])
    missing_projection = metrics.get("missing_projection")
    if missing_projection:
        suppression_reason = "missing_projection"
    elif clean_n < spec.min_n:
        suppression_reason = "insufficient_clean_samples"
    else:
        suppression_reason = None

    return {
        "surface_id": spec.surface_id,
        "truth_class": spec.truth_class,
        "usage_class": spec.usage_class,
        "clean_profile": spec.clean_profile,
        "projection_class": metrics.get("projection_class"),
        "candidate_n": metrics["candidate_n"],
        "clean_n": clean_n,
        "contaminated_n": metrics["contaminated_n"],
        "unknown_n": metrics["unknown_n"],
        "exposed_n": metrics["exposed_n"],
        "intervention_n": metrics["intervention_n"],
        "state_counts": metrics["state_counts"],
        "min_n_required": spec.min_n,
        "suppression_reason": suppression_reason,
        "fallback_mode": spec.fallback_mode,
        "operator_only_skew": {
            "current_user_is_operator": bool(user.is_operator),
            "surface_operator_only": bool(spec.operator_only),
        },
    }


def _eligibility_metrics_for_surface_inputs(
    db: Session,
    *,
    clean_profile: Optional[str],
    signal_targets: tuple[str, ...],
    user_id: int,
    cutoff,
) -> dict[str, Any]:
    projection_class = None
    missing_projection = None
    try:
        projection_class = projection_class_for_profile(clean_profile)
    except ValueError as exc:
        missing_projection = str(exc)

    candidates = _candidate_tasks_for_profile(
        db,
        user_id=user_id,
        clean_profile=clean_profile,
        cutoff=cutoff,
    )
    candidate_count = len(candidates)

    if missing_projection:
        clean_ids: set[str] = set()
    elif clean_profile == "descriptive_history":
        clean_ids = {task.task_id for task in candidates if task.task_id}
    else:
        clean_ids = baseline_clean_task_ids(
            db,
            tasks=candidates,
            signal_targets=list(signal_targets),
        )

    state_counts: Counter[str] = Counter()
    task_state_counts: Counter[str] = Counter()
    for task in candidates:
        results = exposure_results_for_task(
            db,
            task=task,
            signal_targets=list(signal_targets),
        )
        states = {result.state for result in results}
        for result in results:
            state_counts[result.state] += 1
        if "UNKNOWN" in states:
            task_state_counts["unknown"] += 1
        elif "INTERVENTION" in states:
            task_state_counts["intervention"] += 1
        elif "EXPOSED" in states:
            task_state_counts["exposed"] += 1
        elif states == {"NONE"}:
            task_state_counts["none"] += 1

    clean_n = len(clean_ids)
    return {
        "projection_class": projection_class,
        "candidate_n": candidate_count,
        "clean_n": clean_n,
        "contaminated_n": max(0, candidate_count - clean_n),
        "unknown_n": task_state_counts.get("unknown", 0),
        "exposed_n": task_state_counts.get("exposed", 0),
        "intervention_n": task_state_counts.get("intervention", 0),
        "state_counts": dict(sorted(state_counts.items())),
        "missing_projection": missing_projection,
    }


def output_surface_diagnostics(
    db: Session,
    *,
    user_id: int,
    window_days: int = 30,
) -> dict[str, Any]:
    """Operator diagnostic for registry and exposure-chain proof.

    This is meta-instrumentation. It does not render user-facing claims and does
    not create exposure rows.
    """
    user = db.query(User).filter(User.user_id == user_id).one()
    window_days = max(1, min(365, int(window_days)))
    cutoff = strip_tz(now_utc()) - timedelta(days=window_days)

    registry = load_output_surface_registry()
    registered = set(registry)
    decisions = (
        db.query(ExposureDecisionEvent)
        .filter(
            ExposureDecisionEvent.user_id == user_id,
            ExposureDecisionEvent.eligible_at >= cutoff,
        )
        .all()
    )
    decision_ids = [row.exposure_id for row in decisions]
    renders = []
    suppressions = []
    if decision_ids:
        renders = (
            db.query(ExposureRenderEvent)
            .filter(ExposureRenderEvent.exposure_id.in_(decision_ids))
            .all()
        )
        suppressions = (
            db.query(SuppressionEvent)
            .filter(SuppressionEvent.exposure_id.in_(decision_ids))
            .all()
        )

    render_counts = Counter(row.surface for row in renders)
    render_exposure_ids = {row.exposure_id for row in renders}
    suppression_exposure_ids = {row.exposure_id for row in suppressions}
    missing_terminal_ids = sorted(
        row.exposure_id
        for row in decisions
        if not classify_exposure_terminal_state(
            decision_status=row.decision_status,
            has_render=row.exposure_id in render_exposure_ids,
            has_suppression=row.exposure_id in suppression_exposure_ids,
        ).has_terminal_event
    )

    legacy_adapter_reliance = []
    for spec in registry.values():
        if not spec.legacy_adapter:
            continue
        legacy_count = (
            db.query(ReflectionViewLog)
            .filter(
                ReflectionViewLog.user_id == user_id,
                ReflectionViewLog.reflection_type == spec.legacy_adapter,
                ReflectionViewLog.fired_at >= cutoff,
            )
            .count()
        )
        v0_activity = _surface_activity_counts(
            spec=spec,
            decisions=decisions,
            render_counts=render_counts,
            render_exposure_ids=render_exposure_ids,
            suppression_exposure_ids=suppression_exposure_ids,
        )
        legacy_adapter_reliance.append({
            "surface_id": spec.surface_id,
            "legacy_adapter": spec.legacy_adapter,
            "legacy_rows": legacy_count,
            "v0_renders": v0_activity["renders"],
            "parity_delta": legacy_count - v0_activity["renders"],
        })

    eligibility_metrics_cache: dict[
        tuple[Optional[str], tuple[str, ...]],
        dict[str, Any],
    ] = {}
    current_data_eligibility = []
    for spec in registry.values():
        if spec.truth_class not in {"interpretation", "intervention"}:
            continue
        cache_key = (spec.clean_profile, tuple(spec.signal_targets))
        metrics = eligibility_metrics_cache.get(cache_key)
        if metrics is None:
            metrics = _eligibility_metrics_for_surface_inputs(
                db,
                clean_profile=spec.clean_profile,
                signal_targets=tuple(spec.signal_targets),
                user_id=user.user_id,
                cutoff=cutoff,
            )
            eligibility_metrics_cache[cache_key] = metrics
        current_data_eligibility.append(
            _eligibility_audit_for_surface(
                db,
                spec=spec,
                user=user,
                cutoff=cutoff,
                metrics=metrics,
            )
        )

    surface_activity = {
        surface_id: _surface_activity_counts(
            spec=spec,
            decisions=decisions,
            render_counts=render_counts,
            render_exposure_ids=render_exposure_ids,
            suppression_exposure_ids=suppression_exposure_ids,
        )
        for surface_id, spec in sorted(registry.items())
    }

    return {
        "schema_version": "output_surface_diagnostics_v1",
        "window_days": window_days,
        "registry": {
            "registered_surface_count": len(registry),
            "truth_class_counts": dict(
                sorted(Counter(spec.truth_class for spec in registry.values()).items())
            ),
            "usage_class_counts": dict(
                sorted(Counter(spec.usage_class for spec in registry.values()).items())
            ),
            "unregistered_render_surfaces": sorted(set(render_counts) - registered),
            "unregistered_decision_triggers": sorted(
                {
                    row.trigger_source
                    for row in decisions
                    if "." in row.trigger_source and row.trigger_source not in registered
                }
            ),
        },
        "dual_write": {
            "decisions": len(decisions),
            "renders": len(renders),
            "suppressions": len(suppressions),
            "decision_without_terminal_event_count": len(missing_terminal_ids),
            "decision_without_terminal_event_ids": missing_terminal_ids[:50],
            "surface_activity": surface_activity,
        },
        "legacy_adapter_reliance": legacy_adapter_reliance,
        "current_data_eligibility": current_data_eligibility,
    }
