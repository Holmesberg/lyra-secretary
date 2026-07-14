"""Pure, read-only replay primitives for founder pause-policy calibration.

This module mirrors the shipped pause predictor against exported history. It
does not choose a cohort policy, write product state, or enable delivery.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median, stdev
from typing import Any, Iterable
from zoneinfo import ZoneInfo


CONFIDENCE_FLOORS = (0.20, 0.25, 0.30, 0.35, 0.40)
MAX_LEAD_WINDOWS = (3, 5, 10)
MIN_LEAD_MINUTES = 2
HISTORY_GATE_DAYS = 7
MIN_SAMPLES = 5
LOOKBACK_DAYS = 28
OUTCOME_WINDOW_MINUTES = 15
LATE_WINDOW_MINUTES = 60
QUIET_HOUR_START = 22
QUIET_HOUR_END = 8
MIN_PROMPT_SPACING_MINUTES = 30
MAX_PAUSE_PROMPTS_PER_DAY = 3
PAUSE_EXPOSURE_HORIZON_MINUTES = 45
RANDOM_NULL_REPETITIONS = 10_000
BOOTSTRAP_REPETITIONS = 10_000
MINIMUM_ABSOLUTE_LIFT = 0.10
MINIMUM_DISCRETE_HIT_LIFT = 1
MINIMUM_RANDOM_NULL_PERCENTILE = 0.90
LOCAL_ZONE = ZoneInfo("Africa/Cairo")


FROZEN_DEFINITIONS = {
    "scope": "founder_only",
    "status": "provisional",
    "transportability": "unknown",
    "eligible_session": (
        "closed session; valid positive span; not auto-closed; no session "
        "quality flag; canonical task exists and is not voided"
    ),
    "scheduler_ticks": "UTC minute boundaries after session start",
    "history_gate_days": HISTORY_GATE_DAYS,
    "lookback_days": LOOKBACK_DAYS,
    "minimum_samples": MIN_SAMPLES,
    "minimum_lead_minutes_inclusive": MIN_LEAD_MINUTES,
    "confidence_floors": CONFIDENCE_FLOORS,
    "maximum_lead_minutes_inclusive": MAX_LEAD_WINDOWS,
    "hit": (
        "first non-retroactive same-user pause from simulated fire time "
        "through predicted_at plus 15 minutes, inclusive"
    ),
    "late": (
        "first qualifying pause after the hit window through predicted_at "
        "plus 60 minutes, inclusive"
    ),
    "active_use_day": "Cairo local day containing an eligible session",
    "observed_accuracy": "hits / simulated opportunities with closed windows",
    "quiet_hours": "22:00 through 07:59 Cairo local time",
    "pause_prompt_cap": "one per session and three per Cairo local day",
    "cross_prompt_spacing_minutes": MIN_PROMPT_SPACING_MINUTES,
    "empirical_base_rate": (
        "qualifying-pause rate across every eligible holdout minute using "
        "the selected lead plus 15-minute observation window"
    ),
    "simple_baselines": (
        "fixed 30-minute pause time and calibration-period median pause "
        "time; both use selected lead, eligibility, burden, and outcome rules"
    ),
    "random_null": (
        "one uniformly sampled eligible minute per session before burden; "
        "10,000 deterministic seeds numbered 0 through 9,999"
    ),
    "bootstrap": (
        "paired holdout-session resampling with 10,000 deterministic seeds; "
        "80 percent interval for v2 minus strongest simple comparator"
    ),
    "minimum_absolute_lift": MINIMUM_ABSOLUTE_LIFT,
    "minimum_discrete_hit_lift": MINIMUM_DISCRETE_HIT_LIFT,
    "minimum_random_null_percentile": MINIMUM_RANDOM_NULL_PERCENTILE,
    "split": "earliest 70 percent calibration; latest 30 percent holdout",
    "selection": (
        "median 1-2 opportunities per active-use day; then narrower lead, "
        "higher confidence floor, higher calibration accuracy"
    ),
}


def definitions_hash() -> str:
    encoded = json.dumps(FROZEN_DEFINITIONS, sort_keys=True, default=list).encode()
    return hashlib.sha256(encoded).hexdigest()


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    return parsed


@dataclass(frozen=True)
class ReplaySession:
    session_id: str
    task_id: str
    category: str | None
    start: datetime
    end: datetime


@dataclass(frozen=True)
class ReplayPause:
    session_id: str
    at: datetime
    retroactive: bool


@dataclass(frozen=True)
class ReplayCandidate:
    session_id: str
    fired_at: datetime
    predicted_at: datetime
    confidence: float
    mechanism: str


@dataclass(frozen=True)
class ReplayDataset:
    sessions: tuple[ReplaySession, ...]
    pauses: tuple[ReplayPause, ...]
    history_gate_pause_times: tuple[datetime, ...]
    training_pause_times: tuple[datetime, ...]
    qualifying_pause_times: tuple[datetime, ...]
    dirty_training_pause_times: frozenset[datetime]


def _pause_is_dirty(exported: dict[str, Any], event_time: datetime) -> bool:
    start = event_time - timedelta(minutes=PAUSE_EXPOSURE_HORIZON_MINUTES)
    render_times: dict[str, list[datetime]] = {}
    for row in exported.get("exposure_render_events", []):
        rendered = _dt(row.get("rendered_at"))
        if rendered:
            render_times.setdefault(str(row.get("exposure_id")), []).append(rendered)
    suppression_ids = {
        str(row.get("exposure_id"))
        for row in exported.get("suppression_events", [])
    }
    for row in exported.get("exposure_decision_events", []):
        eligible = _dt(row.get("eligible_at"))
        if (
            row.get("exposure_category") != "predictive_alert"
            or row.get("decision_status") == "reserved"
            or eligible is None
            or not start <= eligible <= event_time
        ):
            continue
        exposure_id = str(row.get("exposure_id"))
        if any(start <= value <= event_time for value in render_times.get(exposure_id, [])):
            return True
        if exposure_id not in suppression_ids:
            return True  # incomplete lifecycle fails closed

    for row in exported.get("reflection_view_logs", []):
        fired = _dt(row.get("fired_at"))
        if (
            row.get("event_class") == "impression"
            and row.get("reflection_type") in {"pause_prediction", "resume_prediction"}
            and row.get("viewed_at")
            and fired is not None
            and start <= fired <= event_time
        ):
            return True
    for section in ("pause_prediction_logs", "resume_prediction_logs"):
        for row in exported.get(section, []):
            fired = _dt(row.get("fired_at"))
            if fired is not None and start <= fired <= event_time:
                return True
    return False


def build_dataset(exported: dict[str, Any]) -> ReplayDataset:
    tasks = {str(row.get("task_id")): row for row in exported.get("tasks", [])}
    sessions: list[ReplaySession] = []
    eligible_session_ids: set[str] = set()
    for row in exported.get("stopwatch_sessions", []):
        task_id = str(row.get("task_id"))
        task = tasks.get(task_id)
        start = _dt(row.get("start_time_utc"))
        end = _dt(row.get("end_time_utc"))
        if (
            task is None
            or task.get("voided_at")
            or row.get("auto_closed") is not False
            or row.get("data_quality_flag")
            or start is None
            or end is None
            or end <= start
        ):
            continue
        session_id = str(row.get("session_id"))
        sessions.append(
            ReplaySession(session_id, task_id, task.get("category"), start, end)
        )
        eligible_session_ids.add(session_id)
    sessions.sort(key=lambda row: (row.start, row.session_id))

    pauses: list[ReplayPause] = []
    history_gate_pause_times: list[datetime] = []
    training_pause_times: list[datetime] = []
    dirty: set[datetime] = set()
    for row in exported.get("pause_events", []):
        at = _dt(row.get("paused_at_utc"))
        if at is None:
            continue
        history_gate_pause_times.append(at)
        if row.get("self_reported_retroactively") is True:
            continue
        training_pause_times.append(at)
        if _pause_is_dirty(exported, at):
            dirty.add(at)
        session_id = str(row.get("session_id"))
        if session_id in eligible_session_ids:
            pauses.append(ReplayPause(session_id, at, False))
    pauses.sort(key=lambda row: (row.at, row.session_id))
    history_gate_pause_times.sort()
    training_pause_times.sort()
    return ReplayDataset(
        sessions=tuple(sessions),
        pauses=tuple(pauses),
        history_gate_pause_times=tuple(history_gate_pause_times),
        training_pause_times=tuple(training_pause_times),
        qualifying_pause_times=tuple(training_pause_times),
        dirty_training_pause_times=frozenset(dirty),
    )


def chronological_split(
    sessions: tuple[ReplaySession, ...],
) -> tuple[tuple[ReplaySession, ...], tuple[ReplaySession, ...]]:
    split_at = math.floor(len(sessions) * 0.70)
    return sessions[:split_at], sessions[split_at:]


def _confidence(samples: list[float]) -> float:
    dispersion = stdev(samples) if len(samples) > 1 else 0.0
    sample_factor = min(1.0, len(samples) / 15.0)
    dispersion_factor = max(0.0, 1.0 - dispersion / 30.0)
    return round(min(0.95, 0.30 + 0.30 * sample_factor + 0.40 * dispersion_factor), 3)


def _candidate_at(
    dataset: ReplayDataset,
    active: ReplaySession,
    now: datetime,
    confidence_floor: float,
    max_lead_minutes: int,
) -> ReplayCandidate | None:
    gate_history = [value for value in dataset.history_gate_pause_times if value < now]
    if not gate_history or now - gate_history[0] < timedelta(days=HISTORY_GATE_DAYS):
        return None
    lookback = now - timedelta(days=LOOKBACK_DAYS)
    candidates: list[ReplayCandidate] = []

    anchor_samples = [
        value.minute + value.second / 60.0
        for value in dataset.training_pause_times
        if value < now
        if value >= lookback
        and value not in dataset.dirty_training_pause_times
        and value.hour == now.hour
        and (value.weekday() >= 5) == (now.weekday() >= 5)
    ]
    if len(anchor_samples) >= MIN_SAMPLES:
        anchor_minute = median(anchor_samples)
        predicted = now.replace(
            minute=int(anchor_minute),
            second=int(round((anchor_minute % 1) * 60)),
            microsecond=0,
        )
        lead = (predicted - now).total_seconds() / 60.0
        confidence = _confidence(anchor_samples)
        if (
            predicted > now
            and MIN_LEAD_MINUTES <= lead <= max_lead_minutes
            and confidence >= confidence_floor
        ):
            candidates.append(
                ReplayCandidate(active.session_id, now, predicted, confidence, "clock_anchor")
            )

    if active.category:
        first_pause: dict[str, datetime] = {}
        for pause in dataset.pauses:
            if pause.at >= now:
                break
            first_pause.setdefault(pause.session_id, pause.at)
        rhythm_samples = [
            (first_pause[row.session_id] - row.start).total_seconds() / 60.0
            for row in dataset.sessions
            if row.start >= lookback
            and row.start < now
            and row.category == active.category
            and row.session_id in first_pause
            and first_pause[row.session_id] not in dataset.dirty_training_pause_times
        ]
        if len(rhythm_samples) >= MIN_SAMPLES:
            predicted = active.start + timedelta(minutes=median(rhythm_samples))
            lead = (predicted - now).total_seconds() / 60.0
            confidence = _confidence(rhythm_samples)
            if (
                predicted > now
                and MIN_LEAD_MINUTES <= lead <= max_lead_minutes
                and confidence >= confidence_floor
            ):
                candidates.append(
                    ReplayCandidate(active.session_id, now, predicted, confidence, "work_rhythm")
                )
    return max(candidates, key=lambda row: row.confidence, default=None)


def _ceil_minute(value: datetime) -> datetime:
    rounded = value.replace(second=0, microsecond=0)
    return rounded if value == rounded else rounded + timedelta(minutes=1)


def _local_day(value: datetime) -> str:
    return value.replace(tzinfo=ZoneInfo("UTC")).astimezone(LOCAL_ZONE).date().isoformat()


def _outside_quiet_hours(value: datetime) -> bool:
    hour = value.replace(tzinfo=ZoneInfo("UTC")).astimezone(LOCAL_ZONE).hour
    return QUIET_HOUR_END <= hour < QUIET_HOUR_START


def apply_pause_burden(
    candidates: Iterable[ReplayCandidate],
) -> tuple[ReplayCandidate, ...]:
    accepted: list[ReplayCandidate] = []
    day_counts: dict[str, int] = {}
    for candidate in sorted(candidates, key=lambda row: (row.fired_at, row.session_id)):
        day = _local_day(candidate.fired_at)
        if day_counts.get(day, 0) >= MAX_PAUSE_PROMPTS_PER_DAY:
            continue
        if accepted and candidate.fired_at - accepted[-1].fired_at < timedelta(
            minutes=MIN_PROMPT_SPACING_MINUTES
        ):
            continue
        accepted.append(candidate)
        day_counts[day] = day_counts.get(day, 0) + 1
    return tuple(accepted)


def replay_candidates(
    dataset: ReplayDataset,
    sessions: Iterable[ReplaySession],
    *,
    confidence_floor: float,
    max_lead_minutes: int,
) -> tuple[ReplayCandidate, ...]:
    first_pause = {row.session_id: row.at for row in dataset.pauses}
    raw: list[ReplayCandidate] = []
    for session in sessions:
        cutoff = min(session.end, first_pause.get(session.session_id, session.end))
        now = _ceil_minute(session.start)
        while now < cutoff:
            if _outside_quiet_hours(now):
                candidate = _candidate_at(
                    dataset, session, now, confidence_floor, max_lead_minutes
                )
                if candidate is not None:
                    raw.append(candidate)
                    break
            now += timedelta(minutes=1)

    return apply_pause_burden(raw)


def summarize(
    dataset: ReplayDataset,
    sessions: Iterable[ReplaySession],
    candidates: Iterable[ReplayCandidate],
) -> dict[str, Any]:
    session_rows = tuple(sessions)
    candidate_rows = tuple(candidates)
    active_days = sorted({_local_day(row.start) for row in session_rows})
    opportunities_by_day = {day: 0 for day in active_days}
    hits = late = misses = 0
    mechanisms: dict[str, int] = {}
    for candidate in candidate_rows:
        opportunities_by_day[_local_day(candidate.fired_at)] += 1
        mechanisms[candidate.mechanism] = mechanisms.get(candidate.mechanism, 0) + 1
        hit_end = candidate.predicted_at + timedelta(minutes=OUTCOME_WINDOW_MINUTES)
        late_end = candidate.predicted_at + timedelta(minutes=LATE_WINDOW_MINUTES)
        future = [
            value
            for value in dataset.qualifying_pause_times
            if value >= candidate.fired_at
        ]
        first_hit = next((value for value in future if value <= hit_end), None)
        if first_hit is not None:
            hits += 1
        elif next((value for value in future if value <= late_end), None) is not None:
            late += 1
        else:
            misses += 1
    opportunities = len(candidate_rows)
    daily_values = list(opportunities_by_day.values())
    return {
        "eligible_sessions": len(session_rows),
        "active_use_days": len(active_days),
        "opportunities": opportunities,
        "opportunities_per_active_day_median": median(daily_values) if daily_values else 0.0,
        "opportunities_per_session": opportunities / len(session_rows) if session_rows else 0.0,
        "hits": hits,
        "late": late,
        "misses": misses,
        "observed_accuracy": hits / opportunities if opportunities else None,
        "false_prompt_rate": misses / opportunities if opportunities else None,
        "mechanism_counts": dict(sorted(mechanisms.items())),
    }


def calibration_grid(exported: dict[str, Any]) -> dict[str, Any]:
    dataset = build_dataset(exported)
    calibration, holdout = chronological_split(dataset.sessions)
    rows = []
    for max_lead in MAX_LEAD_WINDOWS:
        for floor in CONFIDENCE_FLOORS:
            candidates = replay_candidates(
                dataset,
                calibration,
                confidence_floor=floor,
                max_lead_minutes=max_lead,
            )
            rows.append(
                {
                    "confidence_floor": floor,
                    "max_lead_minutes": max_lead,
                    "metrics": summarize(dataset, calibration, candidates),
                }
            )
    eligible = [
        row
        for row in rows
        if 1 <= row["metrics"]["opportunities_per_active_day_median"] <= 2
    ]
    eligible.sort(
        key=lambda row: (
            row["max_lead_minutes"],
            -row["confidence_floor"],
            -(row["metrics"]["observed_accuracy"] or 0.0),
        )
    )
    return {
        "definitions_hash": definitions_hash(),
        "scope": "founder_only",
        "status": "calibration_only",
        "transportability": "unknown",
        "eligible_sessions": len(dataset.sessions),
        "eligible_active_days": len({_local_day(row.start) for row in dataset.sessions}),
        "calibration_sessions": len(calibration),
        "holdout_sessions": len(holdout),
        "holdout_evaluated": False,
        "configurations": rows,
        "selected_configuration": (
            {
                "confidence_floor": eligible[0]["confidence_floor"],
                "max_lead_minutes": eligible[0]["max_lead_minutes"],
            }
            if eligible
            else None
        ),
    }
