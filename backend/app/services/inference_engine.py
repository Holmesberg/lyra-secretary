"""Shared inference primitives for JARVIS, analytics, and future user-facing surfaces.

Spec: `docs/calibration_contract.md` (R2 confidence tiers, R9 valence + disagreement).
Phase 3 extends this module with per-signal writers, retirement counters, and
payloads for `/v1/users/me` enrichment per R11.
"""

from __future__ import annotations

from typing import Literal

from app.db.models import Task

ValenceClass = Literal["friction", "flow", "scope_creep", "under_plan", "neutral"]

# R2 default: cold_start < 5, tentative 5–29, confirmed ≥ 30 (per-user, per-signal).
# R2.1 rare-signal overrides: (tentative_floor, confirmed_floor) where
# cold_start is n < tentative_floor, tentative is tentative_floor <= n < confirmed_floor.
SIGNAL_THRESHOLDS: dict[str, tuple[int, int]] = {
    "_default": (5, 30),
    # base_rate_justification: see calibration_contract R2.1 — rare, high-severity
    "cascade_recovery_latency": (3, 10),
    "abandonment_path_stability": (5, 15),
}


def confidence_tier_from_n(n: int, signal_key: str | None = None) -> str:
    """Map sample size to cold_start | tentative | confirmed per R2 / R2.1."""
    key = signal_key if signal_key and signal_key in SIGNAL_THRESHOLDS else "_default"
    t_floor, c_floor = SIGNAL_THRESHOLDS[key]
    if n < t_floor:
        return "cold_start"
    if n < c_floor:
        return "tentative"
    return "confirmed"


def classify_task_valence(t: Task) -> ValenceClass:
    """Classify a task's valence per docs/calibration_contract.md R9.

    Returns one of: friction | flow | scope_creep | under_plan | neutral.

    Naive 'implicit wins on disagreement' breaks at flow state (overrun + high
    focus = success not friction). The valence classifier runs BEFORE any
    implicit-vs-explicit resolution, distinguishing structural classes:

    - friction: overrun + low focus (≤2) + ≥3 pauses + scope unchanged
    - flow: overrun + high focus (≥4) + ≤1 pause
    - scope_creep: overrun + medium focus (3) + scope grew ≥50%
    - under_plan: underrun + high focus + ≤1 pause
    - neutral: within ±15% of plan, focus 3, pauses ≤2

    When focus rating is unavailable (NULL post_task_reflection), valence
    defaults to 'neutral' regardless of duration outcome — we don't have
    the explicit signal needed for resolution.
    """
    if t.executed_duration_minutes is None or t.planned_duration_minutes is None:
        return "neutral"
    if t.planned_duration_minutes <= 0:
        return "neutral"

    delta = t.executed_duration_minutes - t.planned_duration_minutes
    delta_pct = delta / t.planned_duration_minutes
    focus = t.post_task_reflection
    pauses = t.pause_count or 0

    if focus is None:
        return "neutral"

    overrun = delta_pct > 0.15
    underrun = delta_pct < -0.15
    high_focus = focus >= 4
    low_focus = focus <= 2
    medium_focus = focus == 3

    if overrun and high_focus and pauses <= 1:
        return "flow"
    if overrun and low_focus and pauses >= 3:
        return "friction"
    if overrun and medium_focus:
        return "scope_creep"
    if underrun and high_focus and pauses <= 1:
        return "under_plan"

    return "neutral"


def classify_disagreement(t: Task) -> str | None:
    """Classify explicit-vs-implicit disagreement type per task (R9 adjacent).

    The R9 valence classifier handles the *outcome-side* resolution. This
    helper surfaces the *input-vs-outcome* disagreement axis specifically:
    where the operator's pre-task self-report (readiness) didn't match the
    post-task self-report (focus) or the implicit execution behavior.

    Returns one of:
    - 'optimism_collapse': pre_readiness ≥4, post_reflection ≤2
    - 'capacity_surprise': pre_readiness ≤2, post_reflection ≥4
    - 'flow_overrun': post_reflection ≥4, executed ≥1.3× planned
    - 'friction_completion': post_reflection ≤2, |delta| ≤15%
    - None: no disagreement detected
    """
    if t.pre_task_readiness is None and t.post_task_reflection is None:
        return None
    pre = t.pre_task_readiness
    post = t.post_task_reflection
    planned = t.planned_duration_minutes or 0
    executed = t.executed_duration_minutes or 0

    if pre is not None and post is not None:
        if pre >= 4 and post <= 2:
            return "optimism_collapse"
        if pre <= 2 and post >= 4:
            return "capacity_surprise"

    if post is not None and planned > 0 and executed > 0:
        ratio = executed / planned
        if post >= 4 and ratio >= 1.3:
            return "flow_overrun"
        if post <= 2 and abs(ratio - 1.0) <= 0.15:
            return "friction_completion"

    return None
