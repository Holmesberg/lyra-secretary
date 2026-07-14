"""Operator behavioral signature aggregate implementation.

This read-only aggregate was extracted from the parked Jarvis tool island so
operator analytics can depend on a narrow service boundary without importing
the retired ``jarvis_tools`` module. It preserves the historical payload shape
for compatibility.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import (
    PauseEvent,
    PausePredictionLog,
    ReflectionViewLog,
    StopwatchSession,
    Task,
    TaskState,
)
from app.services.inference_engine import (
    classify_disagreement as _classify_disagreement,
    classify_task_valence as _classify_task_valence,
)
from app.utils.time_utils import now_utc


def _confidence_tier(n: int, low: int = 5, high: int = 30) -> str:
    """Default confidence tier per docs/calibration_contract.md R2.

    Per-signal overrides (R2.1) handled by callers passing custom thresholds.
    """
    if n < low:
        return "cold_start"
    if n < high:
        return "tentative"
    return "confirmed"


def _percentile(values: list[float], p: float) -> float | None:
    """Simple percentile (no scipy dependency). p in [0, 100]."""
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return round(s[0], 2)
    k = (len(s) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return round(s[lo] * (1 - frac) + s[hi] * frac, 2)


def _tod_bucket(dt: datetime) -> str:
    """Time-of-day bucket. UTC-only for now (matches get_pattern_summary)."""
    h = dt.hour
    if h < 6:
        return "night"
    if h < 12:
        return "morning"
    if h < 18:
        return "afternoon"
    return "evening"


def analyze_behavioral_signature_aggregate(db: Session, user_id: int, args: dict) -> dict:
    """Comprehensive behavioral fingerprint for operator-side pattern discovery.

    Joins task + stopwatch_session + pause_event + pause_prediction_log +
    reflection_view_log over a window. Returns aggregated structures JARVIS
    can reason over.

    Single SQL window pulls; in-Python aggregation. <500ms target on
    operator-scale data (~100 sessions, ~200 pause events per 30 days).

    voided_at_guard: applied at every filter level — voided rows never
    enter the aggregations.
    """
    window_days = max(1, min(int(args.get("window_days", 14)), 90))
    now = now_utc()
    window_start = now - timedelta(days=window_days)

    # ----- Tasks in window (executed only for productivity-substrate metrics)
    tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.voided_at.is_(None),
            Task.created_at >= window_start,
        )
        .all()
    )
    executed = [
        t for t in tasks
        if t.state == TaskState.EXECUTED
        and t.executed_duration_minutes is not None
    ]
    n_sessions = len(executed)

    # ----- Pause events in window (joined via session ownership)
    pause_events = (
        db.query(PauseEvent)
        .filter(
            PauseEvent.user_id == user_id,
            PauseEvent.paused_at_utc >= window_start,
        )
        .all()
    )
    n_pause_events = len(pause_events)

    # ----- Pause distribution: by reason × time-of-day × initiator
    pause_by_reason: dict[str, int] = {}
    pause_by_initiator: dict[str, int] = {}
    pause_by_tod_reason: dict[str, dict[str, int]] = {
        "morning": {}, "afternoon": {}, "evening": {}, "night": {},
    }
    for pe in pause_events:
        pause_by_reason[pe.pause_reason] = pause_by_reason.get(pe.pause_reason, 0) + 1
        pause_by_initiator[pe.pause_initiator] = pause_by_initiator.get(pe.pause_initiator, 0) + 1
        bucket = _tod_bucket(pe.paused_at_utc)
        pause_by_tod_reason[bucket][pe.pause_reason] = (
            pause_by_tod_reason[bucket].get(pe.pause_reason, 0) + 1
        )

    def _normalize(d: dict[str, int]) -> dict[str, float]:
        total = sum(d.values()) or 1
        return {k: round(v / total, 3) for k, v in d.items()}

    def _sorted_count_dict(d: dict[str, int]) -> dict[str, int]:
        return dict(sorted(d.items(), key=lambda kv: (-kv[1], kv[0])))

    def _task_time(t: Task) -> datetime:
        return t.executed_start_utc or t.planned_start_utc or t.created_at

    pause_distribution = {
        "by_reason_overall": _normalize(pause_by_reason),
        "by_reason_x_tod": {
            tod: _normalize(reasons) for tod, reasons in pause_by_tod_reason.items()
            if reasons
        },
        "by_initiator": _normalize(pause_by_initiator),
        "n_pause_events": n_pause_events,
    }

    # ----- Recovery latency by pause_reason (resumed_at - paused_at)
    recovery_by_reason: dict[str, dict] = {}
    latencies_by_reason: dict[str, list[float]] = {}
    for pe in pause_events:
        if pe.resumed_at_utc is None or pe.duration_minutes is None:
            continue
        latencies_by_reason.setdefault(pe.pause_reason, []).append(float(pe.duration_minutes))
    for reason, vals in latencies_by_reason.items():
        n = len(vals)
        recovery_by_reason[reason] = {
            "n": n,
            "p50_min": _percentile(vals, 50),
            "p75_min": _percentile(vals, 75),
            "confidence": _confidence_tier(n),
        }

    # ----- Hesitation chain: created_at vs planned_start_utc vs executed_start_utc
    creation_to_planned: list[float] = []
    planned_to_executed: list[float] = []
    for t in tasks:
        if t.planned_start_utc and t.created_at:
            delta = (t.planned_start_utc - t.created_at).total_seconds() / 60.0
            if delta >= 0:
                creation_to_planned.append(delta)
        if t.executed_start_utc and t.planned_start_utc:
            delta = (t.executed_start_utc - t.planned_start_utc).total_seconds() / 60.0
            planned_to_executed.append(delta)
    hesitation_chain = {
        "creation_to_planned_start_minutes": {
            "p50": _percentile(creation_to_planned, 50),
            "p75": _percentile(creation_to_planned, 75),
            "n": len(creation_to_planned),
            "confidence": _confidence_tier(len(creation_to_planned)),
        } if creation_to_planned else None,
        "planned_to_executed_start_minutes": {
            "p50": _percentile(planned_to_executed, 50),
            "p75": _percentile(planned_to_executed, 75),
            "n": len(planned_to_executed),
            "confidence": _confidence_tier(len(planned_to_executed)),
        } if planned_to_executed else None,
    }

    # ----- Schedule volatility: reschedule_count distribution
    rc_buckets = {"0": 0, "1": 0, "2": 0, "3+": 0}
    rc_values: list[int] = []
    for t in tasks:
        rc = t.reschedule_count or 0
        rc_values.append(rc)
        if rc == 0:
            rc_buckets["0"] += 1
        elif rc == 1:
            rc_buckets["1"] += 1
        elif rc == 2:
            rc_buckets["2"] += 1
        else:
            rc_buckets["3+"] += 1
    schedule_volatility = {
        "reschedule_count_distribution": rc_buckets,
        "median_reschedule_count": (
            _percentile([float(v) for v in rc_values], 50) if rc_values else None
        ),
        "max_reschedule_count": max(rc_values) if rc_values else 0,
        "n_tasks": len(tasks),
    }

    # ----- Context-switch graph (parent_task_id linkage + task_switch pauses)
    switch_edges: dict[tuple[str, str], int] = {}
    for t in tasks:
        if t.parent_task_id is None:
            continue
        parent = next((p for p in tasks if p.task_id == t.parent_task_id), None)
        if parent is None:
            continue
        from_cat = parent.category or "uncategorized"
        to_cat = t.category or "uncategorized"
        key = (from_cat, to_cat)
        switch_edges[key] = switch_edges.get(key, 0) + 1
    context_switch_graph = sorted(
        [
            {"from_category": k[0], "to_category": k[1], "count": v}
            for k, v in switch_edges.items()
        ],
        key=lambda d: -d["count"],
    )[:10]

    # ----- Snooze chains via parent_firing_id
    pause_predictions = (
        db.query(PausePredictionLog)
        .filter(
            PausePredictionLog.user_id == user_id,
            PausePredictionLog.fired_at >= window_start,
        )
        .all()
    )
    snooze_count = sum(1 for pp in pause_predictions if pp.parent_firing_id is not None)
    # Compute max chain depth by following parent_firing_id links.
    pp_by_id = {pp.firing_id: pp for pp in pause_predictions}
    max_depth = 0
    for pp in pause_predictions:
        depth = 0
        cur = pp
        while cur.parent_firing_id and cur.parent_firing_id in pp_by_id:
            depth += 1
            cur = pp_by_id[cur.parent_firing_id]
            if depth > 20:
                break  # cycle defense
        max_depth = max(max_depth, depth)
    snooze_chains = {
        "n_pause_predictions": len(pause_predictions),
        "n_snoozes": snooze_count,
        "max_chain_depth": max_depth,
        "by_mechanism": {},
    }
    for pp in pause_predictions:
        m = pp.mechanism
        bag = snooze_chains["by_mechanism"].setdefault(m, {"n": 0, "snoozes": 0})
        bag["n"] += 1
        if pp.parent_firing_id is not None:
            bag["snoozes"] += 1

    # ----- Reflection engagement: dwell + outcome per reflection_type
    reflections = (
        db.query(ReflectionViewLog)
        .filter(
            ReflectionViewLog.user_id == user_id,
            ReflectionViewLog.fired_at >= window_start,
            ReflectionViewLog.event_class == "impression",  # exclude telemetry
        )
        .all()
    )
    reflection_engagement: dict[str, dict] = {}
    for r in reflections:
        rt = r.reflection_type
        bag = reflection_engagement.setdefault(rt, {
            "n_fired": 0, "n_viewed": 0, "n_dismissed": 0,
            "dwell_seconds": [], "outcomes": {},
        })
        bag["n_fired"] += 1
        if r.viewed_at:
            bag["n_viewed"] += 1
        if r.dismissed_at:
            bag["n_dismissed"] += 1
        if r.dwell_seconds is not None:
            bag["dwell_seconds"].append(float(r.dwell_seconds))
        if r.outcome:
            bag["outcomes"][r.outcome] = bag["outcomes"].get(r.outcome, 0) + 1
    for rt, bag in reflection_engagement.items():
        dws = bag.pop("dwell_seconds")
        bag["p50_dwell_seconds"] = _percentile(dws, 50)
        bag["p75_dwell_seconds"] = _percentile(dws, 75)
        bag["confidence"] = _confidence_tier(bag["n_fired"])

    # ----- Valence classification per task (per docs/calibration_contract.md R9)
    valence_counts: dict[str, int] = {
        "friction": 0, "flow": 0, "scope_creep": 0, "under_plan": 0, "neutral": 0,
    }
    for t in executed:
        valence_counts[_classify_task_valence(t)] += 1
    valence_distribution = {
        "counts": valence_counts,
        "n_classified": sum(valence_counts.values()),
        "confidence": _confidence_tier(sum(valence_counts.values())),
        "interpretation": (
            "Per R9: 'friction'=overrun+low_focus+≥3pauses; 'flow'=overrun+"
            "high_focus+≤1pause (success state, NOT friction); 'scope_creep'="
            "overrun+medium_focus (route to VT-22 scope analysis); 'under_plan'="
            "underrun+high_focus; 'neutral'=within ±15% plan."
        ),
    }

    # Sessions are reused by several discovery cuts below. Keeping this as
    # aggregate-only output is what lets JARVIS answer harder questions without
    # leaking raw task rows into the model context.
    sessions = (
        db.query(StopwatchSession)
        .join(Task, Task.task_id == StopwatchSession.task_id)
        .filter(
            Task.user_id == user_id,
            Task.voided_at.is_(None),
            StopwatchSession.start_time_utc >= window_start,
        )
        .all()
    )
    sessions_by_id = {s.session_id: s for s in sessions}
    sessions_sorted = sorted(sessions, key=lambda s: s.start_time_utc)
    tasks_by_id = {t.task_id: t for t in tasks}

    pause_reasons_by_task: dict[str, dict[str, int]] = {}
    for pe in pause_events:
        pe_session = sessions_by_id.get(pe.session_id)
        if pe_session is None:
            continue
        bag = pause_reasons_by_task.setdefault(pe_session.task_id, {})
        bag[pe.pause_reason] = bag.get(pe.pause_reason, 0) + 1

    executed_sorted = sorted(executed, key=_task_time)
    valence_by_task_id = {t.task_id: _classify_task_valence(t) for t in executed}
    disagreement_by_task_id = {
        t.task_id: _classify_disagreement(t) for t in executed
    }

    # ----- Valence preconditions: category, time-of-day, prior task valence,
    # and readiness. This prevents the agent from inventing fingerprints from
    # a generic "valence is covered" label.
    valence_preconditions: dict[str, dict[str, Any]] = {}
    previous_valence: Optional[str] = None
    for t in executed_sorted:
        valence = valence_by_task_id[t.task_id]
        bag = valence_preconditions.setdefault(valence, {
            "n": 0,
            "by_category": {},
            "by_time_of_day": {},
            "by_prior_task_valence": {},
            "by_pre_task_readiness": {},
        })
        bag["n"] += 1
        cat = t.category or "uncategorized"
        tod = _tod_bucket(_task_time(t))
        readiness = (
            str(t.pre_task_readiness)
            if t.pre_task_readiness is not None
            else "missing"
        )
        bag["by_category"][cat] = bag["by_category"].get(cat, 0) + 1
        bag["by_time_of_day"][tod] = bag["by_time_of_day"].get(tod, 0) + 1
        if previous_valence is not None:
            prior = bag["by_prior_task_valence"]
            prior[previous_valence] = prior.get(previous_valence, 0) + 1
        bag["by_pre_task_readiness"][readiness] = (
            bag["by_pre_task_readiness"].get(readiness, 0) + 1
        )
        previous_valence = valence
    for bag in valence_preconditions.values():
        for key in (
            "by_category",
            "by_time_of_day",
            "by_prior_task_valence",
            "by_pre_task_readiness",
        ):
            bag[key] = _sorted_count_dict(bag[key])
        bag["confidence"] = _confidence_tier(bag["n"])

    # ----- Explicit-vs-implicit disagreement events
    disagreement_buckets: dict[str, list[dict]] = {
        "optimism_collapse": [],
        "capacity_surprise": [],
        "flow_overrun": [],
        "friction_completion": [],
    }
    for t in executed:
        kind = _classify_disagreement(t)
        if kind is None:
            continue
        pause_reasons = pause_reasons_by_task.get(t.task_id, {})
        disagreement_buckets[kind].append({
            "category": t.category or "uncategorized",
            "pre_readiness": t.pre_task_readiness,
            "post_reflection": t.post_task_reflection,
            "delta_min": (t.executed_duration_minutes or 0) - (t.planned_duration_minutes or 0),
            "pause_reasons": pause_reasons,
        })
    disagreement_events = {}
    for kind, items in disagreement_buckets.items():
        if not items:
            disagreement_events[kind] = {"n": 0}
            continue
        # Cross-tab by category to find which categories drive each disagreement.
        cat_counts: dict[str, int] = {}
        readiness_counts: dict[str, int] = {}
        category_x_pause_reason: dict[str, dict[str, int]] = {}
        for it in items:
            cat_counts[it["category"]] = cat_counts.get(it["category"], 0) + 1
            readiness_key = (
                str(it["pre_readiness"])
                if it["pre_readiness"] is not None
                else "missing"
            )
            readiness_counts[readiness_key] = readiness_counts.get(readiness_key, 0) + 1
            reason_counts = it["pause_reasons"] or {"no_pause_recorded": 1}
            for reason, count in reason_counts.items():
                cat_bag = category_x_pause_reason.setdefault(it["category"], {})
                cat_bag[reason] = cat_bag.get(reason, 0) + count
        top_cat = max(cat_counts.items(), key=lambda kv: kv[1])
        disagreement_events[kind] = {
            "n": len(items),
            "top_category": top_cat[0],
            "top_category_count": top_cat[1],
            "all_categories": _sorted_count_dict(cat_counts),
            "pre_task_readiness_distribution": _sorted_count_dict(readiness_counts),
            "by_category_x_pause_reason": {
                cat: _sorted_count_dict(reasons)
                for cat, reasons in sorted(category_x_pause_reason.items())
            },
        }
    # Description text for the LLM.
    disagreement_events["_descriptions"] = {
        "optimism_collapse": "pre_readiness≥4 + post_reflection≤2 — felt sharp, executed poorly. High-value calibration primitive.",
        "capacity_surprise": "pre_readiness≤2 + post_reflection≥4 — felt drained, executed well. Under-trusted state.",
        "flow_overrun": "post_reflection≥4 + executed≥1.3×planned — high focus AND big overrun (positive valence, not friction).",
        "friction_completion": "post_reflection≤2 + within ±15% of plan — forced through despite friction. Cost not visible in duration metrics alone.",
    }

    # ----- Post-pause transitions: pause_reason → next-task category
    # Answers "after pauses for reason X, what category does the user pick up?"
    # Distinct from context_switch_graph which only tracks parent_task_id
    # (formal /v1/stopwatch/switch). This catches natural cross-task
    # transitions where the user simply stops one task and starts another.
    post_pause_edges: dict[tuple[str, str], int] = {}
    post_pause_reason_totals: dict[str, int] = {}
    category_jump_by_reason: dict[str, dict[str, int]] = {}
    for pe in pause_events:
        if pe.resumed_at_utc is None:
            continue
        pe_session = sessions_by_id.get(pe.session_id)
        if pe_session is None:
            continue
        origin_task = tasks_by_id.get(pe_session.task_id)
        if origin_task is None:
            continue
        origin_cat = origin_task.category or "uncategorized"
        # Find next session by same user that starts AFTER this pause's resume,
        # and is on a DIFFERENT task (cross-task transition only).
        next_s = None
        for s in sessions_sorted:
            if s.start_time_utc <= pe.resumed_at_utc:
                continue
            if s.task_id == pe_session.task_id:
                continue
            next_s = s
            break
        if next_s is None:
            continue
        next_task = tasks_by_id.get(next_s.task_id)
        if next_task is None:
            continue
        next_cat = next_task.category or "uncategorized"
        key = (pe.pause_reason, next_cat)
        post_pause_edges[key] = post_pause_edges.get(key, 0) + 1
        post_pause_reason_totals[pe.pause_reason] = (
            post_pause_reason_totals.get(pe.pause_reason, 0) + 1
        )
        jump_bag = category_jump_by_reason.setdefault(
            pe.pause_reason, {"same_category": 0, "category_jump": 0}
        )
        if origin_cat == next_cat:
            jump_bag["same_category"] += 1
        else:
            jump_bag["category_jump"] += 1
    post_pause_transitions = sorted(
        [
            {"pause_reason": k[0], "next_category": k[1], "count": v}
            for k, v in post_pause_edges.items()
        ],
        key=lambda d: -d["count"],
    )[:20]

    baseline_category_counts: dict[str, int] = {}
    for t in executed:
        cat = t.category or "uncategorized"
        baseline_category_counts[cat] = baseline_category_counts.get(cat, 0) + 1
    baseline_category_frequency = _normalize(baseline_category_counts)
    post_pause_transitions_lift = []
    for (reason, next_cat), count in post_pause_edges.items():
        reason_total = post_pause_reason_totals.get(reason, 0)
        if reason_total == 0:
            continue
        edge_frequency = round(count / reason_total, 3)
        baseline = baseline_category_frequency.get(next_cat, 0.0)
        lift = round(edge_frequency / baseline, 3) if baseline > 0 else None
        post_pause_transitions_lift.append({
            "pause_reason": reason,
            "next_category": next_cat,
            "count": count,
            "edge_frequency_within_pause_reason": edge_frequency,
            "baseline_category_frequency": baseline,
            "lift_vs_baseline": lift,
        })
    post_pause_transitions_lift = sorted(
        post_pause_transitions_lift,
        key=lambda d: (
            d["lift_vs_baseline"] is None,
            -(d["lift_vs_baseline"] or 0),
            -d["count"],
        ),
    )[:20]
    post_pause_category_jump = {}
    for reason, bag in category_jump_by_reason.items():
        total = bag["same_category"] + bag["category_jump"]
        post_pause_category_jump[reason] = {
            **bag,
            "n": total,
            "category_jump_rate": round(bag["category_jump"] / total, 3) if total else None,
        }

    # ----- Big-overrun next-task valence cascade/rebound map.
    big_overrun_next_valence: dict[str, Any] = {
        "threshold": "executed_duration_minutes >= 1.5 * planned_duration_minutes",
        "n_origin_tasks": 0,
        "by_origin_valence": {},
        "by_origin_disagreement": {},
    }
    for idx, t in enumerate(executed_sorted):
        planned = t.planned_duration_minutes or 0
        executed_minutes = t.executed_duration_minutes or 0
        if planned <= 0 or executed_minutes / planned < 1.5:
            continue
        next_task = executed_sorted[idx + 1] if idx + 1 < len(executed_sorted) else None
        if next_task is None:
            continue
        big_overrun_next_valence["n_origin_tasks"] += 1
        next_valence = valence_by_task_id[next_task.task_id]
        origin_valence = valence_by_task_id[t.task_id]
        origin_disagreement = disagreement_by_task_id[t.task_id] or "none"
        for key_name, key_value in (
            ("by_origin_valence", origin_valence),
            ("by_origin_disagreement", origin_disagreement),
        ):
            bag = big_overrun_next_valence[key_name].setdefault(
                key_value, {"n": 0, "next_valence_counts": {}}
            )
            bag["n"] += 1
            counts = bag["next_valence_counts"]
            counts[next_valence] = counts.get(next_valence, 0) + 1
    for key_name in ("by_origin_valence", "by_origin_disagreement"):
        for bag in big_overrun_next_valence[key_name].values():
            bag["next_valence_counts"] = _sorted_count_dict(bag["next_valence_counts"])

    # ----- Repeated-reschedule terminal-state distribution.
    repeated_reschedule_tasks = [t for t in tasks if (t.reschedule_count or 0) >= 2]
    terminal_state_distribution: dict[str, int] = {}
    terminal_by_category: dict[str, dict[str, int]] = {}
    for t in repeated_reschedule_tasks:
        state = t.state.value if hasattr(t.state, "value") else str(t.state)
        terminal_state_distribution[state] = terminal_state_distribution.get(state, 0) + 1
        cat = t.category or "uncategorized"
        cat_bag = terminal_by_category.setdefault(cat, {})
        cat_bag[state] = cat_bag.get(state, 0) + 1
    reschedule_escape_valves = {
        "filter": "task.reschedule_count >= 2",
        "n_tasks": len(repeated_reschedule_tasks),
        "terminal_state_distribution": _sorted_count_dict(terminal_state_distribution),
        "by_category": {
            cat: _sorted_count_dict(states)
            for cat, states in sorted(terminal_by_category.items())
        },
    }

    # Enrich snooze chains with acceptance by depth and mechanism. If depth
    # never exceeds 0, the agent can say "not enough chain data" instead of
    # inferring a collapse point.
    depth_by_firing_id: dict[str, int] = {}
    for pp in pause_predictions:
        depth = 0
        cur = pp
        while cur.parent_firing_id and cur.parent_firing_id in pp_by_id:
            depth += 1
            cur = pp_by_id[cur.parent_firing_id]
            if depth > 20:
                break
        depth_by_firing_id[pp.firing_id] = depth
    acceptance_by_depth: dict[str, dict[str, int]] = {}
    acceptance_by_mechanism_depth: dict[str, dict[str, dict[str, int]]] = {}
    for pp in pause_predictions:
        depth_key = str(depth_by_firing_id.get(pp.firing_id, 0))
        response = pp.user_response or "no_response"
        depth_bag = acceptance_by_depth.setdefault(depth_key, {"n": 0, "accepted": 0})
        depth_bag["n"] += 1
        if response == "pause_now":
            depth_bag["accepted"] += 1
        mech_bag = acceptance_by_mechanism_depth.setdefault(pp.mechanism, {})
        md_bag = mech_bag.setdefault(depth_key, {"n": 0, "accepted": 0})
        md_bag["n"] += 1
        if response == "pause_now":
            md_bag["accepted"] += 1
    for bag in acceptance_by_depth.values():
        bag["acceptance_rate"] = round(bag["accepted"] / bag["n"], 3) if bag["n"] else None
    for mech_bag in acceptance_by_mechanism_depth.values():
        for bag in mech_bag.values():
            bag["acceptance_rate"] = round(bag["accepted"] / bag["n"], 3) if bag["n"] else None
    snooze_chains["acceptance_by_depth"] = acceptance_by_depth
    snooze_chains["acceptance_by_mechanism_depth"] = acceptance_by_mechanism_depth

    # ----- Confidence per top-level signal (rolled up)
    confidence_per_signal = {
        "pause_distribution": _confidence_tier(n_pause_events),
        "recovery_latency": _confidence_tier(
            sum(len(v) for v in latencies_by_reason.values())
        ),
        "hesitation_chain": _confidence_tier(len(creation_to_planned)),
        "schedule_volatility": _confidence_tier(len(tasks)),
        "context_switch_graph": _confidence_tier(sum(switch_edges.values())),
        "snooze_chains": _confidence_tier(len(pause_predictions)),
        "reflection_engagement": _confidence_tier(len(reflections)),
        "valence_distribution": _confidence_tier(sum(valence_counts.values())),
        "valence_preconditions": _confidence_tier(sum(valence_counts.values())),
        "disagreement_events": _confidence_tier(
            sum(v["n"] for k, v in disagreement_events.items() if k != "_descriptions")
        ),
        "post_pause_transitions": _confidence_tier(sum(post_pause_edges.values())),
        "post_pause_transitions_lift": _confidence_tier(sum(post_pause_edges.values())),
        "big_overrun_next_valence": _confidence_tier(
            big_overrun_next_valence["n_origin_tasks"]
        ),
        "reschedule_escape_valves": _confidence_tier(len(repeated_reschedule_tasks)),
    }
    n_by_covered_signal = {
        "pause behavior (reason distribution, initiator, time-of-day)": n_pause_events,
        "recovery latency by pause reason": sum(
            len(v) for v in latencies_by_reason.values()
        ),
        "task hesitation (creation->planned-start, planned->executed-start)": {
            "creation_to_planned_start_minutes": len(creation_to_planned),
            "planned_to_executed_start_minutes": len(planned_to_executed),
        },
        "schedule volatility (reschedule counts)": len(tasks),
        "context-switch graph via parent_task_id (formal /switch endpoint)": sum(
            switch_edges.values()
        ),
        "post-pause cross-task transitions (pause_reason -> next-task category)": sum(
            post_pause_edges.values()
        ),
        "post-pause transition lift vs baseline category frequency": sum(
            post_pause_edges.values()
        ),
        "post-pause same-category vs category-jump rates": sum(post_pause_edges.values()),
        "task valence classification (friction/flow/scope_creep/under_plan/neutral)": sum(
            valence_counts.values()
        ),
        "valence preconditions (category, time-of-day, prior valence, readiness)": sum(
            valence_counts.values()
        ),
        "explicit-vs-implicit disagreements": sum(
            v["n"] for k, v in disagreement_events.items() if k != "_descriptions"
        ),
        "big-overrun next-task valence": big_overrun_next_valence["n_origin_tasks"],
        "reschedule>=2 terminal-state escape valves": len(repeated_reschedule_tasks),
        "pause-prediction snooze chains and mechanism": len(pause_predictions),
        "reflection-surface engagement (dwell + outcome per reflection_type)": len(reflections),
    }

    return {
        "window_days": window_days,
        "n_sessions": n_sessions,
        "n_pause_events": n_pause_events,
        "pause_distribution": pause_distribution,
        "recovery_latency_by_reason": recovery_by_reason,
        "hesitation_chain": hesitation_chain,
        "schedule_volatility": schedule_volatility,
        "context_switch_graph": context_switch_graph,
        "post_pause_transitions": post_pause_transitions,
        "post_pause_transitions_lift_vs_baseline": post_pause_transitions_lift,
        "post_pause_category_jump": post_pause_category_jump,
        "baseline_category_frequency": baseline_category_frequency,
        "valence_distribution": valence_distribution,
        "valence_preconditions": valence_preconditions,
        "disagreement_events": disagreement_events,
        "big_overrun_next_valence": big_overrun_next_valence,
        "reschedule_escape_valves": reschedule_escape_valves,
        "snooze_chains": snooze_chains,
        "reflection_engagement": reflection_engagement,
        "confidence_per_signal": confidence_per_signal,
        # Explicit grounding for the LLM — what this tool DOES and DOES NOT
        # cover. Anti-hallucination defense added 2026-05-02 after operator
        # caught JARVIS inventing onboarding-fingerprint insights it had no
        # data for.
        "coverage": {
            "covered_signal_categories": [
                "pause behavior (reason distribution, initiator, time-of-day)",
                "recovery latency by pause reason",
                "task hesitation (creation→planned-start, planned→executed-start)",
                "schedule volatility (reschedule counts)",
                "context-switch graph via parent_task_id (formal /switch endpoint)",
                "post-pause cross-task transitions (pause_reason → next-task category)",
                "post-pause transition lift vs baseline category frequency",
                "post-pause same-category vs category-jump rates",
                "task valence classification (friction/flow/scope_creep/under_plan/neutral)",
                "valence preconditions (category, time-of-day, prior valence, readiness)",
                "explicit-vs-implicit disagreements (optimism_collapse, capacity_surprise, flow_overrun, friction_completion)",
                "big-overrun next-task valence, crossed by origin valence and disagreement type",
                "reschedule>=2 terminal-state escape valves",
                "pause-prediction snooze chains and mechanism",
                "reflection-surface engagement (dwell + outcome per reflection_type)",
            ],
            "n_by_covered_signal": n_by_covered_signal,
            "NOT_covered_dont_speculate_about_these": [
                "onboarding fingerprint (integration-connect order, skipped steps, archetype-survey response patterns) — NOT INSTRUMENTED",
                "modal dwell / typing latency / hesitation-before-clicking — NOT INSTRUMENTED (Phase 6 telemetry)",
                "calendar/Moodle integration retry patterns or reconnect cadence",
                "per-archetype-item survey timings or response variance",
                "deadline-binding decision history",
                "daily / weekly cascade chains across days (only immediate next-task after big overrun is computed)",
                "user demographics, age, schooling level",
                "external-event attendance vs no-show patterns",
            ],
            "answering_rule": (
                "Answer only from named fields in this payload. If the user asks for "
                "a slice that is not present as a field, say the slice is not computed "
                "by analyze_behavioral_signature yet. Do not infer category/time/"
                "readiness fingerprints from coverage labels alone."
            ),
            "hallucination_rule": (
                "If the operator asks about a signal in NOT_covered, you MUST say "
                "explicitly: 'I don't have that signal in my tool output — I can only "
                "speak to the categories in covered_signal_categories.' Do NOT invent "
                "patterns from data you don't have. Confident-sounding fabrication is "
                "worse than honest 'I can't answer that with current tools.'"
            ),
        },
    }
