"""Analytics endpoints — discrepancy experiment measurement layer."""
import json
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from collections import defaultdict

from app.api.deps import get_db, operator_user_from_scope
from app.db.models import (
    Archetype,
    ArchetypeAssignment,
    Deadline,
    DeadlineCompletionEvent,
    PausePredictionLog,
    StopwatchSession,
    Task,
    TaskDeadlineOutcome,
    TaskExecutionCorrection,
    TaskState,
    User,
)
from app.db.scoping import get_current_user_id
from app.services.exposure_ledger import baseline_clean_task_ids
from app.services.output_surfaces import (
    RULE11_SUPPRESSION_REASON,
    emit_surface_render,
    emit_surface_suppression,
    get_output_surface_spec,
    rule11_no_nudge_control_active,
    rule11_randomization_fields,
)
from app.utils.time_utils import to_local, now_utc, strip_tz
from app.utils.redis_client import RedisClient

router = APIRouter()


def _time_of_day(local_dt) -> str:
    h = local_dt.hour
    if 5 <= h < 12:
        return "morning"
    elif 12 <= h < 17:
        return "afternoon"
    elif 17 <= h < 21:
        return "evening"
    else:
        return "night"


def _avg(vals: list) -> float:
    return round(sum(vals) / len(vals), 2) if vals else 0.0


@router.get("/analytics/discrepancy")
def get_discrepancy(db: Session = Depends(get_db)) -> dict:
    """
    Return discrepancy measurement data in two separate layers:

    - research_layer: time/behavioral signals (delta, initiation, abandonment)
    - product_layer: cognitive signals (readiness shift, depletion rate)

    Metric semantics (per product_sessions entry):
      - ``discrepancy_score`` = ``abs(pre_task_readiness - post_task_reflection)``
        — unsigned magnitude of the metacognitive gap. Bigger = worse calibration
        regardless of direction. This is the field the falsification engine
        correlates against ``duration_delta_minutes`` for H1.
      - ``signed_discrepancy`` = ``post_task_reflection - pre_task_readiness``
        — direction of the miss. Positive = felt better than expected;
        negative = felt worse. Used for typology classification (Phase 6),
        NOT for H1 (abs magnitude is the pre-registered predictor).

    VT-29 note (2026-04-30): this query does NOT yet filter tasks bound
    to imported deadlines (Moodle .ics, future LMS sources). VT-29's
    literal text protects H2 (deadline-distance hypothesis), not H1
    directly — and the H1 contamination question is whether the user's
    PLANNING affordance differs for imported-deadline-bound tasks
    (it might: LMS sets the time, user can't shift it). Operator
    decision pending: should H1 also exclude tasks where
    `deadline_id IS NOT NULL AND deadline.external_source IS NOT NULL`?
    Defaulting to no filter today; revisit before first H1 publication
    once trusted users have populated meaningful imported-deadline data.
    """
    tasks = (
        db.query(Task)
        .filter(
            (Task.state == TaskState.EXECUTED) |
            (Task.initiation_status.in_(["initiated", "abandoned"]))
        )
        .filter(Task.initiation_status != "system_error", Task.voided_at.is_(None))
        .order_by(Task.planned_start_utc)
        .all()
    )

    research_sessions = []
    product_sessions = []

    for t in tasks:
        local_start = to_local(t.planned_start_utc)
        d = local_start.date()
        # Read the immutable stored index (alembic 012). Fallback to 0 only
        # if the column is null, which should not happen post-backfill.
        session_idx = t.session_index_in_day if t.session_index_in_day is not None else 0

        # Shared identity fields
        common = {
            "task_id": t.task_id,
            "title": t.title,
            "date": d.isoformat(),
            "category": t.category,
            "time_of_day": _time_of_day(local_start),
            "session_index_in_day": session_idx,
        }

        # Sum paused minutes across all stopwatch sessions for this task
        sessions_for_task = (
            db.query(StopwatchSession)
            .filter(StopwatchSession.task_id == t.task_id)
            .all()
        )
        total_paused = sum(s.total_paused_minutes for s in sessions_for_task)

        # Build pause pattern
        pause_reasons = [s.pause_reason for s in sessions_for_task if s.pause_reason]
        pause_initiators = [s.pause_initiator for s in sessions_for_task if s.pause_initiator]
        first_pause_minute = None
        for s in sessions_for_task:
            if s.paused_at_utc and s.start_time_utc:
                mins = int((s.paused_at_utc - s.start_time_utc).total_seconds() / 60)
                if first_pause_minute is None or mins < first_pause_minute:
                    first_pause_minute = mins

        research_sessions.append({
            **common,
            "planned_duration_minutes": t.planned_duration_minutes,
            "executed_duration_minutes": t.executed_duration_minutes,
            "delta_minutes": t.duration_delta_minutes,
            "initiation_status": t.initiation_status,
            "initiation_delay_minutes": t.initiation_delay_minutes,
            "pause_count": t.pause_count,
            "total_paused_minutes": total_paused,
            "pause_pattern": {
                "pause_count": t.pause_count or 0,
                "total_paused_minutes": total_paused,
                "first_pause_at_minute": first_pause_minute,
                "pause_reasons": pause_reasons,
                "pause_initiators": pause_initiators,
            },
            "parent_task_id": t.parent_task_id,
            "interruption_type": t.interruption_type,
            "replaces_task_id": t.replaces_task_id,
        })

        product_sessions.append({
            **common,
            "pre_task_readiness": t.pre_task_readiness,
            "post_task_reflection": t.post_task_reflection,
            "discrepancy_score": t.discrepancy_score,      # abs(pre - post): magnitude
            "signed_discrepancy": t.signed_discrepancy,    # post - pre: direction
        })

    # --- Research layer summary ---
    # B-13 fix (2026-04-26): added explicit voided_at IS NOT NULL filter
    # to honor the voided_at_guard discipline. Previously filtered only
    # on initiation_status='system_error', which leaks any non-voided
    # row that happened to have that status. In practice voiding always
    # stamps initiation_status='system_error' so the count is the same,
    # but the discipline rule is "every Task query checks voided_at."
    voided_count = (
        db.query(Task)
        .filter(
            Task.voided_at.is_not(None),
            Task.initiation_status == "system_error",
        )
        .count()
    )
    total = len(research_sessions)
    initiated = [s for s in research_sessions if s["initiation_status"] == "initiated"]
    abandoned = [s for s in research_sessions if s["initiation_status"] == "abandoned"]
    retroactive = [s for s in research_sessions if s["initiation_status"] == "retroactive"]
    delta_vals = [s["delta_minutes"] for s in research_sessions if s["delta_minutes"] is not None]
    delay_vals = [s["initiation_delay_minutes"] for s in research_sessions if s["initiation_delay_minutes"] is not None]

    interrupted = [s for s in research_sessions if s.get("parent_task_id")]
    substituted = [s for s in research_sessions if s.get("replaces_task_id")]

    # Unplanned reason breakdown
    reason_counts: dict[str, int] = defaultdict(int)
    for t in tasks:
        if t.initiation_status == "retroactive" and t.unplanned_reason:
            reason_counts[t.unplanned_reason] += 1

    # Self-consistency score: per category+time_of_day, variance of discrepancy_score
    consistency_buckets: dict[str, list[int]] = defaultdict(list)
    for t in tasks:
        if t.discrepancy_score is not None and t.category:
            tod = _time_of_day(to_local(t.planned_start_utc))
            key = f"{t.category}_{tod}"
            consistency_buckets[key].append(t.discrepancy_score)

    self_consistency = []
    for key, scores in consistency_buckets.items():
        if len(scores) < 2:
            continue
        mean = sum(scores) / len(scores)
        variance = round(sum((s - mean) ** 2 for s in scores) / len(scores), 2)
        cat, tod = key.rsplit("_", 1)
        self_consistency.append({
            "category": cat,
            "time_of_day": tod,
            "variance": variance,
            "sessions": len(scores),
        })

    research_summary = {
        "total_sessions": total,
        "initiated_count": len(initiated),
        "abandoned_count": len(abandoned),
        "abandoned_rate": round(len(abandoned) / total, 3) if total else 0.0,
        "retroactive_count": len(retroactive),
        "unplanned_execution_rate": round(len(retroactive) / total, 3) if total else 0.0,
        "unplanned_reason_breakdown": dict(reason_counts),
        "avg_delta_minutes": _avg(delta_vals),
        "avg_initiation_delay_minutes": _avg(delay_vals),
        "interruption_rate": round(len(interrupted) / total, 3) if total else 0.0,
        "substitution_rate": round(len(substituted) / total, 3) if total else 0.0,
        "self_consistency_scores": self_consistency,
        "voided_count": voided_count,
    }

    # --- Product layer summary ---
    disc_vals = [s["discrepancy_score"] for s in product_sessions if s["discrepancy_score"] is not None]
    signed_vals = [s["signed_discrepancy"] for s in product_sessions if s["signed_discrepancy"] is not None]
    depleting = [v for v in signed_vals if v < 0]

    product_summary = {
        "total_sessions_with_scores": len(disc_vals),
        "avg_discrepancy": _avg(disc_vals),
        "avg_signed_discrepancy": _avg(signed_vals),
        "depletion_rate": round(len(depleting) / len(signed_vals), 3) if signed_vals else 0.0,
    }

    return {
        "research_layer": {
            "sessions": research_sessions,
            "summary": research_summary,
        },
        "product_layer": {
            "sessions": product_sessions,
            "summary": product_summary,
        },
    }


# ---------------------------------------------------------------------------
# Helpers shared by insights
# ---------------------------------------------------------------------------

def _confidence(n: int) -> str:
    if n >= 11:
        return "high"
    if n >= 6:
        return "medium"
    return "low"


def _insight(
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
        "confidence": _confidence(data_points),
        "strength": round(strength, 3),
    }
    if facts:
        result["_facts"] = facts
    if evidence:
        result["evidence"] = evidence
    return result


def _public_insight(result: dict) -> dict:
    return {
        key: value
        for key, value in result.items()
        if not key.startswith("_")
    }


def _surface_metadata(
    surface_id: str,
    *,
    eligible_sample_count: int = 0,
    suppressed_reason: Optional[str] = None,
) -> dict:
    spec = get_output_surface_spec(surface_id)
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
    }


def _eligible_tasks_for_surface(db: Session, tasks: list, surface_id: str) -> list:
    spec = get_output_surface_spec(surface_id)
    if spec.clean_profile == "descriptive_history":
        return tasks
    clean_ids = baseline_clean_task_ids(
        db,
        tasks=tasks,
        signal_targets=list(spec.signal_targets),
    )
    return [
        task for task in tasks
        if task.task_id in clean_ids and not getattr(task, "is_anchor", False)
    ]


def _median(vals: list[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _abs_minutes(value: float) -> int:
    return int(round(abs(value)))


def _is_historical_task(task: Task) -> bool:
    return strip_tz(task.planned_start_utc) <= strip_tz(now_utc())


LEGACY_CATEGORY_INSIGHT_QUARANTINE = {"work"}


def _category_for_insight(task: Task) -> Optional[str]:
    """Return a category only when it is safe for category-level claims.

    `work` was an early default/fallback bucket used by frontend modals and
    keyword mappings before category provenance existed. Until category
    provenance is stored, it is too contaminated to support "best/worst
    category" or profile-divergence claims.
    """
    category = (task.category or "").strip()
    if not category:
        return None
    if category.lower() in LEGACY_CATEGORY_INSIGHT_QUARANTINE:
        return None
    if category.lower() == "uncategorized":
        return None
    return category


def _not_started(task: Task) -> bool:
    return task.state == TaskState.SKIPPED or task.initiation_status == "abandoned"


# ---------------------------------------------------------------------------
# Individual insight generators — each returns a dict or None
# ---------------------------------------------------------------------------

def _insight_time_of_day(tasks: list) -> Optional[dict]:
    """Time-of-day estimate delta. Picks the TOD with max |avg delta|."""
    buckets: dict[str, list[int]] = defaultdict(list)
    for t in tasks:
        if t.state == TaskState.EXECUTED and t.duration_delta_minutes is not None:
            tod = _time_of_day(to_local(t.planned_start_utc))
            buckets[tod].append(t.duration_delta_minutes)

    best = None  # (tod, avg, n)
    for tod, deltas in buckets.items():
        if len(deltas) < 3:
            continue
        avg = _avg(deltas)
        if best is None or abs(avg) > abs(best[1]):
            best = (tod, avg, len(deltas))

    if best is None or abs(best[1]) < 8:
        return None
    tod, avg, n = best
    if avg > 0:  # delta = planned - executed; positive avg = finished early
        obs = (
            f"In this window, {tod} executed tasks finished "
            f"{_abs_minutes(avg)} min under plan on average."
        )
    else:
        obs = (
            f"In this window, {tod} executed tasks ran "
            f"{_abs_minutes(avg)} min over plan on average."
        )
    return _insight(
        "time_of_day_bias",
        obs,
        n,
        strength=abs(avg),
        facts={
            "time_of_day": tod,
            "average_delta_minutes": avg,
            "direction": "under_plan" if avg > 0 else "over_plan",
        },
    )


def _insight_readiness(tasks: list) -> Optional[dict]:
    """Self-reported readiness compared with absolute estimation error."""
    pairs = [
        (t.pre_task_readiness, abs(t.duration_delta_minutes))
        for t in tasks
        if t.pre_task_readiness is not None and t.duration_delta_minutes is not None
    ]
    if len(pairs) < 6:
        return None

    low = [error for readiness, error in pairs if readiness <= 2]
    high = [error for readiness, error in pairs if readiness >= 4]
    low_label = "1-2"
    high_label = "4-5"
    if len(low) < 3 or len(high) < 3:
        med = _median([p[0] for p in pairs])
        low = [error for readiness, error in pairs if readiness < med]
        high = [error for readiness, error in pairs if readiness > med]
        low_label = f"below {med:g}"
        high_label = f"above {med:g}"
    if len(low) < 3 or len(high) < 3:
        return None

    avg_low_error = _avg(low)
    avg_high_error = _avg(high)
    diff = avg_low_error - avg_high_error
    n = len(low) + len(high)

    if abs(diff) < 5:
        return _insight(
            "readiness_predicts_outcome",
            (
                "In rated sessions, lower and higher readiness starts landed "
                f"within {_abs_minutes(diff)} min of each other on estimation error."
            ),
            n,
            strength=abs(diff),
        )
    if diff > 0:
        return _insight(
            "readiness_predicts_outcome",
            (
                f"In rated sessions, readiness {high_label} landed "
                f"{_abs_minutes(diff)} min closer to plan than readiness {low_label}."
            ),
            n,
            strength=abs(diff),
        )
    return _insight(
        "readiness_predicts_outcome",
        (
            f"In rated sessions, readiness {low_label} landed "
            f"{_abs_minutes(diff)} min closer to plan than readiness {high_label}. "
            "This is a self-report comparison, not an ability claim."
        ),
        n,
        strength=abs(diff),
    )


def _insight_abandonment(tasks: list) -> Optional[dict]:
    """Not-started planned-task rate by TOD and category."""
    tod_total: dict[str, int] = defaultdict(int)
    tod_ab: dict[str, int] = defaultdict(int)
    cat_total: dict[str, int] = defaultdict(int)
    cat_ab: dict[str, int] = defaultdict(int)

    for t in tasks:
        if not _is_historical_task(t) or t.state == TaskState.DELETED:
            continue
        tod = _time_of_day(to_local(t.planned_start_utc))
        tod_total[tod] += 1
        if _not_started(t):
            tod_ab[tod] += 1
        category = _category_for_insight(t)
        if category:
            cat_total[category] += 1
            if _not_started(t):
                cat_ab[category] += 1

    best_tod = None
    for tod, tot in tod_total.items():
        if tot < 5:
            continue
        rate = tod_ab.get(tod, 0) / tot
        if rate >= 0.20 and (best_tod is None or rate > best_tod[1]):
            best_tod = (tod, rate, tot)

    best_cat = None
    for cat, tot in cat_total.items():
        if tot < 3:
            continue
        rate = cat_ab.get(cat, 0) / tot
        if rate >= 0.25 and (best_cat is None or rate > best_cat[1]):
            best_cat = (cat, rate, tot)

    pick = None
    if best_tod and best_cat:
        pick = best_tod if best_tod[1] >= best_cat[1] else best_cat
        kind = "tod" if pick is best_tod else "cat"
    elif best_tod:
        pick, kind = best_tod, "tod"
    elif best_cat:
        pick, kind = best_cat, "cat"
    else:
        return None

    label, rate, n = pick
    not_started = (
        tod_ab.get(label, 0)
        if kind == "tod"
        else cat_ab.get(label, 0)
    )
    pct = round(rate * 100)
    obs = (
        f"In this window, {not_started}/{n} planned {label} tasks were not started ({pct}%)."
        if kind == "tod"
        else f"In this window, {not_started}/{n} {label} tasks were not started ({pct}%)."
    )
    return _insight(
        "abandonment_pattern",
        obs,
        n,
        strength=rate * 100,
        facts={
            "kind": kind,
            "label": label,
            "not_started": not_started,
            "total": n,
            "percent": pct,
        },
    )


def _insight_estimation_trend(tasks: list) -> Optional[dict]:
    """Estimation accuracy trend over last 10 sessions."""
    executed = sorted(
        [t for t in tasks if t.state == TaskState.EXECUTED and t.duration_delta_minutes is not None and t.executed_end_utc],
        key=lambda t: t.executed_end_utc,
        reverse=True,
    )
    if len(executed) < 10:
        return None

    recent = executed[:5]
    older = executed[5:10]
    avg_recent = _avg([abs(t.duration_delta_minutes) for t in recent])
    avg_older = _avg([abs(t.duration_delta_minutes) for t in older])
    improvement = round(avg_older - avg_recent, 1)

    if abs(improvement) < 3:
        return None
    if improvement > 0:
        obs = f"Your time estimates are getting more accurate — down {improvement} min avg error over your last 10 sessions."
    else:
        obs = f"Your estimation error has increased by {abs(improvement)} min over your last 10 sessions."
    return _insight(
        "estimation_accuracy_trend",
        obs,
        10,
        strength=abs(improvement),
        facts={
            "change_minutes": improvement,
            "direction": "improving" if improvement > 0 else "worsening",
        },
    )


def _insight_best_category(tasks: list) -> Optional[dict]:
    """Most predictable task category."""
    cat_errors: dict[str, list[int]] = defaultdict(list)
    for t in tasks:
        category = _category_for_insight(t)
        if t.state == TaskState.EXECUTED and t.duration_delta_minutes is not None and category:
            cat_errors[category].append(abs(t.duration_delta_minutes))

    eligible = {
        cat: errors
        for cat, errors in cat_errors.items()
        if len(errors) >= 3
    }
    if len(eligible) < 2:
        return None

    best_cat, best_median, best_n = None, float("inf"), 0
    for cat, errors in cat_errors.items():
        if len(errors) < 3:
            continue
        median_error = _median(errors)
        if median_error < best_median:
            best_cat, best_median, best_n = cat, median_error, len(errors)

    if best_cat is None:
        return None
    return _insight(
        "best_category",
        (
            f"Among categories with enough data, {best_cat} tasks were closest "
            f"to plan: median error {_abs_minutes(best_median)} min across {best_n} sessions."
        ),
        best_n,
        strength=max(0.0, 60.0 - best_median),  # closer to plan = stronger insight
    )


def _insight_worst_category(tasks: list) -> Optional[dict]:
    """Least predictable task category - the bucket pulling estimation accuracy down."""
    cat_errors: dict[str, list[int]] = defaultdict(list)
    for t in tasks:
        category = _category_for_insight(t)
        if t.state == TaskState.EXECUTED and t.duration_delta_minutes is not None and category:
            cat_errors[category].append(abs(t.duration_delta_minutes))

    eligible = {
        cat: errors
        for cat, errors in cat_errors.items()
        if len(errors) >= 3
    }
    if len(eligible) < 2:
        return None

    worst_cat, worst_median, worst_n = None, 0.0, 0
    for cat, errors in cat_errors.items():
        if len(errors) < 3:
            continue
        median_error = _median(errors)
        if median_error > worst_median:
            worst_cat, worst_median, worst_n = cat, median_error, len(errors)

    if worst_cat is None or worst_median < 20:
        return None
    return _insight(
        "worst_category",
        (
            f"Among categories with enough data, {worst_cat} tasks had the "
            f"widest planning error: median {_abs_minutes(worst_median)} min from plan."
        ),
        worst_n,
        strength=worst_median,
    )


def _insight_discrepancy_signal(tasks: list) -> Optional[dict]:
    """Cognitive shift vs execution error — median split."""
    pairs = [
        (t.discrepancy_score, abs(t.duration_delta_minutes))
        for t in tasks
        if t.discrepancy_score is not None and t.duration_delta_minutes is not None
    ]
    if len(pairs) < 6:
        return None

    med = _median([p[0] for p in pairs])
    high = [e for d, e in pairs if d > med]
    low = [e for d, e in pairs if d <= med]
    if len(high) < 3 or len(low) < 3:
        return None

    avg_high = _avg(high)
    avg_low = _avg(low)
    n = len(high) + len(low)
    if avg_low <= 0:
        return None

    ratio = avg_high / avg_low
    # LYR-061: require ≥20% spread — 15% fired on pairs like (10, 12) which
    # is 17% but clinically meaningless (2-minute delta). Matches the gate in
    # test_discrepancy_signal_returns_none_when_no_signal.
    if abs(ratio - 1) < 0.20:
        return None
    pct = round((ratio - 1) * 100)
    if pct > 0:
        obs = (
            "Where readiness/reflection ratings shifted most, estimation error "
            f"was {pct}% higher in this window."
        )
    else:
        obs = (
            "Where readiness/reflection ratings shifted most, estimation error "
            f"was {abs(pct)}% lower in this window."
        )
    return _insight("discrepancy_signal", obs, n, strength=abs(pct))


def _insight_pause_pattern(tasks: list) -> Optional[dict]:
    """Pause behavior across executed sessions."""
    executed = [t for t in tasks if t.state == TaskState.EXECUTED]
    if len(executed) < 5:
        return None
    paused = [t for t in executed if (t.pause_count or 0) > 0]
    rate = len(paused) / len(executed)
    if rate < 0.25:
        return None
    avg_pauses = _avg([t.pause_count for t in paused])
    pct = round(rate * 100)
    return _insight(
        "pause_pattern",
        (
            f"Recorded pauses appeared in {pct}% of executed sessions; "
            f"paused sessions averaged {avg_pauses} pause events."
        ),
        len(executed),
        strength=rate * 100,
    )


def _insight_morning_anchor(tasks: list) -> Optional[dict]:
    """Cascade signal: does skipping the morning anchor predict the rest of the day?"""
    days_map: dict = defaultdict(list)
    for t in tasks:
        if t.state == TaskState.DELETED:
            continue
        d = to_local(t.planned_start_utc).date()
        days_map[d].append(t)

    days_with_morning = 0
    morning_skipped_days = 0
    morning_skip_cascade = 0
    for d, day_tasks in days_map.items():
        day_tasks_sorted = sorted(day_tasks, key=lambda x: x.planned_start_utc)
        first = day_tasks_sorted[0]
        if to_local(first.planned_start_utc).hour >= 9:
            continue
        days_with_morning += 1
        is_skip = first.state == TaskState.SKIPPED or first.initiation_status == "abandoned"
        if is_skip:
            morning_skipped_days += 1
            rest = day_tasks_sorted[1:]
            if rest:
                rest_skips = sum(1 for x in rest if x.state == TaskState.SKIPPED or x.initiation_status == "abandoned")
                if rest_skips / len(rest) > 0.5:
                    morning_skip_cascade += 1

    if days_with_morning < 3 or morning_skipped_days < 2:
        return None
    cascade_rate = morning_skip_cascade / morning_skipped_days
    if cascade_rate < 0.5:
        return None
    pct = round(cascade_rate * 100)
    return _insight(
        "morning_anchor_cascade",
        (
            "On days where the first task before 9 AM was not started, "
            f"later planned tasks were also mostly not started on "
            f"{morning_skip_cascade}/{morning_skipped_days} days ({pct}%)."
        ),
        morning_skipped_days,
        strength=cascade_rate * 100,
    )


def _insight_retroactive_rate(tasks: list) -> Optional[dict]:
    """How much of execution is logged retroactively rather than planned-then-executed."""
    if len(tasks) < 10:
        return None
    retro = sum(1 for t in tasks if t.initiation_status == "retroactive")
    rate = retro / len(tasks)
    if rate < 0.15:
        return None
    pct = round(rate * 100)
    return _insight(
        "retroactive_rate",
        f"{pct}% of your sessions are logged after the fact rather than planned ahead.",
        len(tasks),
        strength=rate * 100,
    )


def _insight_initiation_delay(tasks: list) -> Optional[dict]:
    """Average minutes between scheduled start and actual start."""
    delays = [
        t.initiation_delay_minutes
        for t in tasks
        if t.initiation_delay_minutes is not None and t.state == TaskState.EXECUTED
    ]
    if len(delays) < 5:
        return None
    avg = _avg(delays)
    if abs(avg) < 5:
        return None
    if avg > 0:
        obs = f"On average you start tasks {round(avg)} min after their scheduled time."
    else:
        obs = f"On average you start tasks {round(abs(avg))} min before their scheduled time."
    return _insight(
        "initiation_delay",
        obs,
        len(delays),
        strength=abs(avg),
        facts={
            "average_delay_minutes": avg,
            "direction": "after_schedule" if avg > 0 else "before_schedule",
        },
    )


# ---------------------------------------------------------------------------
# Primary synthesis composer
# ---------------------------------------------------------------------------

PRIMARY_SYNTHESIS_ID = "primary_synthesis"
PRIMARY_SYNTHESIS_SURFACE_ID = "analytics.insights.primary_synthesis"
PRIMARY_SYNTHESIS_MIN_HISTORY_EVENTS = 30


def _evidence_item(label: str, value: str, source_insight_id: str) -> dict:
    return {
        "label": label,
        "value": value,
        "source_insight_id": source_insight_id,
    }


def _abandonment_evidence_value(insight: dict) -> Optional[str]:
    facts = insight.get("_facts") or {}
    label = facts.get("label")
    not_started = facts.get("not_started")
    total = facts.get("total")
    percent = facts.get("percent")
    if label is None or not_started is None or total is None or percent is None:
        return None
    if facts.get("kind") == "tod":
        return f"{not_started}/{total} planned {label} tasks not started ({percent}%)"
    return f"{not_started}/{total} {label} tasks not started ({percent}%)"


def _time_of_day_evidence_value(insight: dict) -> Optional[str]:
    facts = insight.get("_facts") or {}
    tod = facts.get("time_of_day")
    avg = facts.get("average_delta_minutes")
    if tod is None or avg is None:
        return None
    direction = "under plan" if avg > 0 else "over plan"
    return f"{tod} tasks {round(abs(avg))} min {direction} on average"


def _estimation_trend_evidence_value(insight: dict) -> Optional[str]:
    facts = insight.get("_facts") or {}
    change = facts.get("change_minutes")
    if change is None:
        return None
    if change > 0:
        return f"estimate error down {abs(change):g} min over the last 10 sessions"
    return f"estimate error up {abs(change):g} min over the last 10 sessions"


def _initiation_delay_evidence_value(insight: dict) -> Optional[str]:
    facts = insight.get("_facts") or {}
    avg = facts.get("average_delay_minutes")
    if avg is None:
        return None
    direction = "after schedule" if avg > 0 else "before schedule"
    return f"starts averaged {round(abs(avg))} min {direction}"


def _primary_synthesis_observation(abandonment: dict, supports: list[dict]) -> str:
    abandonment_facts = abandonment.get("_facts") or {}
    category = (
        abandonment_facts.get("label")
        if abandonment_facts.get("kind") == "cat"
        else None
    )
    time_support = next(
        (
            support
            for support in supports
            if support.get("id") == "time_of_day_bias"
        ),
        None,
    )
    time_facts = (time_support or {}).get("_facts") or {}
    tod = time_facts.get("time_of_day")
    late_day = tod in {"evening", "night"}

    if category and late_day:
        return (
            f"Planning drift is currently clustering around {category} tasks "
            "and late-day execution."
        )
    if category:
        return (
            f"Planning drift is currently clustering around {category} tasks, "
            "with supporting execution signals in the same window."
        )
    if tod:
        return (
            f"Planning drift is currently clustering around {tod} task placement, "
            "with supporting execution signals in the same window."
        )
    return (
        "Several current signals point to one planning-reliability cluster "
        "rather than a single isolated metric."
    )


def _compose_primary_synthesis(
    candidates: list[dict],
    *,
    history_events_analyzed: int,
) -> Optional[dict]:
    """Create a bounded synthesis from already registered source insights."""
    by_id = {candidate.get("id"): candidate for candidate in candidates}
    abandonment = by_id.get("abandonment_pattern")
    if abandonment is None or history_events_analyzed < PRIMARY_SYNTHESIS_MIN_HISTORY_EVENTS:
        return None

    support_order = [
        "time_of_day_bias",
        "estimation_accuracy_trend",
        "initiation_delay",
    ]
    supports = [
        by_id[insight_id]
        for insight_id in support_order
        if insight_id in by_id
    ]
    if not supports:
        return None

    evidence = []
    abandonment_value = _abandonment_evidence_value(abandonment)
    if abandonment_value:
        evidence.append(
            _evidence_item(
                "Not-started pattern",
                abandonment_value,
                "abandonment_pattern",
            )
        )

    evidence_builders = {
        "time_of_day_bias": ("Time placement", _time_of_day_evidence_value),
        "estimation_accuracy_trend": ("Estimate drift", _estimation_trend_evidence_value),
        "initiation_delay": ("Start timing", _initiation_delay_evidence_value),
    }
    for support in supports:
        insight_id = support.get("id")
        label_and_builder = evidence_builders.get(insight_id)
        if label_and_builder is None:
            continue
        label, builder = label_and_builder
        value = builder(support)
        if value:
            evidence.append(_evidence_item(label, value, insight_id))

    if len(evidence) < 2:
        return None

    sources = [abandonment, *supports]
    data_points = max(source.get("data_points", 0) for source in sources)
    strength = max(source.get("strength", 0.0) for source in sources) + 50.0
    synthesis = _insight(
        PRIMARY_SYNTHESIS_ID,
        _primary_synthesis_observation(abandonment, supports),
        data_points,
        strength=strength,
        evidence=evidence[:4],
    )
    return synthesis


# ---------------------------------------------------------------------------
# Archetype-aware insight generators (2026-04-22 clustering ship, Rule 13)
#
# These fire ONLY when the user has an Archetype assigned (after taking
# or skipping the survey). They compare the operator's personal
# bias_factor to the archetype prior for the same cell and surface
# emergent patterns: divergence (personal differs from expected prior)
# and maturation (personal_weight has grown enough to dominate).
#
# Depends on SVC_RESEARCH_PRIORS + SVC_RESEARCH_PRIOR_DEFAULT imported
# from bias_factor_service at module top.
# ---------------------------------------------------------------------------


def _insight_archetype_divergence(
    tasks: list, archetype: Optional[Archetype]
) -> Optional[dict]:
    """Personal bias_factor diverges from archetype prior by ≥25%.

    Groups executed tasks by category, computes personal_sum_ratio,
    compares to the archetype-scaled research prior for that category.
    Reports the category with the largest absolute divergence as long
    as the personal sample is ≥5 tasks.

    Meaning: "Your archetype expects X, your data shows Y — you're
    behaving differently from the cohort-level prior in this area."
    Useful even when divergence is downward (person does BETTER than
    their archetype expects — confirmation of discipline) or upward
    (person does WORSE — scope-inflation warning vector).
    """
    if archetype is None:
        return None

    # Group executed tasks by category (ignore uncategorized).
    from collections import defaultdict
    cat_ratios: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for t in tasks:
        category = _category_for_insight(t)
        if (
            t.state != TaskState.EXECUTED
            or t.executed_duration_minutes is None
            or not t.planned_duration_minutes
            or category is None
        ):
            continue
        cat_ratios[category].append(
            (t.planned_duration_minutes, t.executed_duration_minutes)
        )

    best_cat: Optional[str] = None
    best_divergence: float = 0.0
    best_personal: float = 0.0
    best_prior: float = 0.0
    best_n: int = 0

    for cat, pairs in cat_ratios.items():
        if len(pairs) < 5:
            continue
        sum_p = sum(p for p, _ in pairs)
        sum_e = sum(e for _, e in pairs)
        if sum_p <= 0:
            continue
        personal = sum_e / sum_p
        research = RESEARCH_PRIORS.get(cat, RESEARCH_PRIOR_DEFAULT)["bias_factor"]
        archetype_prior_for_cell = research * (archetype.prior_bias_factor / 1.30)
        if archetype_prior_for_cell <= 0:
            continue
        divergence = abs(personal - archetype_prior_for_cell) / archetype_prior_for_cell
        if divergence < 0.25:
            continue
        if divergence > best_divergence:
            best_divergence = divergence
            best_cat = cat
            best_personal = personal
            best_prior = archetype_prior_for_cell
            best_n = len(pairs)

    if best_cat is None:
        return None

    personal_pct = round((best_personal - 1) * 100)
    prior_pct = round((best_prior - 1) * 100)

    def _fmt(pct: int) -> str:
        """Human-readable delta: '+30% over plan', '15% under plan', 'on plan'."""
        if pct > 0:
            return f"+{pct}% over plan"
        if pct < 0:
            return f"{abs(pct)}% under plan"
        return "on plan"

    direction = "below" if best_personal < best_prior else "above"
    obs = (
        f"On {best_cat} tasks, trace data is {_fmt(personal_pct)}, "
        f"{direction} the starting profile prior ({_fmt(prior_pct)}). "
        "Treat this as calibration drift, not an identity label."
    )
    return _insight(
        "archetype_divergence",
        obs,
        best_n,
        strength=best_divergence * 100,
    )


def _insight_calibration_maturation(
    tasks: list, archetype: Optional[Archetype]
) -> Optional[dict]:
    """Personal data has enough volume in ≥1 cell to dominate the blend.

    Per Rule 13, `personal_weight = min(1.0, n_sessions_in_cell / 30)`.
    At n=15, weight ≥ 0.5 — personal is now the majority contributor.
    Fires when the user hits that threshold in any (category,
    time_of_day) cell. Shows the shrinkage learning velocity in
    plain language.
    """
    if archetype is None:
        return None

    from collections import defaultdict
    cell_counts: dict[tuple[str, str], int] = defaultdict(int)
    for t in tasks:
        category = _category_for_insight(t)
        if (
            t.state != TaskState.EXECUTED
            or t.executed_duration_minutes is None
            or not t.planned_duration_minutes
            or category is None
        ):
            continue
        tod = _time_of_day(to_local(t.planned_start_utc))
        cell_counts[(category, tod)] += 1

    # Cells where personal_weight ≥ 0.5 (i.e., n ≥ 15).
    mature_cells = [
        (cat, tod, n)
        for (cat, tod), n in cell_counts.items()
        if n >= 15
    ]
    if not mature_cells:
        return None

    # Pick the highest-volume mature cell for the observation.
    mature_cells.sort(key=lambda x: -x[2])
    top_cat, top_tod, top_n = mature_cells[0]
    weight_pct = round(min(1.0, top_n / 30) * 100)

    obs = (
        f"Personal traces now carry {weight_pct}% of planning calibration "
        f"for {top_cat}/{top_tod} tasks ({top_n} sessions). "
        "The starting prior is mostly a fallback in this cell."
    )
    return _insight(
        "calibration_maturation",
        obs,
        top_n,
        strength=weight_pct,
    )


CONTRACT_SAFE_INSIGHT_GENERATORS = [
    ("analytics.insights.estimation_accuracy_trend", _insight_estimation_trend),
    ("analytics.insights.initiation_delay", _insight_initiation_delay),
    ("analytics.insights.retroactive_rate", _insight_retroactive_rate),
    ("analytics.insights.time_of_day_bias", _insight_time_of_day),
    ("analytics.insights.readiness_predicts_outcome", _insight_readiness),
    ("analytics.insights.abandonment_pattern", _insight_abandonment),
    ("analytics.insights.best_category", _insight_best_category),
    ("analytics.insights.worst_category", _insight_worst_category),
    ("analytics.insights.discrepancy_signal", _insight_discrepancy_signal),
    ("analytics.insights.pause_pattern", _insight_pause_pattern),
    ("analytics.insights.morning_anchor_cascade", _insight_morning_anchor),
]


PROFILE_AWARE_INSIGHT_GENERATORS = [
    ("analytics.insights.archetype_divergence", _insight_archetype_divergence),
    ("analytics.insights.calibration_maturation", _insight_calibration_maturation),
]


LEGACY_SUPPRESSED_INSIGHT_SURFACES = []


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

    Rule-based only — no ML. Execution insights require enough clean executed
    sessions; planning-history insights may render from descriptive history.
    Pass ?auto_mark=true to suppress already-shown insights (24h cooldown per insight_id).
    """
    surface_id = "analytics.insights"
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
    clean_tasks = _eligible_tasks_for_surface(db, all_tasks, surface_id)

    # Gate check: need at least MIN_SESSIONS executed tasks with delta data
    delta_sessions = [
        t for t in clean_tasks
        if t.state == TaskState.EXECUTED and t.duration_delta_minutes is not None
    ]
    sessions_analyzed = len(delta_sessions)
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
        generator_tasks = _eligible_tasks_for_surface(db, all_tasks, insight_surface_id)
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
        generator_tasks = _eligible_tasks_for_surface(db, all_tasks, insight_surface_id)
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

    primary_synthesis = _compose_primary_synthesis(
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
        "ready": True,
        "suppressed_generators": suppressed_generators,
    }
    try:
        if insights:
            eligible_at = now_utc()
            arm, policy = rule11_randomization_fields(
                db, user_id=uid, surface_id=surface_id, eligible_at=eligible_at
            )
            if rule11_no_nudge_control_active(
                db, user_id=uid, surface_id=surface_id, eligible_at=eligible_at
            ):
                emit_surface_suppression(
                    db,
                    surface_id=surface_id,
                    user_id=uid,
                    suppression_reason=RULE11_SUPPRESSION_REASON,
                    eligible_at=eligible_at,
                    suppressed_at=eligible_at,
                    content_template_id="analytics_insights",
                    trigger_source="analytics.insights",
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
            else:
                emitted = emit_surface_render(
                    db,
                    surface_id=surface_id,
                    user_id=uid,
                    content_snapshot=json.dumps(response_payload, sort_keys=True, default=str),
                    eligible_at=eligible_at,
                    rendered_at=eligible_at,
                    content_template_id="analytics_insights",
                    trigger_source="analytics.insights",
                    randomization_arm=arm,
                    randomization_policy_version=policy,
                )
                response_payload["exposure_id"] = emitted["exposure_id"]
                response_payload["render_id"] = emitted["render_id"]
        else:
            emit_surface_suppression(
                db,
                surface_id=surface_id,
                user_id=uid,
                suppression_reason="no_contract_safe_insights",
                content_template_id="analytics_insights",
                trigger_source="analytics.insights",
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
                "ready": False,
                "message": "Insights are temporarily unavailable while exposure logging catches up.",
                "suppressed_generators": suppressed_generators,
            }

    return response_payload


def _require_operator_analytics(db: Session, request: Request | None = None) -> User:
    return operator_user_from_scope(db, request=request)


@router.get("/analytics/behavioral_signature")
def get_behavioral_signature(
    request: Request,
    window_days: int = Query(14, ge=1, le=90, description="Look-back window in days"),
    db: Session = Depends(get_db),
) -> dict:
    """Operator-only aggregated fingerprint (pause mix, valence, reflection dwell, …).

    Same computation as JARVIS ``analyze_behavioral_signature``. Per
    ``docs/calibration_contract.md`` R11 — **not** for Today/Insights rendering;
    use for operator dashboards, scripts, and JARVIS-equivalent HTTP access.
    """
    op = _require_operator_analytics(db, request)
    from app.services.inference_engine import behavioral_signature_for_operator

    return behavioral_signature_for_operator(
        db, op.user_id, window_days=window_days
    )


@router.get("/analytics/cortex/diagnostics")
def get_cortex_diagnostics(
    request: Request,
    window_days: int = Query(30, ge=1, le=365, description="Look-back window in days"),
    db: Session = Depends(get_db),
) -> dict:
    """Operator-only Cortex Core v0 contract diagnostics.

    Read-time instrument audit only. This endpoint does not write state, does
    not infer psychology, and must not be used by user-facing first-paint paths.
    """
    op = _require_operator_analytics(db, request)
    from app.services.cortex import cortex_diagnostics
    from app.services.runtime_topology import backend_topology_report

    payload = cortex_diagnostics(db, user_id=op.user_id, window_days=window_days)
    payload["topology"] = backend_topology_report(request)
    return payload


@router.get("/analytics/output_surfaces/diagnostics")
def get_output_surface_diagnostics(
    request: Request,
    window_days: int = Query(30, ge=1, le=365, description="Look-back window in days"),
    db: Session = Depends(get_db),
) -> dict:
    """Operator-only Wave 4 output-surface enforcement diagnostics."""
    op = _require_operator_analytics(db, request)
    from app.services.output_surfaces import output_surface_diagnostics
    from app.services.runtime_topology import backend_topology_report

    payload = output_surface_diagnostics(db, user_id=op.user_id, window_days=window_days)
    payload["topology"] = backend_topology_report(request)
    return payload


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

    # Group by local date
    days_map: dict[date, list[Task]] = defaultdict(list)
    for t in tasks:
        d = to_local(t.planned_start_utc).date()
        days_map[d].append(t)

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

    def _is_skip(t: Task) -> bool:
        return t.state == TaskState.SKIPPED or t.initiation_status == "abandoned"

    for d in sorted(days_map.keys()):
        day_tasks = [t for t in days_map[d] if t.state != TaskState.DELETED]
        chain = []
        current_streak = 0
        first_skip_time = None
        first_skip_category = None
        consecutive_sequences: list[list[str]] = []
        current_seq: list[str] = []

        for i, t in enumerate(day_tasks):
            skip = _is_skip(t)
            tod = _time_of_day(to_local(t.planned_start_utc))

            # Category / TOD counters for summary
            if t.category:
                category_total_counts[t.category] += 1
                if skip:
                    category_skip_counts[t.category] += 1
            tod_total_counts[tod] += 1
            if skip:
                tod_skip_counts[tod] += 1

            if skip:
                current_streak += 1
                current_seq.append(t.title)
                if first_skip_time is None:
                    first_skip_time = to_local(t.planned_start_utc).strftime("%H:%M")
                    first_skip_category = t.category
            else:
                if current_seq:
                    consecutive_sequences.append(current_seq)
                current_seq = []
                current_streak = 0

            # Track skip-followed-by-skip
            if i > 0:
                prev = day_tasks[i - 1]
                if _is_skip(prev):
                    total_skip_followed_by_any += 1
                    if skip:
                        total_skip_followed_by_skip += 1

            chain.append({
                "task_id": t.task_id,
                "title": t.title,
                "category": t.category,
                "state": t.state.value if hasattr(t.state, "value") else str(t.state),
                "initiation_status": t.initiation_status,
                "is_skip": skip,
                "streak": current_streak,
            })

        if current_seq:
            consecutive_sequences.append(current_seq)

        # Morning anchor analysis (first task before 9am)
        morning_anchor_executed = False
        if day_tasks:
            first = day_tasks[0]
            local_hour = to_local(first.planned_start_utc).hour
            if local_hour < 9:
                total_days_with_morning += 1
                if _is_skip(first):
                    morning_anchor_skips += 1
                    rest_skips = sum(1 for t in day_tasks[1:] if _is_skip(t))
                    if len(day_tasks) > 1 and rest_skips / (len(day_tasks) - 1) > 0.5:
                        morning_anchor_cascade_days += 1
                else:
                    morning_anchor_executed = True
                    morning_anchor_executed_days += 1

        executed_count = sum(1 for t in day_tasks if t.state == TaskState.EXECUTED)
        skipped_count = sum(1 for t in day_tasks if _is_skip(t))
        max_streak = max((c["streak"] for c in chain), default=0)

        # Per-day cascade score
        day_skip_pairs = sum(
            1 for i in range(1, len(day_tasks))
            if _is_skip(day_tasks[i - 1])
        )
        day_skip_skip = sum(
            1 for i in range(1, len(day_tasks))
            if _is_skip(day_tasks[i - 1]) and _is_skip(day_tasks[i])
        )
        day_cascade = round(day_skip_skip / day_skip_pairs, 3) if day_skip_pairs > 0 else 0.0
        all_cascade_scores.append(day_cascade)

        daily_cascades.append({
            "date": d.isoformat(),
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

    # Most cascade-prone category and TOD (highest skip rate with >= 3 tasks)
    most_prone_category = max(
        (c for c in category_total_counts if category_total_counts[c] >= 3),
        key=lambda c: category_skip_counts.get(c, 0) / category_total_counts[c],
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
)

_bias_cell = _svc_bias_cell


@router.get("/analytics/bias_factor")
def get_bias_factor(
    min_sessions: int = Query(3, ge=2, le=50, description="Minimum sessions per bucket"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Per (category, time_of_day) estimation bias factor with fallback aggregations.

    Returns the primary cells (category × time_of_day) plus three fallback layers
    (category-only, time_of_day-only, global) that a scheduler can fall back through
    when a specific cell lacks data. Also returns the list of insufficient cells so
    the operator can see what is data-starved.

    Both ratios are returned per cell:
        bias_factor       — sum(executed) / sum(planned)        — PRIMARY
        bias_factor_mean  — mean(executed_i / planned_i)        — sanity check

    bias_factor > 1.0 → tasks run longer than planned (underestimates).
    Excludes retroactive sessions (delta=0 by construction; would corrupt the ratio).

    VT-29 filter (added 2026-04-30): exclude tasks bound to externally-
    imported deadlines (Moodle .ics, future LMS sources). Imported
    deadlines have a fundamentally different planning context (LMS sets
    the time, not the user) so their tasks' bias_factor reflects the
    interaction between user-planning and external-constraint, not
    user-planning alone. Tasks with no deadline binding stay in (they
    can never be external by construction).
    """
    tasks = (
        db.query(Task)
        .outerjoin(Deadline, Task.deadline_id == Deadline.deadline_id)
        .filter(
            Task.state == TaskState.EXECUTED,
            Task.initiation_status != "system_error",
            Task.voided_at.is_(None),
            Task.is_anchor.is_(False),
            Task.initiation_status != "retroactive",
            Task.executed_duration_minutes != None,
            Task.planned_duration_minutes > 0,
            ~db.query(TaskExecutionCorrection.correction_id)
            .filter(TaskExecutionCorrection.task_id == Task.task_id)
            .exists(),
            # VT-29: exclude tasks bound to imported deadlines.
            (Task.deadline_id.is_(None)) | (Deadline.external_source.is_(None)),
        )
        .all()
    )

    cell_buckets: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    cat_buckets: dict[str, list[tuple[int, int]]] = defaultdict(list)
    tod_buckets: dict[str, list[tuple[int, int]]] = defaultdict(list)
    global_rows: list[tuple[int, int]] = []

    for t in tasks:
        cat = t.category or "uncategorized"
        tod = _time_of_day(to_local(t.planned_start_utc))
        pair = (t.planned_duration_minutes, t.executed_duration_minutes)
        cell_buckets[(cat, tod)].append(pair)
        cat_buckets[cat].append(pair)
        tod_buckets[tod].append(pair)
        global_rows.append(pair)

    cells = []
    insufficient = []
    for (cat, tod), rows in sorted(cell_buckets.items()):
        cell = _bias_cell(rows, min_sessions)
        if cell is None:
            insufficient.append({"category": cat, "time_of_day": tod, "sessions": len(rows)})
            continue
        cell["category"] = cat
        cell["time_of_day"] = tod
        cells.append(cell)

    category_only = []
    for cat, rows in sorted(cat_buckets.items()):
        cell = _bias_cell(rows, min_sessions)
        if cell is None:
            continue
        cell["category"] = cat
        category_only.append(cell)

    time_of_day_only = []
    for tod, rows in sorted(tod_buckets.items()):
        cell = _bias_cell(rows, min_sessions)
        if cell is None:
            continue
        cell["time_of_day"] = tod
        time_of_day_only.append(cell)

    global_cell = _bias_cell(global_rows, min_sessions)

    return {
        "cells": cells,
        "category_only": category_only,
        "time_of_day_only": time_of_day_only,
        "global": global_cell,
        "insufficient_cells": insufficient,
        "min_sessions": min_sessions,
        "total_executed": len(tasks),
        "primary_metric": "bias_factor (sum-ratio)",
    }


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
    db: Session = Depends(get_db),
) -> dict:
    """Canonical calibration lookup per MANIFESTO Rule 13.

    Returns the shrinkage-blended `bias_factor_final` (frontend
    calibration_nudge consumes this) PLUS the full `_adaptive_calibration`
    cascade metadata for transparency:

      bias_factor_final          — (1-w) × archetype_prior_for_cell
                                  + w × personal_sum_ratio_for_cell
                                  where w = min(1.0, n/30)
      personal_weight, prior_weight — the blend ratio used
      archetype_id, archetype_prior_bias_factor — which archetype fired
      archetype_prior_for_cell, archetype_scaling — composite scaling trace
      cell.bias_factor           — personal-only diagnostic (pre-blend)
      signal_level, signals      — cascade provenance

    When the user has no ArchetypeAssignment, archetype_id resolves to
    `diffuse_average` (population midpoint) — NOT flat 1.0, so every
    user still benefits from a research-backed prior at cold start.
    """
    uid = get_current_user_id()
    # Rule 13 operational definition of n_sessions_in_cell (MANIFESTO
    # v1.10 §13): planned_duration_minutes >= 5. The 5-minute floor
    # matches the H1 exclusion threshold (Rule 4) — sub-5-minute tasks
    # are dominated by startup overhead, not planning-fallacy signal.
    #
    # VT-29 filter (added 2026-04-30): exclude tasks bound to externally-
    # imported deadlines. Same rationale as the bias_factor surface above.
    tasks = (
        db.query(Task)
        .outerjoin(Deadline, Task.deadline_id == Deadline.deadline_id)
        .filter(
            Task.state == TaskState.EXECUTED,
            Task.initiation_status != "system_error",
            Task.voided_at.is_(None),
            Task.initiation_status != "retroactive",
            Task.is_anchor.is_(False),
            Task.executed_duration_minutes != None,
            Task.planned_duration_minutes >= 5,
            ~db.query(TaskExecutionCorrection.correction_id)
            .filter(TaskExecutionCorrection.task_id == Task.task_id)
            .exists(),
            # VT-29: exclude tasks bound to imported deadlines.
            (Task.deadline_id.is_(None)) | (Deadline.external_source.is_(None)),
        )
        .all()
    )
    # If scoping is absent (admin or test path), fall through to the
    # legacy personal-only cascade — blend() requires a user_id to look
    # up the archetype. This should not happen under normal auth flow.
    if uid is None:
        return _adaptive_calibration(tasks, category, tod, planned_minutes)
    from app.services.bias_factor_service import blend
    result = blend(db, uid, tasks, category, tod, planned_minutes)
    cell = result.get("cell")
    magnitude = result.get("bias_factor_final")
    if magnitude is None and cell is not None:
        magnitude = cell.get("bias_factor")
    threshold = 1.20 if result.get("source") == "research" else 1.25
    if cell is not None and magnitude is not None and magnitude >= threshold:
        suggested_minutes = max(5, round((planned_minutes * magnitude) / 5) * 5)
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
                return {
                    "cell": None,
                    "sessions": result.get("sessions", 0),
                    "min_sessions": result.get("min_sessions", 3),
                    "source": result.get("source"),
                    "suppressed_reason": emitted["suppressed_reason"],
                    "surface_id": emitted["surface_id"],
                    "truth_class": emitted["truth_class"],
                    "signal_targets": emitted["signal_targets"],
                    "clean_profile": emitted["clean_profile"],
                    "fallback_mode": emitted["fallback_mode"],
                    "exposure_id": emitted["exposure_id"],
                    "suppression_id": emitted["suppression_id"],
                }
            emitted = emit_surface_render(
                db,
                surface_id=surface_id,
                user_id=uid,
                content_snapshot={
                    "copy": (
                        f"Suggested window is {suggested_minutes} min "
                        f"for {category} / {tod} from a {round(magnitude, 3)}x "
                        f"Rule-13 factor."
                    ),
                    "category": category,
                    "time_of_day": tod,
                    "planned_minutes": planned_minutes,
                    "suggested_minutes": suggested_minutes,
                    "bias_factor": round(magnitude, 3),
                    "personal_bias_factor": cell.get("bias_factor"),
                    "personal_weight": result.get("personal_weight"),
                    "prior_weight": result.get("prior_weight"),
                    "archetype_prior_for_cell": result.get("archetype_prior_for_cell"),
                    "archetype_prior_citation": result.get("archetype_prior_citation"),
                    "sample_size": cell.get("sessions"),
                    "source": result.get("source"),
                },
                eligible_at=eligible_at,
                rendered_at=eligible_at,
                content_template_id="task_creation_nudge_lookup",
                initiative="system",
                trigger_source="analytics.bias_factor.lookup",
                randomization_arm=arm,
                randomization_policy_version=policy,
            )
            db.commit()
            result.update(
                {
                    "surface_id": emitted["surface_id"],
                    "truth_class": emitted["truth_class"],
                    "signal_targets": emitted["signal_targets"],
                    "clean_profile": emitted["clean_profile"],
                    "fallback_mode": emitted["fallback_mode"],
                    "exposure_id": emitted["exposure_id"],
                    "render_id": emitted["render_id"],
                }
            )
        except Exception:
            db.rollback()
            return {
                "cell": None,
                "sessions": result.get("sessions", 0),
                "min_sessions": result.get("min_sessions", 3),
                "source": result.get("source"),
                "suppressed_reason": "exposure_emit_failed",
                "surface_id": "task.creation_nudge",
                "truth_class": "intervention",
                "signal_targets": ["planning_estimate"],
                "clean_profile": "planning_calibration",
                "fallback_mode": "suppress",
            }
    return result


@router.get("/analytics/pause_prediction")
def get_pause_prediction(db: Session = Depends(get_db)) -> dict:
    """VT-17 pause-prediction dashboard (scoped to the requesting user).

    Reports firing volume, acceptance_rate, and per-mechanism breakdown
    over the user's full pause_prediction_log history. Unreconciled
    rows (user_response IS NULL) are reported separately — they are
    neither counted in acceptance_rate numerator nor denominator.

    Acceptance-rate formula (MANIFESTO §VT-17, pre-registered, frozen at
    launch):

        acceptance_rate = acceptance_count / total_fires

    where total_fires EXCLUDES re-fires from snooze chains
    (parent_firing_id IS NOT NULL). VT-17 kill criterion is per-user —
    this endpoint IS that per-user view (auto-scoped by X-User-Id).
    Operator cross-user analysis runs in the Commit 5c notebook via
    direct DB reads, bypassing the scoping hook.

    Response shape is flat + nested dicts so the notebook can read it
    without field-name gymnastics; any change to shape is a breaking
    change because cells VT-17a/b/c read specific keys.
    """
    all_rows = db.query(PausePredictionLog).all()

    # Snooze re-fires are excluded from denominator per pre-registration.
    primary = [r for r in all_rows if r.parent_firing_id is None]
    reconciled = [r for r in primary if r.user_response is not None]
    unreconciled = [r for r in primary if r.user_response is None]
    accepted = [r for r in reconciled if r.user_response == "pause_now"]
    no_response = [r for r in reconciled if r.user_response == "no_response"]
    dismissed = [r for r in reconciled if r.user_response == "dismiss"]

    def _rate(num: list, denom: list) -> float:
        return round(len(num) / len(denom), 3) if denom else 0.0

    summary = {
        "total_fires": len(primary),
        "total_reconciled": len(reconciled),
        "total_unreconciled": len(unreconciled),
        "accepted": len(accepted),
        "no_response": len(no_response),
        "dismissed": len(dismissed),
        # Denominator is reconciled-only so an open window doesn't drag
        # the rate toward zero. Kill criterion is pre-registered against
        # this number (MANIFESTO §VT-17).
        "acceptance_rate": _rate(accepted, reconciled),
        "snooze_refires_excluded": len(all_rows) - len(primary),
    }

    by_mechanism = []
    for mechanism in ("clock_anchor", "work_rhythm"):
        mech_rows = [r for r in primary if r.mechanism == mechanism]
        mech_reconciled = [r for r in mech_rows if r.user_response is not None]
        mech_accepted = [r for r in mech_reconciled if r.user_response == "pause_now"]
        by_mechanism.append({
            "mechanism": mechanism,
            "fires": len(mech_rows),
            "reconciled": len(mech_reconciled),
            "accepted": len(mech_accepted),
            "acceptance_rate": _rate(mech_accepted, mech_reconciled),
        })

    return {
        "summary": summary,
        "by_mechanism": by_mechanism,
        "primary_metric": "acceptance_rate (MANIFESTO §VT-17, pre-registered)",
    }


@router.get("/analytics/deadline-shape")
def get_deadline_shape(
    db: Session = Depends(get_db),
    include_external: bool = False,
) -> dict:
    """Loop 11 — per-user deadline-met distribution (MANIFESTO Rules 14, 15).

    Pre-registered at MANIFESTO v1.12 (2026-04-26). Reads
    `task_deadline_outcome` rows (written by Phase H reconciliation job)
    and stratifies along the dimensions specified in Rules 14 + 15:

    - Rule 14: Spearman ρ between `delay_minutes` and signed
      `duration_delta_minutes` is computed downstream by the operator
      notebook from the per-task rows we expose here. Stratification
      by `deadline_match_source` is included.

    - Rule 15: per-deadline `bias_factor_observed = mean(signed delta)
      / mean(planned_minutes)` requires per-deadline aggregation; we
      surface the per-deadline summary so the notebook can compute σ
      across deadlines per user.

    Voided_at discipline (per `feedback_voided_at_guard` memory):
    every query in this endpoint filters voided rows from BOTH
    `task_deadline_outcome.voided_at IS NULL` AND the underlying
    `task` and `deadline` rows.

    External-source filter (MANIFESTO VT-29, alembic 041, 2026-04-29):
    by default, deadlines imported from third-party sources (Moodle
    iCal, future LMS integrations) are EXCLUDED — H2 is a hypothesis
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
          "mean_delay_minutes": float,           # signed: + miss, − met
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

    # Per-task outcome rows + joined task fields. voided_at filtered
    # on all three tables (outcome, task, deadline) per the discipline.
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
        )
    )
    if uid is not None:
        rows = rows.filter(TaskDeadlineOutcome.user_id == uid)
    # VT-29 default: native-only. Toggle with ?include_external=true to
    # run the contamination test.
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
            "primary_metric": "delay_minutes_distribution (MANIFESTO Rule 14, pre-registered)",
            "note": "no deadline-bound EXECUTED tasks reconciled for this user yet",
        }

    met = [r for r in results if r[0].deadline_met]
    delays = sorted([r[0].delay_minutes for r in results])

    def _mean(xs):
        return round(sum(xs) / len(xs), 2) if xs else None

    def _median(xs):
        if not xs:
            return None
        n = len(xs)
        return xs[n // 2] if n % 2 == 1 else int((xs[n // 2 - 1] + xs[n // 2]) / 2)

    def _rate(num: int, denom: int) -> float:
        return round(num / denom, 3) if denom else 0.0

    summary = {
        "total_outcomes": total,
        "deadline_met_count": len(met),
        "deadline_missed_count": total - len(met),
        "deadline_met_rate": _rate(len(met), total),
        "mean_delay_minutes": _mean(delays),
        "median_delay_minutes": _median(delays),
    }

    # Stratify by deadline_match_source (Rule 14 stratification).
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

    # Stratify by scope_bullet_count_at_plan (Rule 12 amendment).
    def _band(count):
        if count is None:
            return "0"  # null treated as zero-bullets for stratification
        if count == 0:
            return "0"
        if count <= 3:
            return "1-3"
        if count <= 6:
            return "4-6"
        return "7+"

    by_band: dict[str, list] = defaultdict(list)
    for outcome, task, _ in results:
        by_band[_band(task.scope_bullet_count_at_plan)].append(outcome)

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

    # Per-deadline aggregation (Rule 15 inputs).
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
        planned_minutes = [t.planned_duration_minutes for t in group_tasks if t.planned_duration_minutes]
        # bias_factor_observed: mean(signed delta) / mean(planned_minutes).
        # Note sign: in Lyra duration_delta = planned - executed, so negative
        # means overran. bias_factor in canonical form is executed/planned;
        # for Rule 15 we report the signed-delta-based ratio per the spec.
        bias_factor_observed = (
            round(_mean(deltas) / _mean(planned_minutes), 3)
            if deltas and planned_minutes and _mean(planned_minutes)
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
        "primary_metric": "delay_minutes_distribution (MANIFESTO Rule 14, pre-registered)",
    }


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
    rows = (
        db.query(DeadlineCompletionEvent, Deadline)
        .join(Deadline, Deadline.deadline_id == DeadlineCompletionEvent.deadline_id)
        .filter(
            DeadlineCompletionEvent.voided_at.is_(None),
            Deadline.voided_at.is_(None),
        )
    )
    if uid is not None:
        rows = rows.filter(DeadlineCompletionEvent.user_id == uid)
    if not include_external:
        rows = rows.filter(Deadline.external_source.is_(None))
    results = rows.all()

    if not results:
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
            "primary_metric": "deadline_completion_delay_distribution",
            "note": "no deadline completion events for this user yet",
        }

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

    def _event_sort_key(pair):
        event, _deadline = pair
        return (
            strip_tz(event.completed_at_utc),
            strip_tz(event.recorded_at_utc),
            event.event_id,
        )

    total = len(results)
    late_events = [event for event, _ in results if event.completed_after_due]
    delays = [event.delay_minutes for event, _ in results]

    earliest_by_deadline = {}
    events_by_deadline: dict[str, list] = defaultdict(list)
    for pair in sorted(results, key=_event_sort_key):
        event, deadline = pair
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
        "primary_metric": "deadline_completion_delay_distribution",
    }


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
            emitted = emit_surface_render(
                db,
                surface_id=surface_id,
                user_id=uid,
                content_snapshot=json.dumps(response_payload, sort_keys=True, default=str),
                content_template_id="analytics_archetype_proximity",
                trigger_source="analytics.archetype_proximity",
            )
            response_payload["exposure_id"] = emitted["exposure_id"]
            response_payload["render_id"] = emitted["render_id"]
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
    prior_window_days}. Powers the frontend "a month ago you were 65/70 —
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
    """Loop 1 — calibration nudge effectiveness (per feedback_loops_closure_plan.md §Loop 1).

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
    from datetime import datetime, timedelta
    from app.db.models import CalibrationNudgeEvent

    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(CalibrationNudgeEvent)
        .filter(
            CalibrationNudgeEvent.user_id == uid,
            CalibrationNudgeEvent.voided_at.is_(None),
            CalibrationNudgeEvent.decided_at >= cutoff,
        )
        .all()
    )

    accepted = [r for r in rows if r.user_decision == "accepted"]
    dismissed = [r for r in rows if r.user_decision == "dismissed"]
    resolved = [r for r in rows if r.executed_duration_minutes is not None]
    unresolved = [r for r in rows if r.executed_duration_minutes is None]

    def _mean_delta(events: list) -> Optional[float]:
        """Mean (user_planned − executed_duration) for events with outcome."""
        deltas = [
            e.user_planned_duration_minutes - e.executed_duration_minutes
            for e in events
            if e.executed_duration_minutes is not None
        ]
        return round(sum(deltas) / len(deltas), 2) if deltas else None

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
            "acceptance_rate": (
                round(len(accepted) / total, 3) if total else 0.0
            ),
        },
        "delta_by_decision": {
            "accepted_mean_delta_minutes": accepted_delta,
            "accepted_resolved_n": sum(
                1 for e in accepted if e.executed_duration_minutes is not None
            ),
            "dismissed_mean_delta_minutes": dismissed_delta,
            "dismissed_resolved_n": sum(
                1 for e in dismissed if e.executed_duration_minutes is not None
            ),
            "delta_difference_accepted_minus_dismissed": delta_difference,
        },
        "lookback_days": days,
        "primary_metric": "delta_difference_accepted_minus_dismissed (Loop 1, pre-registered)",
    }
