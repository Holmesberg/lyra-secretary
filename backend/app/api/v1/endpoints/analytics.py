"""Analytics endpoints â€” discrepancy experiment measurement layer."""
import json
from time import monotonic
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_db, operator_user_from_scope
from app.core.authority import authority_for_surface
from app.db.models import (
    Archetype,
    ArchetypeAssignment,
    ExposureDecisionEvent,
    Task,
    TaskState,
    User,
)
from app.db.scoping import get_current_user_id
from app.services.interruption_metrics import task_interruption_metrics_from_sessions
from app.services.cortex import (
    planning_calibration_query,
)
from app.services.calibration_nudge_analytics_service import calibration_nudge_snapshot
from app.services.analytics_bias_lookup_cache import (
    cached_bias_lookup_response,
    log_slow_bias_lookup,
    store_bias_lookup_response,
)
from app.services.analytics_insight_helpers import (
    abs_minutes as _abs_minutes,
    average as _avg,
    build_insight_candidate as _insight,
    category_for_insight as _category_for_insight,
    is_historical_task as _is_historical_task,
    median as _median,
    not_started as _not_started,
    time_of_day as _time_of_day,
)
from app.services.analytics_insight_public_packaging import (
    AUTHORITY_LABELS,
    CONFIDENCE_LABELS,
    INSIGHT_TITLES,
    insights_exposure_snapshot as _insights_exposure_snapshot,
    public_insight_card as _public_insight,
)
from app.services.analytics_insight_rule11 import (
    ANALYTICS_INSIGHTS_SURFACE_ID,
    ANALYTICS_INSIGHTS_TEMPLATE_ID,
    INSIGHTS_RULE11_REOPEN_CLEAN_SESSIONS,
    insights_rule11_hold_message as _insights_rule11_hold_message,
    insights_rule11_reopen_gate as _insights_rule11_reopen_gate,
)
from app.services.analytics_surface_eligibility import (
    eligible_tasks_for_surface_cached as _eligible_tasks_for_surface_cached,
    eligible_tasks_for_surface as _eligible_tasks_for_surface,
    surface_metadata as _surface_metadata,
)
from app.services.deadline_completion_analytics_service import deadline_completion_snapshot
from app.services.deadline_shape_service import deadline_shape_snapshot
from app.services.pause_prediction_analytics_service import pause_prediction_snapshot
from app.services.discrepancy_analytics_service import discrepancy_snapshot
from app.services.cascade_analytics_service import cascade_snapshot
from app.services.claim_compiler import (
    PRIMARY_SYNTHESIS_ID,
    PRIMARY_SYNTHESIS_SURFACE_ID,
    compile_primary_synthesis,
)
from app.services.output_surfaces import (
    RULE11_ACTIVE_ARM,
    RULE11_CONTROL_ARM,
    RULE11_POLICY_VERSION,
    RULE11_SUPPRESSION_REASON,
    create_output_surface_decision,
    emit_surface_suppression,
    get_output_surface_spec,
    rule11_no_nudge_control_active,
    rule11_randomization_fields,
)
from app.utils.time_utils import now_utc
from app.utils.redis_client import RedisClient

router = APIRouter()

@router.get("/analytics/discrepancy")
def get_discrepancy(db: Session = Depends(get_db)) -> dict:
    """Return discrepancy measurement data in research and product layers."""
    return discrepancy_snapshot(db)


# ---------------------------------------------------------------------------
# Individual insight generators - compatibility re-exports
# ---------------------------------------------------------------------------

from app.services.analytics_insight_generators import (
    CONTRACT_SAFE_INSIGHT_GENERATORS,
    LEGACY_SUPPRESSED_INSIGHT_SURFACES,
    PROFILE_AWARE_INSIGHT_GENERATORS,
    _insight_abandonment,
    _insight_archetype_divergence,
    _insight_best_category,
    _insight_calibration_maturation,
    _insight_discrepancy_signal,
    _insight_estimation_trend,
    _insight_initiation_delay,
    _insight_morning_anchor,
    _insight_occupancy_footprint,
    _insight_pause_pattern,
    _insight_readiness,
    _insight_readiness_time_of_day,
    _insight_retroactive_rate,
    _insight_time_of_day,
    _insight_worst_category,
)
# ---------------------------------------------------------------------------
# Insights endpoint
# ---------------------------------------------------------------------------

@router.get("/analytics/insights")
def get_insights(
    auto_mark: bool = Query(False, description="Mark returned unseen insights as seen in Redis (24h TTL)"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Generate up to 5 plain-language behavioral observations from task history,
    sorted by strength (largest signal first).

    Rule-based only â€” no ML. Execution insights require enough clean executed
    sessions; planning-history insights may render from descriptive history.
    Pass ?auto_mark=true to suppress already-shown insights (24h cooldown per insight_id).
    """
    surface_id = ANALYTICS_INSIGHTS_SURFACE_ID
    parent_spec = get_output_surface_spec(surface_id)
    MIN_SESSIONS = parent_spec.min_n
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")

    all_tasks = (
        db.query(Task)
        .filter(
            Task.user_id == uid,
            Task.initiation_status != "system_error",
            Task.voided_at.is_(None),
        )
        .order_by(Task.planned_start_utc)
        .all()
    )
    eligibility_cache: dict[tuple, set[str]] = {}
    clean_tasks = _eligible_tasks_for_surface_cached(
        db,
        all_tasks,
        surface_id,
        eligibility_cache,
        eligible_tasks_fn=_eligible_tasks_for_surface,
    )

    # Gate check: need at least MIN_SESSIONS executed tasks with delta data
    delta_sessions = [
        t for t in clean_tasks
        if t.state == TaskState.EXECUTED and t.duration_delta_minutes is not None
    ]
    sessions_analyzed = len(delta_sessions)
    unlocked = sessions_analyzed >= MIN_SESSIONS
    history_events_analyzed = len(
        [
            t for t in all_tasks
            if t.state != TaskState.DELETED and _is_historical_task(t)
        ]
    )
    suppressed_generators = [
        {
            **_surface_metadata(
                suppressed_surface_id,
                eligible_sample_count=0,
                suppressed_reason="requires_insights_rewrite",
            ),
            "id": insight_id,
            "owner": "Insights Rewrite",
            "deadline": "Wave 3",
        }
        for suppressed_surface_id, insight_id in LEGACY_SUPPRESSED_INSIGHT_SURFACES
    ]

    candidates = []
    for insight_surface_id, gen in CONTRACT_SAFE_INSIGHT_GENERATORS:
        generator_tasks = _eligible_tasks_for_surface_cached(
            db,
            all_tasks,
            insight_surface_id,
            eligibility_cache,
            eligible_tasks_fn=_eligible_tasks_for_surface,
        )
        result = gen(generator_tasks)
        if result is not None:
            result.update(
                _surface_metadata(
                    insight_surface_id,
                    eligible_sample_count=len(generator_tasks),
                    suppressed_reason=None,
                )
            )
            candidates.append(result)

    user = db.query(User).filter(User.user_id == uid).first()
    archetype = None
    if user is not None and user.archetype_id:
        archetype = (
            db.query(Archetype)
            .filter(Archetype.archetype_id == user.archetype_id)
            .first()
        )
    for insight_surface_id, gen in PROFILE_AWARE_INSIGHT_GENERATORS:
        generator_tasks = _eligible_tasks_for_surface_cached(
            db,
            all_tasks,
            insight_surface_id,
            eligibility_cache,
            eligible_tasks_fn=_eligible_tasks_for_surface,
        )
        result = gen(generator_tasks, archetype)
        if result is not None:
            result.update(
                _surface_metadata(
                    insight_surface_id,
                    eligible_sample_count=len(generator_tasks),
                    suppressed_reason=None,
                )
            )
            candidates.append(result)

    primary_synthesis = compile_primary_synthesis(
        candidates,
        history_events_analyzed=history_events_analyzed,
    )
    if primary_synthesis is not None:
        primary_synthesis.update(
            _surface_metadata(
                PRIMARY_SYNTHESIS_SURFACE_ID,
                eligible_sample_count=history_events_analyzed,
                suppressed_reason=None,
            )
        )
        candidates.append(primary_synthesis)

    if not candidates and sessions_analyzed < MIN_SESSIONS:
        remaining = MIN_SESSIONS - sessions_analyzed
        suppression = _surface_metadata(
            surface_id,
            eligible_sample_count=sessions_analyzed,
            suppressed_reason="insufficient_clean_samples",
        )
        try:
            emit_surface_suppression(
                db,
                surface_id=surface_id,
                user_id=uid,
                suppression_reason="insufficient_clean_samples",
                content_template_id="analytics_insights",
                trigger_source="analytics.insights",
            )
            db.commit()
        except Exception:
            db.rollback()
        return {
            **suppression,
            "insights": [],
            "sessions_analyzed": sessions_analyzed,
            "history_events_analyzed": history_events_analyzed,
            "min_sessions_required": MIN_SESSIONS,
            "unlocked": False,
            "ready": False,
            "message": f"Log {remaining} more executed session{'s' if remaining != 1 else ''} to unlock execution insights.",
            "suppressed_generators": suppressed_generators,
        }

    # Sort by strength (largest signal first), then by data_points
    candidates.sort(key=lambda r: (r.get("strength", 0.0), r.get("data_points", 0)), reverse=True)

    redis = RedisClient()
    insights = []
    for result in candidates:
        insight_id = result["id"]
        redis_key = f"insight_shown:{uid}:{insight_id}"
        result["seen"] = bool(redis.client.exists(redis_key))
        if auto_mark and result["seen"]:
            continue
        if auto_mark:
            redis.client.setex(redis_key, 86400, "1")
            result["seen"] = True
        insights.append(_public_insight(result))

    response_metadata = _surface_metadata(
        surface_id,
        eligible_sample_count=sessions_analyzed,
        suppressed_reason=None if insights else "no_contract_safe_insights",
    )
    response_payload = {
        **response_metadata,
        "insights": insights,
        "sessions_analyzed": sessions_analyzed,
        "history_events_analyzed": history_events_analyzed,
        "min_sessions_required": MIN_SESSIONS,
        "unlocked": unlocked or bool(candidates),
        "ready": True,
        "suppressed_generators": suppressed_generators,
    }
    try:
        if insights:
            eligible_at = now_utc()
            arm, policy = rule11_randomization_fields(
                db, user_id=uid, surface_id=surface_id, eligible_at=eligible_at
            )
            rule11_control_active = rule11_no_nudge_control_active(
                db, user_id=uid, surface_id=surface_id, eligible_at=eligible_at
            )
            reopen_gate = (
                _insights_rule11_reopen_gate(
                    db,
                    user_id=uid,
                    delta_sessions=delta_sessions,
                    eligible_at=eligible_at,
                )
                if rule11_control_active
                else None
            )
            if rule11_control_active and reopen_gate and reopen_gate["should_hold"]:
                emit_surface_suppression(
                    db,
                    surface_id=surface_id,
                    user_id=uid,
                    suppression_reason=RULE11_SUPPRESSION_REASON,
                    eligible_at=eligible_at,
                    suppressed_at=eligible_at,
                    content_template_id=ANALYTICS_INSIGHTS_TEMPLATE_ID,
                    trigger_source=ANALYTICS_INSIGHTS_SURFACE_ID,
                    randomization_arm=arm,
                    randomization_policy_version=policy,
                )
                response_payload.update(
                    _surface_metadata(
                        surface_id,
                        eligible_sample_count=sessions_analyzed,
                        suppressed_reason=RULE11_SUPPRESSION_REASON,
                    )
                )
                response_payload["insights"] = []
                response_payload["ready"] = False
                response_payload["unlocked"] = True
                response_payload.update(
                    {
                        "reopen_after_clean_sessions": reopen_gate[
                            "reopen_after_clean_sessions"
                        ],
                        "new_clean_sessions_since_hold": reopen_gate[
                            "new_clean_sessions_since_hold"
                        ],
                        "clean_sessions_until_reopen": reopen_gate[
                            "clean_sessions_until_reopen"
                        ],
                        "message": _insights_rule11_hold_message(
                            int(reopen_gate["clean_sessions_until_reopen"])
                        ),
                    }
                )
            else:
                if rule11_control_active and reopen_gate:
                    arm = RULE11_ACTIVE_ARM
                render_snapshot = _insights_exposure_snapshot(
                    response_payload,
                    candidates,
                )
                decision = create_output_surface_decision(
                    db,
                    surface_id=surface_id,
                    user_id=uid,
                    decision_status="reserved",
                    eligible_at=eligible_at,
                    content_template_id=ANALYTICS_INSIGHTS_TEMPLATE_ID,
                    trigger_source=ANALYTICS_INSIGHTS_SURFACE_ID,
                    randomization_arm=arm,
                    randomization_policy_version=policy,
                )
                response_payload["exposure_id"] = decision.exposure_id
                response_payload["render_snapshot"] = render_snapshot
        else:
            emit_surface_suppression(
                db,
                surface_id=surface_id,
                user_id=uid,
                suppression_reason="no_contract_safe_insights",
                content_template_id=ANALYTICS_INSIGHTS_TEMPLATE_ID,
                trigger_source=ANALYTICS_INSIGHTS_SURFACE_ID,
            )
        db.commit()
    except Exception:
        db.rollback()
        if insights:
            failure_metadata = _surface_metadata(
                surface_id,
                eligible_sample_count=sessions_analyzed,
                suppressed_reason="exposure_emit_failed",
            )
            return {
                **failure_metadata,
                "insights": [],
                "sessions_analyzed": sessions_analyzed,
                "history_events_analyzed": history_events_analyzed,
                "min_sessions_required": MIN_SESSIONS,
                "unlocked": unlocked,
                "ready": False,
                "message": "Insights are temporarily unavailable while exposure logging catches up.",
                "suppressed_generators": suppressed_generators,
            }

    return response_payload


def _require_operator_analytics(db: Session, request: Request | None = None) -> User:
    return operator_user_from_scope(db, request=request)


@router.post("/analytics/exposure_policy/effect_log")
def record_exposure_policy_effect_log(
    request: Request,
    window_days: int = Query(30, ge=1, le=365, description="Look-back window in days"),
    db: Session = Depends(get_db),
) -> dict:
    """Operator-only snapshot of exposure gate behavior.

    This writes meta-instrumentation about the horizon policy, not behavioral
    learning data. It exists so the operator can detect when the gate becomes
    invisible authority: high UNKNOWN rate, ledger-incomplete drift, or broad
    EXPOSED collapse.
    """
    op = _require_operator_analytics(db, request)
    from app.services.cortex import measured_execution_query
    from app.services.exposure_ledger import (
        DEFAULT_HORIZON_POLICY_VERSION,
        record_policy_effect_snapshot,
    )

    cutoff = now_utc() - timedelta(days=max(1, min(365, int(window_days))))
    window_end = now_utc()
    tasks = measured_execution_query(db, user_id=op.user_id, cutoff=cutoff).all()
    rows = record_policy_effect_snapshot(
        db,
        user_id=op.user_id,
        tasks=tasks,
        signal_targets=["duration_behavior", "planning_estimate"],
        window_start=cutoff,
        window_end=window_end,
    )
    db.commit()
    return {
        "policy_version": DEFAULT_HORIZON_POLICY_VERSION,
        "window_days": max(1, min(365, int(window_days))),
        "rows": [
            {
                "log_id": row.log_id,
                "signal_target": row.signal_target,
                "exposure_category": row.exposure_category,
                "state_distribution_counts": row.state_distribution_counts,
                "unknown_rate": row.unknown_rate,
                "ledger_incomplete_rate": row.ledger_incomplete_rate,
                "sample_count": row.sample_count,
            }
            for row in rows
        ],
    }


# ---------------------------------------------------------------------------
# Cascade Analytics
# ---------------------------------------------------------------------------

@router.get("/analytics/cascade")
def get_cascade(
    days: int = Query(7, ge=1, le=90, description="Look-back window in days"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Cascade failure analysis: does skipping/abandoning task N predict
    skipping task N+1?

    Returns per-day cascade chains, morning-anchor analysis, and
    aggregate cascade_score = P(skip N+1 | skip N).
    """
    return cascade_snapshot(db, days=days)


# ---------------------------------------------------------------------------
# Bias Factor
# ---------------------------------------------------------------------------

# `_bias_cell` extracted to services/bias_factor_service.py on 2026-04-22
# (Phase A of the clustering ship). Re-exported here so existing call
# sites in this module keep working unchanged. See MANIFESTO.md v1.10
# Rule 13 for the canonical computation definition.
from app.services.bias_factor_service import (
    RESEARCH_PRIOR_DEFAULT as _SVC_RESEARCH_PRIOR_DEFAULT,
    RESEARCH_PRIORS as _SVC_RESEARCH_PRIORS,
    _adaptive_calibration as _svc_adaptive_calibration,
    _bias_cell as _svc_bias_cell,
    bias_factor_snapshot,
)

_bias_cell = _svc_bias_cell


@router.get("/analytics/bias_factor")
def get_bias_factor(
    min_sessions: int = Query(3, ge=2, le=50, description="Minimum sessions per bucket"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Per (category, time_of_day) estimation bias factor with fallback aggregations.

    Returns the primary cells (category Ã— time_of_day) plus three fallback layers
    (category-only, time_of_day-only, global) that a scheduler can fall back through
    when a specific cell lacks data. Also returns the list of insufficient cells so
    the operator can see what is data-starved.

    Both ratios are returned per cell:
        bias_factor       â€” sum(executed) / sum(planned)        â€” PRIMARY
        bias_factor_mean  â€” mean(executed_i / planned_i)        â€” sanity check

    bias_factor > 1.0 â†’ tasks run longer than planned (underestimates).
    Excludes retroactive sessions (delta=0 by construction; would corrupt the ratio).

    VT-29 filter (added 2026-04-30): exclude tasks bound to externally-
    imported deadlines (Moodle .ics, future LMS sources). Imported
    deadlines have a fundamentally different planning context (LMS sets
    the time, not the user) so their tasks' bias_factor reflects the
    interaction between user-planning and external-constraint, not
    user-planning alone. Tasks with no deadline binding stay in (they
    can never be external by construction).
    """
    return bias_factor_snapshot(db, min_sessions=min_sessions)


# RESEARCH_PRIORS + RESEARCH_PRIOR_DEFAULT extracted to
# services/bias_factor_service.py (2026-04-22, Phase A). These module-level
# names remain for backward compatibility with any call site that still
# imports them from here.
RESEARCH_PRIORS = _SVC_RESEARCH_PRIORS
RESEARCH_PRIOR_DEFAULT = _SVC_RESEARCH_PRIOR_DEFAULT


# _adaptive_calibration was extracted to services/bias_factor_service.py
# on 2026-04-22 (Phase A of the clustering ship). Re-exported as a
# module-level alias so `analytics._adaptive_calibration(...)` call
# sites keep working without edits. See MANIFESTO.md v1.10 Rule 13.
_adaptive_calibration = _svc_adaptive_calibration


@router.get("/analytics/bias_factor/lookup")
def bias_factor_lookup(
    category: str = Query(..., description="Task category"),
    tod: str = Query(..., description="Time-of-day bucket (morning/afternoon/evening/night)"),
    planned_minutes: int = Query(30, ge=1, description="Planned duration for duration-bucket signal"),
    fast: bool = Query(False, description="Use research-prior fast path for latency-sensitive UI"),
    exposure_id: Optional[str] = Query(
        None,
        max_length=64,
        description="Optional client-minted exposure ID for optimistic render reconciliation",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """Canonical calibration lookup per MANIFESTO Rule 13.

    Returns the shrinkage-blended `bias_factor_final` (frontend
    calibration_nudge consumes this) PLUS the full `_adaptive_calibration`
    cascade metadata for transparency:

      bias_factor_final          â€” (1-w) Ã— archetype_prior_for_cell
                                  + w Ã— personal_sum_ratio_for_cell
                                  where w = min(1.0, n/30)
      personal_weight, prior_weight â€” the blend ratio used
      archetype_id, archetype_prior_bias_factor â€” which archetype fired
      archetype_prior_for_cell, archetype_scaling â€” composite scaling trace
      cell.bias_factor           â€” personal-only diagnostic (pre-blend)
      signal_level, signals      â€” cascade provenance

    When the user has no ArchetypeAssignment, archetype_id resolves to
    `diffuse_average` (population midpoint) â€” NOT flat 1.0, so every
    user still benefits from a research-backed prior at cold start.
    """
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    cache_key = (uid, category, tod, planned_minutes, int(fast), exposure_id or "")
    cached = cached_bias_lookup_response(cache_key)
    if cached is not None:
        return cached
    lookup_started = monotonic()
    tasks_ms = 0.0
    blend_ms = 0.0
    exposure_ms = 0.0
    # Rule 13 operational definition of n_sessions_in_cell (MANIFESTO
    # v1.10 Â§13): planned_duration_minutes >= 5. The 5-minute floor
    # matches the H1 exclusion threshold (Rule 4) â€” sub-5-minute tasks
    # are dominated by startup overhead, not planning-fallacy signal.
    #
    # VT-29 filter (added 2026-04-30): exclude tasks bound to externally-
    # imported deadlines. Same rationale as the bias_factor surface above.
    from app.services.bias_factor_service import blend, research_prior_projection
    if fast:
        tasks = []
    else:
        candidate_query = planning_calibration_query(db, user_id=uid)
        if category == "uncategorized":
            candidate_query = candidate_query.filter(
                or_(Task.category.is_(None), Task.category == category)
            )
        else:
            candidate_query = candidate_query.filter(Task.category == category)
        phase_started = monotonic()
        tasks = candidate_query.all()
        tasks_ms = (monotonic() - phase_started) * 1000
    phase_started = monotonic()
    result = (
        research_prior_projection(category, tod, planned_minutes)
        if fast
        else blend(db, uid, tasks, category, tod, planned_minutes)
    )
    blend_ms = (monotonic() - phase_started) * 1000
    cell = result.get("cell")
    magnitude = result.get("bias_factor_final")
    if magnitude is None and cell is not None:
        magnitude = cell.get("bias_factor")
    threshold = 1.20 if result.get("source") == "research" else 1.25
    occupancy_factor = result.get("occupancy_factor")
    pause_sample_size = result.get("pause_overhead_sample_size") or 0
    execution_triggered = magnitude is not None and magnitude >= threshold
    occupancy_triggered = (
        occupancy_factor is not None
        and occupancy_factor >= threshold
        and pause_sample_size >= 3
    )
    if cell is not None and (execution_triggered or occupancy_triggered):
        exposure_started = monotonic()
        suggested_minutes = (
            result.get("occupancy_suggested_minutes")
            or result.get("execution_suggested_minutes")
            or max(5, round((planned_minutes * (magnitude or 1.0)) / 5) * 5)
        )
        surface_id = "task.creation_nudge"
        eligible_at = now_utc()
        arm, policy = rule11_randomization_fields(
            db, user_id=uid, surface_id=surface_id, eligible_at=eligible_at
        )
        try:
            if rule11_no_nudge_control_active(
                db, user_id=uid, surface_id=surface_id, eligible_at=eligible_at
            ):
                emitted = emit_surface_suppression(
                    db,
                    surface_id=surface_id,
                    user_id=uid,
                    suppression_reason=RULE11_SUPPRESSION_REASON,
                    eligible_at=eligible_at,
                    suppressed_at=eligible_at,
                    content_template_id="task_creation_nudge_lookup",
                    initiative="system",
                    trigger_source="analytics.bias_factor.lookup",
                    randomization_arm=arm,
                    randomization_policy_version=policy,
                )
                db.commit()
                exposure_ms = (monotonic() - exposure_started) * 1000
                total_ms = (monotonic() - lookup_started) * 1000
                log_slow_bias_lookup(
                    user_id=uid,
                    category=category,
                    tod=tod,
                    planned_minutes=planned_minutes,
                    tasks_ms=tasks_ms,
                    blend_ms=blend_ms,
                    exposure_ms=exposure_ms,
                    total_ms=total_ms,
                    source=result.get("source"),
                    sessions=result.get("sessions"),
                )
                return store_bias_lookup_response(cache_key, {
                    "cell": None,
                    "sessions": result.get("sessions", 0),
                    "min_sessions": result.get("min_sessions", 3),
                    "source": result.get("source"),
                    "execution_suggested_minutes": result.get("execution_suggested_minutes"),
                    "pause_overhead_minutes": result.get("pause_overhead_minutes"),
                    "pause_overhead_sample_size": result.get("pause_overhead_sample_size"),
                    "occupancy_suggested_minutes": result.get("occupancy_suggested_minutes"),
                    "occupancy_strategy": result.get("occupancy_strategy"),
                    "occupancy_factor": result.get("occupancy_factor"),
                    "suppressed_reason": emitted["suppressed_reason"],
                    "surface_id": emitted["surface_id"],
                    "truth_class": emitted["truth_class"],
                    "signal_targets": emitted["signal_targets"],
                    "clean_profile": emitted["clean_profile"],
                    "fallback_mode": emitted["fallback_mode"],
                    "exposure_id": emitted["exposure_id"],
                    "suppression_id": emitted["suppression_id"],
                })
            spec = get_output_surface_spec(surface_id)
            authority = authority_for_surface(spec).as_dict()
            decision = create_output_surface_decision(
                db,
                surface_id=surface_id,
                user_id=uid,
                decision_status="delivered",
                eligible_at=eligible_at,
                content_template_id="task_creation_nudge_lookup",
                initiative="system",
                trigger_source="analytics.bias_factor.lookup",
                delivered_at=eligible_at,
                randomization_arm=arm,
                randomization_policy_version=policy,
                exposure_id=exposure_id,
            )
            db.commit()
            exposure_ms = (monotonic() - exposure_started) * 1000
            result.update(
                {
                    "surface_id": surface_id,
                    "truth_class": spec.truth_class,
                    "signal_targets": list(spec.signal_targets),
                    "clean_profile": spec.clean_profile,
                    "fallback_mode": spec.fallback_mode,
                    "exposure_id": decision.exposure_id,
                    "render_id": None,
                    **authority,
                }
            )
        except Exception:
            db.rollback()
            exposure_ms = (monotonic() - exposure_started) * 1000
            total_ms = (monotonic() - lookup_started) * 1000
            log_slow_bias_lookup(
                user_id=uid,
                category=category,
                tod=tod,
                planned_minutes=planned_minutes,
                tasks_ms=tasks_ms,
                blend_ms=blend_ms,
                exposure_ms=exposure_ms,
                total_ms=total_ms,
                source=result.get("source"),
                sessions=result.get("sessions"),
            )
            return store_bias_lookup_response(cache_key, {
                "cell": None,
                "sessions": result.get("sessions", 0),
                "min_sessions": result.get("min_sessions", 3),
                "source": result.get("source"),
                "execution_suggested_minutes": result.get("execution_suggested_minutes"),
                "pause_overhead_minutes": result.get("pause_overhead_minutes"),
                "pause_overhead_sample_size": result.get("pause_overhead_sample_size"),
                "occupancy_suggested_minutes": result.get("occupancy_suggested_minutes"),
                "occupancy_strategy": result.get("occupancy_strategy"),
                "occupancy_factor": result.get("occupancy_factor"),
                "suppressed_reason": "exposure_emit_failed",
                "surface_id": "task.creation_nudge",
                "truth_class": "intervention",
                "signal_targets": ["planning_estimate", "pause_behavior"],
                "clean_profile": "planning_calibration",
                "fallback_mode": "suppress",
            })
    total_ms = (monotonic() - lookup_started) * 1000
    log_slow_bias_lookup(
        user_id=uid,
        category=category,
        tod=tod,
        planned_minutes=planned_minutes,
        tasks_ms=tasks_ms,
        blend_ms=blend_ms,
        exposure_ms=exposure_ms,
        total_ms=total_ms,
        source=result.get("source"),
        sessions=result.get("sessions"),
    )
    return store_bias_lookup_response(cache_key, result)


@router.get("/analytics/pause_prediction")
def get_pause_prediction(db: Session = Depends(get_db)) -> dict:
    """VT-17 pause-prediction dashboard (scoped to the requesting user).

    Reports firing volume, acceptance_rate, and per-mechanism breakdown
    over the user's full pause_prediction_log history. Unreconciled
    rows (user_response IS NULL) are reported separately â€” they are
    neither counted in acceptance_rate numerator nor denominator.

    Acceptance-rate formula (MANIFESTO Â§VT-17, pre-registered, frozen at
    launch):

        acceptance_rate = acceptance_count / total_fires

    where total_fires EXCLUDES re-fires from snooze chains
    (parent_firing_id IS NOT NULL). VT-17 kill criterion is per-user â€”
    this endpoint IS that per-user view (auto-scoped by X-User-Id).
    Operator cross-user analysis runs in the Commit 5c notebook via
    direct DB reads, bypassing the scoping hook.

    Response shape is flat + nested dicts so the notebook can read it
    without field-name gymnastics; any change to shape is a breaking
    change because cells VT-17a/b/c read specific keys.
    """
    return pause_prediction_snapshot(db)


@router.get("/analytics/deadline-shape")
def get_deadline_shape(
    db: Session = Depends(get_db),
    include_external: bool = False,
) -> dict:
    """Loop 11 â€” per-user deadline-met distribution (MANIFESTO Rules 14, 15).

    Pre-registered at MANIFESTO v1.12 (2026-04-26). Reads
    `task_deadline_outcome` rows (written by Phase H reconciliation job)
    and stratifies along the dimensions specified in Rules 14 + 15:

    - Rule 14: Spearman Ï between `delay_minutes` and signed
      `duration_delta_minutes` is computed downstream by the operator
      notebook from the per-task rows we expose here. Stratification
      by `deadline_match_source` is included.

    - Rule 15: per-deadline `bias_factor_observed = mean(signed delta)
      / mean(planned_minutes)` requires per-deadline aggregation; we
      surface the per-deadline summary so the notebook can compute Ïƒ
      across deadlines per user.

    Voided_at discipline (per `feedback_voided_at_guard` memory):
    every query in this endpoint filters voided rows from BOTH
    `task_deadline_outcome.voided_at IS NULL` AND the underlying
    `task` and `deadline` rows.

    External-source filter (MANIFESTO VT-29, alembic 041, 2026-04-29):
    by default, deadlines imported from third-party sources (Moodle
    iCal, future LMS integrations) are EXCLUDED â€” H2 is a hypothesis
    about user-specified deadlines, and imported rows have no user
    agency in the deadline timestamp. Pass `?include_external=true` to
    run the VT-29 contamination test (effect size with vs without
    imported rows; threshold 0.30).

    Response shape:
      {
        "summary": {
          "total_outcomes": int,
          "deadline_met_count": int,
          "deadline_missed_count": int,
          "deadline_met_rate": float,           # met / total
          "mean_delay_minutes": float,           # signed: + miss, âˆ’ met
          "median_delay_minutes": int,
        },
        "by_match_source": [
          {"source": "user_explicit", "n": ..., "met_rate": ..., "mean_delay": ...},
          {"source": "parser_auto", ...},
          {"source": "user_corrected", ...},
        ],
        "by_scope_bullet_count_band": [
          {"band": "0", "n": ..., "met_rate": ...},        # zero or null
          {"band": "1-3", "n": ..., "met_rate": ...},
          {"band": "4-6", "n": ..., "met_rate": ...},
          {"band": "7+", "n": ..., "met_rate": ...},
        ],
        "per_deadline": [
          {
            "deadline_id": ..., "title": ..., "n": ...,
            "met_rate": ..., "mean_delay_minutes": ...,
            "bias_factor_observed": ...,        # for Rule 15
          },
          ...
        ],
        "primary_metric": "delay_minutes_distribution (MANIFESTO Rule 14, pre-registered)",
      }

    Auto-scoped to current user via `get_current_user_id()`. Operator
    cross-user analysis bypasses this endpoint via direct DB reads.
    """
    uid = get_current_user_id()
    return deadline_shape_snapshot(db, user_id=uid, include_external=include_external)


@router.get("/analytics/deadline-completions")
def get_deadline_completions(
    db: Session = Depends(get_db),
    include_external: bool = False,
) -> dict:
    """Deadline completion/submission behavior, separate from execution truth.

    Reads append-only `deadline_completion_event` rows. Multiple valid events
    per deadline are allowed, so this endpoint reports both behavior-count and
    distinct-deadline metrics. Moodle rows are external submission traces, not
    stopwatch execution traces.
    """
    uid = get_current_user_id()
    return deadline_completion_snapshot(
        db,
        user_id=uid,
        include_external=include_external,
    )


@router.get("/analytics/archetype/proximity")
def get_archetype_proximity(
    days: int = Query(14, ge=1, le=90, description="Lookback window in days"),
    db: Session = Depends(get_db),
) -> dict:
    """VT-25 dynamic-reveal data source. Pre-registered MANIFESTO Rule 17 (2026-04-27).

    Returns per-archetype Bayesian posterior probabilities over the user's
    last N days of EXECUTED, non-voided task data. Frontend renders the
    top-3 archetypes with percentage bars + trend arrows; replaces the
    static "Profile: Procrastinator" reveal that shipped via LYR-112.

    Filters (per Rule 13 + voided_at_guard memory):
      - state == EXECUTED
      - voided_at IS NULL
      - initiation_status != 'system_error'
      - planned_duration_minutes >= 5
      - executed_duration_minutes IS NOT NULL

    Cold start (no qualifying tasks): returns uniform 1/N distribution.
    Frontend renders this as "settling in" copy without the percentage UI.

    Auto-scoped via current_user_id ContextVar.
    """
    from app.services.archetype_proximity_service import compute_proximity

    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    proximity = compute_proximity(db, uid, lookback_days=days)
    n_tasks = proximity[0]["n_tasks"] if proximity else 0
    surface_id = "analytics.archetype_proximity"
    spec = get_output_surface_spec(surface_id)
    ready = n_tasks >= spec.min_n
    metadata = _surface_metadata(
        surface_id,
        eligible_sample_count=n_tasks,
        suppressed_reason=None if ready else "insufficient_clean_samples",
    )
    response_payload = {
        **metadata,
        "proximity": proximity,
        "lookback_days": days,
        "n_tasks": n_tasks,
        "ready": ready,
        "display_mode": "behavioral_proximity" if ready else spec.fallback_mode,
        "primary_metric": "archetype_posterior (MANIFESTO Rule 17, pre-registered)",
    }
    try:
        if ready:
            delivered_at = now_utc()
            decision = create_output_surface_decision(
                db,
                surface_id=surface_id,
                user_id=uid,
                decision_status="delivered",
                eligible_at=delivered_at,
                content_template_id="analytics_archetype_proximity",
                initiative="system",
                trigger_source="analytics.archetype_proximity",
                delivered_at=delivered_at,
            )
            response_payload["exposure_id"] = decision.exposure_id
        else:
            emit_surface_suppression(
                db,
                surface_id=surface_id,
                user_id=uid,
                suppression_reason="insufficient_clean_samples",
                content_template_id="analytics_archetype_proximity",
                trigger_source="analytics.archetype_proximity",
            )
        db.commit()
    except Exception:
        db.rollback()
        if ready:
            response_payload.update(
                _surface_metadata(
                    surface_id,
                    eligible_sample_count=n_tasks,
                    suppressed_reason="exposure_emit_failed",
                )
            )
            response_payload["ready"] = False
            response_payload["display_mode"] = spec.fallback_mode
    return response_payload


@router.get("/analytics/archetype/proximity/trend")
def get_archetype_proximity_trend(
    current_days: int = Query(14, ge=1, le=90, description="Current window"),
    prior_days: int = Query(14, ge=1, le=90, description="Prior window (immediately before current)"),
    db: Session = Depends(get_db),
) -> dict:
    """Current vs prior window comparison for archetype proximity.

    Returns {current, prior, delta_per_archetype, current_window_days,
    prior_window_days}. Powers the frontend "a month ago you were 65/70 â€”
    pattern is consolidating toward Procrastinator" copy.

    Time math:
      current = [now - current_days, now]
      prior   = [now - current_days - prior_days, now - current_days]

    Same per-row shape as /proximity. Pre-registered Rule 17.
    """
    from app.services.archetype_proximity_service import compute_proximity_trend

    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return compute_proximity_trend(db, uid, current_days, prior_days)


@router.get("/analytics/calibration_nudge")
def get_calibration_nudge_outcomes(
    days: int = Query(30, ge=1, le=180, description="Rolling window in days"),
    db: Session = Depends(get_db),
) -> dict:
    """Loop 1 â€” calibration nudge effectiveness (per feedback_loops_closure_plan.md Â§Loop 1).

    Mirrors `/v1/analytics/pause_prediction` shape. Stratified by user_decision
    (accepted | dismissed). Pre-registered primary metric is the
    delta_difference between accepted-vs-dismissed groups: did accepting
    the nudge produce smaller mean overruns than dismissing?

    Filters (per voided_at_guard discipline):
      - voided_at IS NULL on the event row
      - decided_at within the rolling window
      - auto-scoped to current_user via ContextVar

    Outcome fields (executed_duration_minutes, resolved_at) are stamped
    inline by TaskManager.complete_task when the task transitions to
    EXECUTED. Events with NULL outcome are reported as 'unresolved'.
    """
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return calibration_nudge_snapshot(db, user_id=uid, days=days)
