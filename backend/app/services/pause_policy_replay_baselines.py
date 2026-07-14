"""Frozen holdout and null comparisons for founder pause-policy replay."""
from __future__ import annotations

import random
from datetime import timedelta
from statistics import median
from typing import Any, Iterable

from app.services.pause_policy_replay import (
    BOOTSTRAP_REPETITIONS,
    LATE_WINDOW_MINUTES,
    MINIMUM_ABSOLUTE_LIFT,
    MINIMUM_DISCRETE_HIT_LIFT,
    MINIMUM_RANDOM_NULL_PERCENTILE,
    OUTCOME_WINDOW_MINUTES,
    RANDOM_NULL_REPETITIONS,
    ReplayCandidate,
    ReplayDataset,
    ReplaySession,
    _ceil_minute,
    _local_day,
    _outside_quiet_hours,
    apply_pause_burden,
    build_dataset,
    calibration_grid,
    chronological_split,
    replay_candidates,
    summarize,
)


def _first_pause_by_session(dataset: ReplayDataset) -> dict[str, Any]:
    result = {}
    for pause in dataset.pauses:
        result.setdefault(pause.session_id, pause.at)
    return result


def _eligible_ticks(dataset: ReplayDataset, session: ReplaySession) -> list[Any]:
    first_pause = _first_pause_by_session(dataset).get(session.session_id)
    cutoff = min(session.end, first_pause or session.end)
    tick = _ceil_minute(session.start)
    ticks = []
    while tick < cutoff:
        if _outside_quiet_hours(tick):
            ticks.append(tick)
        tick += timedelta(minutes=1)
    return ticks


def _candidate_for_predicted_time(
    session: ReplaySession,
    predicted_at: Any,
    max_lead_minutes: int,
    mechanism: str,
) -> ReplayCandidate | None:
    fired_at = _ceil_minute(predicted_at - timedelta(minutes=max_lead_minutes))
    lead = (predicted_at - fired_at).total_seconds() / 60.0
    if fired_at < session.start or not 2 <= lead <= max_lead_minutes:
        return None
    return ReplayCandidate(session.session_id, fired_at, predicted_at, 0.0, mechanism)


def _fixed_candidates(
    dataset: ReplayDataset,
    sessions: Iterable[ReplaySession],
    *,
    pause_offset_minutes: float,
    max_lead_minutes: int,
    mechanism: str,
) -> tuple[ReplayCandidate, ...]:
    rows = []
    for session in sessions:
        candidate = _candidate_for_predicted_time(
            session,
            session.start + timedelta(minutes=pause_offset_minutes),
            max_lead_minutes,
            mechanism,
        )
        if (
            candidate is not None
            and candidate.fired_at in set(_eligible_ticks(dataset, session))
        ):
            rows.append(candidate)
    return apply_pause_burden(rows)


def _calibration_median_offset(
    dataset: ReplayDataset, calibration: Iterable[ReplaySession]
) -> float | None:
    first_pause = _first_pause_by_session(dataset)
    values = [
        (first_pause[row.session_id] - row.start).total_seconds() / 60.0
        for row in calibration
        if row.session_id in first_pause
        and first_pause[row.session_id] not in dataset.dirty_training_pause_times
    ]
    return median(values) if values else None


def _is_hit(dataset: ReplayDataset, candidate: ReplayCandidate) -> bool:
    end = candidate.predicted_at + timedelta(minutes=OUTCOME_WINDOW_MINUTES)
    return any(
        candidate.fired_at <= value <= end
        for value in dataset.qualifying_pause_times
    )


def _empirical_eligible_minute_rate(
    dataset: ReplayDataset,
    sessions: Iterable[ReplaySession],
    max_lead_minutes: int,
) -> dict[str, Any]:
    total = hits = 0
    for session in sessions:
        for tick in _eligible_ticks(dataset, session):
            total += 1
            end = tick + timedelta(minutes=max_lead_minutes + OUTCOME_WINDOW_MINUTES)
            if any(tick <= value <= end for value in dataset.qualifying_pause_times):
                hits += 1
    return {"eligible_minutes": total, "hits": hits, "rate": hits / total if total else None}


def _random_candidates(
    dataset: ReplayDataset,
    sessions: Iterable[ReplaySession],
    *,
    max_lead_minutes: int,
    seed: int,
) -> tuple[ReplayCandidate, ...]:
    rng = random.Random(seed)
    rows = []
    for session in sessions:
        ticks = _eligible_ticks(dataset, session)
        if not ticks:
            continue
        fired_at = ticks[rng.randrange(len(ticks))]
        rows.append(
            ReplayCandidate(
                session.session_id,
                fired_at,
                fired_at + timedelta(minutes=max_lead_minutes),
                0.0,
                "random_time",
            )
        )
    return apply_pause_burden(rows)


def _percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * probability)
    return ordered[index]


def _paired_bootstrap_interval(
    dataset: ReplayDataset,
    sessions: tuple[ReplaySession, ...],
    v2: tuple[ReplayCandidate, ...],
    baseline: tuple[ReplayCandidate, ...],
) -> list[float] | None:
    v2_by_session = {row.session_id: _is_hit(dataset, row) for row in v2}
    baseline_by_session = {row.session_id: _is_hit(dataset, row) for row in baseline}
    session_ids = [row.session_id for row in sessions]
    if not session_ids:
        return None
    lifts = []
    for seed in range(BOOTSTRAP_REPETITIONS):
        rng = random.Random(seed)
        sample = [session_ids[rng.randrange(len(session_ids))] for _ in session_ids]
        v2_values = [v2_by_session[value] for value in sample if value in v2_by_session]
        baseline_values = [
            baseline_by_session[value] for value in sample if value in baseline_by_session
        ]
        if not v2_values or not baseline_values:
            continue
        lifts.append(
            sum(v2_values) / len(v2_values)
            - sum(baseline_values) / len(baseline_values)
        )
    if not lifts:
        return None
    return [_percentile(lifts, 0.10), _percentile(lifts, 0.90)]


def evaluate_founder_holdout(exported: dict[str, Any]) -> dict[str, Any]:
    calibration_result = calibration_grid(exported)
    selected = calibration_result["selected_configuration"]
    if selected is None:
        return {
            **calibration_result,
            "status": "inconclusive",
            "reason": "no_calibration_configuration_met_opportunity_constraints",
        }

    dataset = build_dataset(exported)
    calibration, holdout = chronological_split(dataset.sessions)
    holdout_days = len({_local_day(row.start) for row in holdout})
    if len(dataset.sessions) < 30 or len({_local_day(row.start) for row in dataset.sessions}) < 10:
        return {**calibration_result, "status": "inconclusive", "reason": "total_sample_minimum"}
    if len(holdout) < 9 or holdout_days < 3:
        return {**calibration_result, "status": "inconclusive", "reason": "holdout_sample_minimum"}

    max_lead = selected["max_lead_minutes"]
    floor = selected["confidence_floor"]
    v2 = replay_candidates(
        dataset, holdout, confidence_floor=floor, max_lead_minutes=max_lead
    )
    fixed = _fixed_candidates(
        dataset,
        holdout,
        pause_offset_minutes=30,
        max_lead_minutes=max_lead,
        mechanism="fixed_30_minute",
    )
    median_offset = _calibration_median_offset(dataset, calibration)
    median_rows = (
        _fixed_candidates(
            dataset,
            holdout,
            pause_offset_minutes=median_offset,
            max_lead_minutes=max_lead,
            mechanism="calibration_median",
        )
        if median_offset is not None
        else tuple()
    )
    v2_metrics = summarize(dataset, holdout, v2)
    fixed_metrics = summarize(dataset, holdout, fixed)
    median_metrics = summarize(dataset, holdout, median_rows)
    empirical = _empirical_eligible_minute_rate(dataset, holdout, max_lead)

    simple = [("fixed_30_minute", fixed, fixed_metrics), ("calibration_median", median_rows, median_metrics)]
    strongest_name, strongest_rows, strongest_metrics = max(
        simple,
        key=lambda item: (item[2]["observed_accuracy"] or 0.0, item[2]["hits"]),
    )
    strongest_rate = max(
        strongest_metrics["observed_accuracy"] or 0.0,
        empirical["rate"] or 0.0,
    )

    random_rates = []
    for seed in range(RANDOM_NULL_REPETITIONS):
        rows = _random_candidates(
            dataset, holdout, max_lead_minutes=max_lead, seed=seed
        )
        metrics = summarize(dataset, holdout, rows)
        if metrics["observed_accuracy"] is not None:
            random_rates.append(metrics["observed_accuracy"])
    v2_rate = v2_metrics["observed_accuracy"] or 0.0
    random_percentile = (
        sum(value <= v2_rate for value in random_rates) / len(random_rates)
        if random_rates
        else None
    )
    interval = _paired_bootstrap_interval(dataset, holdout, v2, strongest_rows)
    burden_passes = (
        1 <= v2_metrics["opportunities_per_active_day_median"] <= 2
        and v2_metrics["opportunities_per_session"] <= 1
    )
    lift = v2_rate - strongest_rate
    signal_passes = (
        burden_passes
        and lift >= MINIMUM_ABSOLUTE_LIFT
        and v2_metrics["hits"] - strongest_metrics["hits"] >= MINIMUM_DISCRETE_HIT_LIFT
        and random_percentile is not None
        and random_percentile >= MINIMUM_RANDOM_NULL_PERCENTILE
        and interval is not None
        and interval[1] >= 0
    )
    return {
        **calibration_result,
        "status": (
            "founder_visible_candidate"
            if signal_passes
            else "no_incremental_signal_demonstrated"
        ),
        "holdout_evaluated": True,
        "holdout_active_days": holdout_days,
        "v2": v2_metrics,
        "comparators": {
            "empirical_eligible_minute": empirical,
            "fixed_30_minute": fixed_metrics,
            "calibration_median": {**median_metrics, "offset_minutes": median_offset},
            "strongest_simple": strongest_name,
        },
        "random_null": {
            "repetitions": len(random_rates),
            "median_hit_rate": median(random_rates) if random_rates else None,
            "p90_hit_rate": _percentile(random_rates, 0.90),
            "v2_percentile": random_percentile,
        },
        "absolute_lift_over_strongest": lift,
        "absolute_lift_bootstrap_80": interval,
        "burden_gate_passes": burden_passes,
        "incremental_signal_gate_passes": signal_passes,
        "visible_runtime_enabled": False,
    }
