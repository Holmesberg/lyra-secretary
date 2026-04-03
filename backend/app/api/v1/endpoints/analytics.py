"""Analytics endpoints — discrepancy experiment measurement layer."""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from collections import defaultdict

from app.api.deps import get_db
from app.db.models import Task, TaskState, StopwatchSession
from app.utils.time_utils import to_local
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
    """
    tasks = (
        db.query(Task)
        .filter(
            (Task.state == TaskState.EXECUTED) |
            (Task.initiation_status.in_(["initiated", "abandoned"]))
        )
        .order_by(Task.planned_start_utc)
        .all()
    )

    # Build local-date → task_id list for session index calculation
    day_index: dict[date, list[str]] = {}
    for t in tasks:
        local_start = to_local(t.planned_start_utc)
        d = local_start.date()
        day_index.setdefault(d, []).append(t.task_id)

    research_sessions = []
    product_sessions = []

    for t in tasks:
        local_start = to_local(t.planned_start_utc)
        d = local_start.date()
        day_tasks = day_index.get(d, [])
        session_idx = day_tasks.index(t.task_id) if t.task_id in day_tasks else 0

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

        research_sessions.append({
            **common,
            "planned_duration_minutes": t.planned_duration_minutes,
            "executed_duration_minutes": t.executed_duration_minutes,
            "delta_minutes": t.duration_delta_minutes,
            "initiation_status": t.initiation_status,
            "initiation_delay_minutes": t.initiation_delay_minutes,
            "pause_count": t.pause_count,
            "total_paused_minutes": total_paused,
        })

        product_sessions.append({
            **common,
            "pre_task_readiness": t.pre_task_readiness,
            "post_task_reflection": t.post_task_reflection,
            "discrepancy_score": t.discrepancy_score,      # abs(pre - post): magnitude
            "signed_discrepancy": t.signed_discrepancy,    # post - pre: direction
        })

    # --- Research layer summary ---
    total = len(research_sessions)
    initiated = [s for s in research_sessions if s["initiation_status"] == "initiated"]
    abandoned = [s for s in research_sessions if s["initiation_status"] == "abandoned"]
    delta_vals = [s["delta_minutes"] for s in research_sessions if s["delta_minutes"] is not None]
    delay_vals = [s["initiation_delay_minutes"] for s in research_sessions if s["initiation_delay_minutes"] is not None]

    research_summary = {
        "total_sessions": total,
        "initiated_count": len(initiated),
        "abandoned_count": len(abandoned),
        "abandoned_rate": round(len(abandoned) / total, 3) if total else 0.0,
        "avg_delta_minutes": _avg(delta_vals),
        "avg_initiation_delay_minutes": _avg(delay_vals),
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


def _insight(id: str, observation: str, data_points: int) -> dict:
    return {
        "id": id,
        "observation": observation,
        "data_points": data_points,
        "confidence": _confidence(data_points),
    }


# ---------------------------------------------------------------------------
# Individual insight generators — each returns a dict or None
# ---------------------------------------------------------------------------

def _insight_time_of_day(tasks: list) -> Optional[dict]:
    """Insight 1: time-of-day bias in delta_minutes."""
    buckets: dict[str, list[int]] = defaultdict(list)
    for t in tasks:
        if t.state == TaskState.EXECUTED and t.duration_delta_minutes is not None:
            tod = _time_of_day(to_local(t.planned_start_utc))
            buckets[tod].append(t.duration_delta_minutes)

    best_over, best_under = None, None
    for tod, deltas in buckets.items():
        if len(deltas) < 3:
            continue
        avg = _avg(deltas)
        n = len(deltas)
        if avg > 15:
            if best_over is None or avg > best_over[1]:
                best_over = (tod, avg, n)
        if avg < -10:
            if best_under is None or avg < best_under[1]:
                best_under = (tod, avg, n)

    if best_over:
        tod, avg, n = best_over
        return _insight(
            "time_of_day_bias",
            f"Your {tod} tasks run an average of {round(avg)} minutes over plan.",
            n,
        )
    if best_under:
        tod, avg, n = best_under
        return _insight(
            "time_of_day_bias",
            f"You consistently finish {tod} tasks early — you may be underplanning them.",
            n,
        )
    return None


def _insight_readiness(tasks: list) -> Optional[dict]:
    """Insight 2: pre-task readiness predicts delta outcome."""
    low, high = [], []
    for t in tasks:
        if t.pre_task_readiness is None or t.duration_delta_minutes is None:
            continue
        if t.pre_task_readiness <= 2:
            low.append(t.duration_delta_minutes)
        elif t.pre_task_readiness >= 4:
            high.append(t.duration_delta_minutes)

    if len(low) < 3 or len(high) < 3:
        return None

    avg_low = _avg(low)
    avg_high = _avg(high)
    diff = avg_low - avg_high  # positive = low readiness runs longer over plan
    n = len(low) + len(high)

    if diff > 15:
        return _insight(
            "readiness_predicts_outcome",
            f"When you start sharp (4-5), you finish {round(diff)} min closer to plan than when drained (1-2).",
            n,
        )
    if abs(diff) < 5:
        return _insight(
            "readiness_predicts_outcome",
            "Your readiness rating doesn't seem to affect your execution time yet — interesting.",
            n,
        )
    return None


def _insight_abandonment(tasks: list) -> Optional[dict]:
    """Insight 3: abandonment rate by time-of-day and category."""
    tod_total: dict[str, int] = defaultdict(int)
    tod_abandoned: dict[str, int] = defaultdict(int)
    cat_total: dict[str, int] = defaultdict(int)
    cat_abandoned: dict[str, int] = defaultdict(int)

    for t in tasks:
        tod = _time_of_day(to_local(t.planned_start_utc))
        tod_total[tod] += 1
        if t.initiation_status == "abandoned":
            tod_abandoned[tod] += 1
        if t.category:
            cat_total[t.category] += 1
            if t.initiation_status == "abandoned":
                cat_abandoned[t.category] += 1

    # Check time-of-day abandonment
    for tod, total in tod_total.items():
        if total < 3:
            continue
        rate = tod_abandoned.get(tod, 0) / total
        if rate > 0.40:
            pct = round(rate * 100)
            return _insight(
                "abandonment_pattern",
                f"You abandon {pct}% of your {tod} tasks before starting them.",
                total,
            )

    # Check category abandonment
    worst_cat, worst_rate, worst_n = None, 0.0, 0
    for cat, total in cat_total.items():
        if total < 3:
            continue
        rate = cat_abandoned.get(cat, 0) / total
        if rate > worst_rate:
            worst_cat, worst_rate, worst_n = cat, rate, total

    if worst_cat and worst_rate > 0.40:
        return _insight(
            "abandonment_pattern",
            f"Your {worst_cat} tasks are your most abandoned.",
            worst_n,
        )
    return None


def _insight_estimation_trend(tasks: list) -> Optional[dict]:
    """Insight 4: estimation accuracy improving or worsening over last 10 sessions."""
    executed = sorted(
        [t for t in tasks if t.state == TaskState.EXECUTED and t.duration_delta_minutes is not None and t.executed_end_utc],
        key=lambda t: t.executed_end_utc,
        reverse=True,
    )
    if len(executed) < 10:
        return None

    recent = executed[:5]   # newest 5
    older = executed[5:10]  # next 5

    avg_recent = _avg([abs(t.duration_delta_minutes) for t in recent])
    avg_older = _avg([abs(t.duration_delta_minutes) for t in older])
    improvement = round(avg_older - avg_recent, 1)

    if improvement > 3:
        return _insight(
            "estimation_accuracy_trend",
            f"Your time estimates are getting more accurate — down {improvement} min average error over your last 10 sessions.",
            10,
        )
    if improvement < -3:
        return _insight(
            "estimation_accuracy_trend",
            "Your estimation error has increased over your last 10 sessions. You may be fatigued or rushing your planning.",
            10,
        )
    return None


def _insight_best_category(tasks: list) -> Optional[dict]:
    """Insight 5: most predictable task category."""
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

    if best_cat:
        return _insight(
            "best_category",
            f"Your {best_cat} tasks are your most predictable — avg {round(best_avg)} min from plan.",
            best_n,
        )
    return None


def _insight_discrepancy_signal(tasks: list) -> Optional[dict]:
    """Insight 6: link between cognitive shift and execution error."""
    high_disc, low_disc = [], []
    for t in tasks:
        if t.discrepancy_score is None or t.duration_delta_minutes is None:
            continue
        if t.discrepancy_score >= 3:
            high_disc.append(abs(t.duration_delta_minutes))
        else:
            low_disc.append(abs(t.duration_delta_minutes))

    if len(high_disc) < 3 or len(low_disc) < 3:
        return None

    avg_high = _avg(high_disc)
    avg_low = _avg(low_disc)
    n = len(high_disc) + len(low_disc)

    if avg_low > 0 and avg_high > avg_low * 1.2:
        pct = round((avg_high / avg_low - 1) * 100)
        return _insight(
            "discrepancy_signal",
            f"On sessions where your cognitive state shifted most, your execution error was {pct}% higher.",
            n,
        )
    return _insight(
        "discrepancy_signal",
        "No clear link between your readiness shift and execution error yet — keep logging.",
        n,
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
    Generate up to 3 plain-language behavioral observations from task history.

    Rule-based only — no ML. Requires >= 3 completed sessions with delta data.
    Pass ?auto_mark=true to suppress already-shown insights (24h cooldown per insight_id).
    """
    MIN_SESSIONS = 3

    all_tasks = db.query(Task).order_by(Task.planned_start_utc).all()

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

    # Run all insight generators, collect results
    generators = [
        _insight_time_of_day,
        _insight_readiness,
        _insight_abandonment,
        _insight_estimation_trend,
        _insight_best_category,
        _insight_discrepancy_signal,
    ]

    redis = RedisClient()
    insights = []

    for gen in generators:
        if len(insights) >= 3:
            break
        result = gen(all_tasks)
        if result is None:
            continue

        insight_id = result["id"]
        redis_key = f"insight_shown:{insight_id}"

        # Mark seen status from Redis
        result["seen"] = bool(redis.client.exists(redis_key))

        # If auto_mark: skip already-seen insights entirely
        if auto_mark and result["seen"]:
            continue

        # Mark as seen in Redis with 24h TTL
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
