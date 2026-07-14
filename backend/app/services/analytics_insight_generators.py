"""Pure insight generator catalog for /analytics/insights.

This module must remain computation-only. Exposure rendering, suppression,
Rule 11 gating, Redis seen-state, and HTTP response assembly stay in the
analytics endpoint until their writer authority is explicitly extracted.
"""

from collections import defaultdict
from typing import Optional

from app.db.models import Archetype, TaskState
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
from app.services.bias_factor_service import RESEARCH_PRIOR_DEFAULT, RESEARCH_PRIORS
from app.services.interruption_metrics import task_interruption_metrics_from_sessions
from app.utils.time_utils import to_local
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


def _insight_readiness_time_of_day(tasks: list) -> Optional[dict]:
    """Self-reported readiness as context for time-window planning fit.

    This deliberately avoids "best brain time" or cognitive-capacity copy.
    The user reported readiness; LyraOS observed planning error by time window.
    The output is a low-authority placement/recovery hypothesis only.
    """
    buckets: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for t in tasks:
        if t.state != TaskState.EXECUTED:
            continue
        if t.pre_task_readiness is None or t.duration_delta_minutes is None:
            continue
        tod = _time_of_day(to_local(t.planned_start_utc))
        buckets[tod].append((int(t.pre_task_readiness), abs(int(t.duration_delta_minutes))))

    summaries = []
    for tod, pairs in buckets.items():
        if len(pairs) < 3:
            continue
        readiness_vals = [readiness for readiness, _error in pairs]
        error_vals = [error for _readiness, error in pairs]
        summaries.append(
            {
                "time_of_day": tod,
                "sessions": len(pairs),
                "avg_readiness": _avg(readiness_vals),
                "avg_abs_error": _avg(error_vals),
            }
        )

    if len(summaries) < 2:
        return None

    best = min(summaries, key=lambda row: row["avg_abs_error"])
    comparison = max(summaries, key=lambda row: row["avg_abs_error"])
    diff = comparison["avg_abs_error"] - best["avg_abs_error"]
    if diff < 8:
        return None

    obs = (
        f"In rated sessions, {best['time_of_day']} starts landed "
        f"{_abs_minutes(diff)} min closer to plan than {comparison['time_of_day']}. "
        f"Self-reported readiness averaged {best['avg_readiness']:.1f}/5 in that window. "
        "This is a planning-context signal, not an ability or identity claim."
    )
    return _insight(
        "readiness_time_of_day",
        obs,
        sum(row["sessions"] for row in summaries),
        strength=diff,
        facts={
            "best_time_of_day": best["time_of_day"],
            "comparison_time_of_day": comparison["time_of_day"],
            "best_average_readiness": best["avg_readiness"],
            "best_average_absolute_error_minutes": best["avg_abs_error"],
            "comparison_average_absolute_error_minutes": comparison["avg_abs_error"],
        },
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


def _insight_occupancy_footprint(tasks: list) -> Optional[dict]:
    """Planning-window footprint from active work plus bounded pause overhead."""
    rows = []
    for task in tasks:
        if task.state != TaskState.EXECUTED:
            continue
        if getattr(task, "is_anchor", False):
            continue
        sessions = list(getattr(task, "stopwatch_sessions", []) or [])
        metrics = task_interruption_metrics_from_sessions(task, sessions)
        if (
            metrics.execution_time_minutes is None
            or metrics.session_span_minutes is None
            or metrics.execution_efficiency is None
        ):
            continue
        rows.append(metrics)

    if len(rows) < 5:
        return None

    pause_values = [row.pause_overhead_minutes for row in rows]
    execution_values = [row.execution_time_minutes for row in rows if row.execution_time_minutes is not None]
    span_values = [row.session_span_minutes for row in rows if row.session_span_minutes is not None]
    median_pause = _median(pause_values)
    if median_pause < 15:
        return None

    median_execution = _median(execution_values)
    median_span = _median(span_values)
    obs = (
        f"Across {len(rows)} completed sessions with clean timer data, "
        f"median active work was {_abs_minutes(median_execution)} min, "
        f"median session span was {_abs_minutes(median_span)} min, "
        f"and median pause overhead was {_abs_minutes(median_pause)} min. "
        "Treat occupancy as planning-window guidance, not execution time."
    )
    return _insight(
        "occupancy_footprint",
        obs,
        len(rows),
        strength=median_pause,
        facts={
            "median_execution_minutes": median_execution,
            "median_session_span_minutes": median_span,
            "median_pause_overhead_minutes": median_pause,
        },
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
    ("analytics.insights.readiness_time_of_day", _insight_readiness_time_of_day),
    ("analytics.insights.abandonment_pattern", _insight_abandonment),
    ("analytics.insights.best_category", _insight_best_category),
    ("analytics.insights.worst_category", _insight_worst_category),
    ("analytics.insights.discrepancy_signal", _insight_discrepancy_signal),
    ("analytics.insights.pause_pattern", _insight_pause_pattern),
    ("analytics.insights.occupancy_footprint", _insight_occupancy_footprint),
    ("analytics.insights.morning_anchor_cascade", _insight_morning_anchor),
]


PROFILE_AWARE_INSIGHT_GENERATORS = [
    ("analytics.insights.archetype_divergence", _insight_archetype_divergence),
    ("analytics.insights.calibration_maturation", _insight_calibration_maturation),
]


LEGACY_SUPPRESSED_INSIGHT_SURFACES = []



