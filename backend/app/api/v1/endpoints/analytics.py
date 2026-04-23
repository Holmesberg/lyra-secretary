"""Analytics endpoints — discrepancy experiment measurement layer."""
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from collections import defaultdict

from app.api.deps import get_db
from app.db.models import Archetype, ArchetypeAssignment, Task, TaskState, StopwatchSession, PausePredictionLog, User
from app.db.scoping import get_current_user_id
from app.utils.time_utils import to_local, now_utc
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
async def get_discrepancy(db: Session = Depends(get_db)) -> dict:
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
    voided_count = db.query(Task).filter(Task.initiation_status == "system_error").count()
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


def _insight(id: str, observation: str, data_points: int, strength: float = 0.0) -> dict:
    return {
        "id": id,
        "observation": observation,
        "data_points": data_points,
        "confidence": _confidence(data_points),
        "strength": round(strength, 3),
    }


def _median(vals: list[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


# ---------------------------------------------------------------------------
# Individual insight generators — each returns a dict or None
# ---------------------------------------------------------------------------

def _insight_time_of_day(tasks: list) -> Optional[dict]:
    """Time-of-day bias in delta_minutes. Picks the TOD with max |avg delta|."""
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
        obs = f"You consistently finish {tod} tasks {round(avg)} min early — you may be overplanning them."
    else:
        obs = f"Your {tod} tasks run an average of {round(abs(avg))} min over plan."
    return _insight("time_of_day_bias", obs, n, strength=abs(avg))


def _insight_readiness(tasks: list) -> Optional[dict]:
    """Pre-task readiness vs delta — median split, always emits when computable."""
    pairs = [
        (t.pre_task_readiness, t.duration_delta_minutes)
        for t in tasks
        if t.pre_task_readiness is not None and t.duration_delta_minutes is not None
    ]
    if len(pairs) < 6:
        return None

    med = _median([p[0] for p in pairs])
    low = [d for r, d in pairs if r < med]
    high = [d for r, d in pairs if r > med]
    if len(low) < 3 or len(high) < 3:
        return None

    avg_low = _avg(low)
    avg_high = _avg(high)
    diff = avg_low - avg_high  # positive = low-readiness sessions overrun more (delta smaller)
    n = len(low) + len(high)

    if abs(diff) < 5:
        return _insight(
            "readiness_predicts_outcome",
            "Your readiness rating doesn't track execution time — your starting state isn't predicting outcomes.",
            n,
            strength=abs(diff),
        )
    if diff > 0:
        return _insight(
            "readiness_predicts_outcome",
            f"When you start sharp, you finish {round(abs(diff))} min closer to plan than when drained.",
            n,
            strength=abs(diff),
        )
    return _insight(
        "readiness_predicts_outcome",
        f"When you start drained, you actually finish {round(abs(diff))} min closer to plan — your low-readiness sessions outperform your sharp ones.",
        n,
        strength=abs(diff),
    )


def _insight_abandonment(tasks: list) -> Optional[dict]:
    """Abandonment rate by TOD and category. Threshold 20%."""
    tod_total: dict[str, int] = defaultdict(int)
    tod_ab: dict[str, int] = defaultdict(int)
    cat_total: dict[str, int] = defaultdict(int)
    cat_ab: dict[str, int] = defaultdict(int)

    for t in tasks:
        tod = _time_of_day(to_local(t.planned_start_utc))
        tod_total[tod] += 1
        if t.initiation_status == "abandoned":
            tod_ab[tod] += 1
        if t.category:
            cat_total[t.category] += 1
            if t.initiation_status == "abandoned":
                cat_ab[t.category] += 1

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
    pct = round(rate * 100)
    obs = (
        f"You abandon {pct}% of your {label} tasks before starting them."
        if kind == "tod"
        else f"Your {label} tasks are your most abandoned — {pct}% never start."
    )
    return _insight("abandonment_pattern", obs, n, strength=rate * 100)


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
    return _insight("estimation_accuracy_trend", obs, 10, strength=abs(improvement))


def _insight_best_category(tasks: list) -> Optional[dict]:
    """Most predictable task category."""
    cat_errors: dict[str, list[int]] = defaultdict(list)
    for t in tasks:
        if t.state == TaskState.EXECUTED and t.duration_delta_minutes is not None and t.category:
            cat_errors[t.category].append(abs(t.duration_delta_minutes))

    best_cat, best_avg, best_n = None, float("inf"), 0
    for cat, errors in cat_errors.items():
        if len(errors) < 3:
            continue
        avg = _avg(errors)
        if avg < best_avg:
            best_cat, best_avg, best_n = cat, avg, len(errors)

    if best_cat is None:
        return None
    return _insight(
        "best_category",
        f"Your {best_cat} tasks are your most predictable — avg {round(best_avg)} min from plan.",
        best_n,
        strength=max(0.0, 60.0 - best_avg),  # closer to plan = stronger insight
    )


def _insight_worst_category(tasks: list) -> Optional[dict]:
    """Least predictable task category — the bucket pulling estimation accuracy down."""
    cat_errors: dict[str, list[int]] = defaultdict(list)
    for t in tasks:
        if t.state == TaskState.EXECUTED and t.duration_delta_minutes is not None and t.category:
            cat_errors[t.category].append(abs(t.duration_delta_minutes))

    worst_cat, worst_avg, worst_n = None, 0.0, 0
    for cat, errors in cat_errors.items():
        if len(errors) < 3:
            continue
        avg = _avg(errors)
        if avg > worst_avg:
            worst_cat, worst_avg, worst_n = cat, avg, len(errors)

    if worst_cat is None or worst_avg < 20:
        return None
    return _insight(
        "worst_category",
        f"Your {worst_cat} tasks are your least predictable — avg {round(worst_avg)} min from plan.",
        worst_n,
        strength=worst_avg,
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
        obs = f"On sessions where your cognitive state shifted most, your execution error was {pct}% higher."
    else:
        obs = f"On sessions where your cognitive state shifted most, your execution error was actually {abs(pct)}% lower — interesting."
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
        f"You pause on {pct}% of your sessions — averaging {avg_pauses} interruptions when you do.",
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
        f"When you skip your first morning task, {pct}% of the rest of that day collapses with it.",
        days_with_morning,
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
        obs = f"On average you start tasks {round(abs(avg))} min before their scheduled time — your plan is lagging behind your reality."
    return _insight("initiation_delay", obs, len(delays), strength=abs(avg))


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
        if (
            t.state != TaskState.EXECUTED
            or t.executed_duration_minutes is None
            or not t.planned_duration_minutes
            or t.category is None
            or t.category == "uncategorized"
        ):
            continue
        cat_ratios[t.category].append(
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
        f"On {best_cat} tasks you're running {_fmt(personal_pct)} — "
        f"{direction} your archetype's prior ({_fmt(prior_pct)}). "
        f"Your personal data is pulling the blended prediction away "
        f"from the cohort average."
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
        if (
            t.state != TaskState.EXECUTED
            or t.executed_duration_minutes is None
            or not t.planned_duration_minutes
            or t.category is None
            or t.category == "uncategorized"
        ):
            continue
        tod = _time_of_day(to_local(t.planned_start_utc))
        cell_counts[(t.category, tod)] += 1

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
        f"Your personal data now accounts for {weight_pct}% of the "
        f"prediction on {top_cat}/{top_tod} tasks ({top_n} sessions). "
        f"The blend is shifting from your archetype's prior to your "
        f"actual behavior — predictions are becoming yours, not the "
        f"reference cohort's."
    )
    return _insight(
        "calibration_maturation",
        obs,
        top_n,
        strength=weight_pct,
    )


# ---------------------------------------------------------------------------
# Insights endpoint
# ---------------------------------------------------------------------------

@router.get("/analytics/insights")
async def get_insights(
    auto_mark: bool = Query(False, description="Mark returned unseen insights as seen in Redis (24h TTL)"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Generate up to 5 plain-language behavioral observations from task history,
    sorted by strength (largest signal first).

    Rule-based only — no ML. Requires >= 3 completed sessions with delta data.
    Pass ?auto_mark=true to suppress already-shown insights (24h cooldown per insight_id).
    """
    MIN_SESSIONS = 3

    all_tasks = (
        db.query(Task)
        .filter(Task.initiation_status != "system_error", Task.voided_at.is_(None))
        .order_by(Task.planned_start_utc)
        .all()
    )

    # Gate check: need at least MIN_SESSIONS executed tasks with delta data
    delta_sessions = [
        t for t in all_tasks
        if t.state == TaskState.EXECUTED and t.duration_delta_minutes is not None
    ]
    sessions_analyzed = len(delta_sessions)

    if sessions_analyzed < MIN_SESSIONS:
        remaining = MIN_SESSIONS - sessions_analyzed
        return {
            "insights": [],
            "sessions_analyzed": sessions_analyzed,
            "min_sessions_required": MIN_SESSIONS,
            "ready": False,
            "message": f"Log {remaining} more session{'s' if remaining != 1 else ''} to unlock your first behavioral insights.",
        }

    # Resolve archetype for archetype-aware generators. Falls back to
    # Diffuse Average when user has no assignment (per Rule 13 skip-path).
    uid = get_current_user_id()
    archetype: Optional[Archetype] = None
    if uid is not None:
        user = db.query(User).filter(User.user_id == uid).first()
        archetype_id = (user.archetype_id if user else None) or "diffuse_average"
        archetype = (
            db.query(Archetype)
            .filter(Archetype.archetype_id == archetype_id)
            .first()
        )

    # Run all insight generators, collect results. Archetype-aware
    # generators take the Archetype row as a second arg; regular ones
    # just take tasks.
    base_generators = [
        _insight_time_of_day,
        _insight_readiness,
        _insight_abandonment,
        _insight_estimation_trend,
        _insight_best_category,
        _insight_worst_category,
        _insight_discrepancy_signal,
        _insight_pause_pattern,
        _insight_morning_anchor,
        _insight_retroactive_rate,
        _insight_initiation_delay,
    ]
    archetype_generators = [
        _insight_archetype_divergence,
        _insight_calibration_maturation,
    ]

    redis = RedisClient()
    candidates = []
    for gen in base_generators:
        result = gen(all_tasks)
        if result is not None:
            candidates.append(result)
    for gen in archetype_generators:
        result = gen(all_tasks, archetype)
        if result is not None:
            candidates.append(result)

    # Sort by strength (largest signal first), then by data_points
    candidates.sort(key=lambda r: (r.get("strength", 0.0), r.get("data_points", 0)), reverse=True)

    insights = []
    for result in candidates:
        insight_id = result["id"]
        redis_key = f"insight_shown:{insight_id}"
        result["seen"] = bool(redis.client.exists(redis_key))
        if auto_mark and result["seen"]:
            continue
        if auto_mark:
            redis.client.setex(redis_key, 86400, "1")
            result["seen"] = True
        insights.append(result)

    return {
        "insights": insights,
        "sessions_analyzed": sessions_analyzed,
        "min_sessions_required": MIN_SESSIONS,
        "ready": True,
    }


# ---------------------------------------------------------------------------
# Cascade Analytics
# ---------------------------------------------------------------------------

@router.get("/analytics/cascade")
async def get_cascade(
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
async def get_bias_factor(
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
    """
    tasks = (
        db.query(Task)
        .filter(
            Task.state == TaskState.EXECUTED,
            Task.initiation_status != "system_error",
            Task.voided_at.is_(None),
            Task.initiation_status != "retroactive",
            Task.executed_duration_minutes != None,
            Task.planned_duration_minutes > 0,
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
async def bias_factor_lookup(
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
    tasks = (
        db.query(Task)
        .filter(
            Task.state == TaskState.EXECUTED,
            Task.initiation_status != "system_error",
            Task.voided_at.is_(None),
            Task.initiation_status != "retroactive",
            Task.executed_duration_minutes != None,
            Task.planned_duration_minutes >= 5,
        )
        .all()
    )
    # If scoping is absent (admin or test path), fall through to the
    # legacy personal-only cascade — blend() requires a user_id to look
    # up the archetype. This should not happen under normal auth flow.
    if uid is None:
        return _adaptive_calibration(tasks, category, tod, planned_minutes)
    from app.services.bias_factor_service import blend
    return blend(db, uid, tasks, category, tod, planned_minutes)


@router.get("/analytics/pause_prediction")
async def get_pause_prediction(db: Session = Depends(get_db)) -> dict:
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
