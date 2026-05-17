"""Academic pressure map service.

V1 deliberately avoids new persistence. It reads existing deadlines,
planned Lyra tasks, and read-only calendar context to produce a bounded,
transparent workload-pressure snapshot. It does not claim behavioral
personalization and does not feed clean learning paths.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil

from sqlalchemy.orm import Session

from app.db.models import Deadline, Task, TaskState, User
from app.db.scoping import get_current_user_id
from app.schemas.academic import (
    AcademicComplexityTier,
    AcademicPressureEstimate,
    AcademicPressureItem,
    AcademicPressureMapResponse,
    AcademicPressureLevel,
    AcademicSourceSummary,
    AcademicTrustState,
)
from app.services.calendar_sync import fetch_google_events
from app.utils.time_utils import now_utc, strip_tz


MIN_HORIZON_DAYS = 1
MAX_HORIZON_DAYS = 30

_HIGH_COMPLEXITY_TERMS = {
    "algorithm",
    "algorithms",
    "compiler",
    "operating",
    "systems",
    "os",
    "math",
    "calculus",
    "probability",
    "statistics",
    "database",
    "architecture",
    "signals",
    "physics",
    "proof",
    "theory",
}


@dataclass(frozen=True)
class _TypePrior:
    low: int
    high: int
    assumption: str


_TYPE_PRIORS: dict[str, _TypePrior] = {
    "quiz": _TypePrior(240, 420, "quiz prior from assessment type"),
    "midterm": _TypePrior(480, 840, "midterm prior from assessment type"),
    "final": _TypePrior(720, 1200, "final-exam prior from assessment type"),
    "exam": _TypePrior(480, 840, "exam prior from assessment type"),
    "assignment": _TypePrior(120, 300, "assignment prior from assessment type"),
    "lab": _TypePrior(90, 240, "lab prior from assessment type"),
    "project": _TypePrior(360, 900, "project prior from assessment type"),
    "lecture": _TypePrior(75, 150, "lecture/revision prior without recording duration"),
    "deadline": _TypePrior(90, 240, "generic academic-deadline prior"),
}


def _clamp_horizon(days: int) -> int:
    return max(MIN_HORIZON_DAYS, min(MAX_HORIZON_DAYS, days))


def _classify_obligation(title: str) -> str:
    t = title.lower()
    if "final" in t:
        return "final"
    if "midterm" in t:
        return "midterm"
    if "quiz" in t:
        return "quiz"
    if "exam" in t:
        return "exam"
    if "project" in t:
        return "project"
    if "assignment" in t or "homework" in t or "sheet" in t:
        return "assignment"
    if "lab" in t:
        return "lab"
    if "lecture" in t or "revision" in t or "review" in t:
        return "lecture"
    return "deadline"


def _complexity_tier(title: str, category_hint: str | None) -> AcademicComplexityTier:
    haystack = f"{title} {category_hint or ''}".lower()
    if any(term in haystack for term in _HIGH_COMPLEXITY_TERMS):
        return "high"
    if any(term in haystack for term in ("reading", "note", "slides")):
        return "low"
    return "medium"


def _complexity_multiplier(tier: AcademicComplexityTier) -> float:
    if tier == "high":
        return 1.35
    if tier == "low":
        return 0.8
    return 1.0


def _round_minutes(value: float) -> int:
    """Round outward to 30-minute blocks to avoid fake precision."""
    return int(ceil(value / 30.0) * 30)


def _pressure_level(due_at: datetime, now: datetime) -> AcademicPressureLevel:
    due_at = strip_tz(due_at) or due_at
    delta_days = (due_at - now).total_seconds() / 86400
    if delta_days < 0:
        return "overdue"
    if delta_days <= 3:
        return "high"
    if delta_days <= 10:
        return "medium"
    return "low"


def _trust_state(deadline: Deadline) -> AcademicTrustState:
    if deadline.external_source == "moodle_ics":
        # Imported calendar entries are reachable/imported, but coverage
        # correctness is not guaranteed by the iCal feed alone.
        return "verified_reachable"
    return "requires_user_confirmation"


def _estimate(deadline: Deadline) -> AcademicPressureEstimate:
    obligation_type = _classify_obligation(deadline.title)
    tier = _complexity_tier(deadline.title, deadline.category_hint)
    prior = _TYPE_PRIORS.get(obligation_type, _TYPE_PRIORS["deadline"])
    multiplier = _complexity_multiplier(tier)
    low = _round_minutes(prior.low * multiplier)
    high = _round_minutes(prior.high * multiplier)
    assumptions = [
        prior.assumption,
        f"{tier} complexity tier from title/category heuristics",
        "no lecture/tutorial/resource counts attached yet",
        "no personal execution history applied to this estimate yet",
    ]
    if deadline.external_source:
        assumptions.append(f"imported from {deadline.external_source}; source remains canonical")
    else:
        assumptions.append("manually/native Lyra deadline; coverage needs user confirmation")
    return AcademicPressureEstimate(
        low_minutes=low,
        high_minutes=max(high, low + 30),
        confidence="low",
        assumptions=assumptions,
    )


def _calendar_busy_minutes(user_id: int, user: User | None, start: datetime, end: datetime) -> tuple[int, bool]:
    if user is None or not user.google_refresh_token:
        return 0, False
    events = fetch_google_events(user_id, start, end)
    total = 0
    for event in events:
        try:
            event_start = datetime.fromisoformat(event.start)
            event_end = datetime.fromisoformat(event.end)
        except ValueError:
            continue
        if event_end <= event_start:
            continue
        total += int((event_end - event_start).total_seconds() / 60)
    return total, True


def _planned_task_minutes(db: Session, user_id: int, start: datetime, end: datetime) -> int:
    rows = (
        db.query(Task.planned_duration_minutes)
        .filter(Task.user_id == user_id)
        .filter(Task.voided_at.is_(None))
        .filter(Task.state.in_([TaskState.PLANNED, TaskState.EXECUTING, TaskState.PAUSED]))
        .filter(Task.planned_start_utc >= start)
        .filter(Task.planned_start_utc < end)
        .all()
    )
    return sum(int(row[0] or 0) for row in rows)


def _headline(items: list[AcademicPressureItem], low: int, high: int, horizon_days: int) -> str:
    if not items:
        return f"No active academic deadlines in the next {horizon_days} days."
    high_pressure = sum(1 for item in items if item.pressure_level in ("high", "overdue"))
    hours_low = round(low / 60)
    hours_high = round(high / 60)
    if high_pressure:
        return (
            f"{len(items)} academic obligations in the next {horizon_days} days; "
            f"{high_pressure} pressure points may need a recovery option."
        )
    return (
        f"{len(items)} academic obligations in the next {horizon_days} days; "
        f"estimated visible load is {hours_low}-{hours_high}h."
    )


def build_pressure_map(db: Session, horizon_days: int = 14) -> AcademicPressureMapResponse:
    uid = get_current_user_id()
    if uid is None:
        raise RuntimeError("academic_pressure: no current_user_id")

    horizon_days = _clamp_horizon(horizon_days)
    generated_at = now_utc()
    window_end = generated_at + timedelta(days=horizon_days)
    overdue_floor = generated_at - timedelta(days=14)

    user = db.query(User).filter(User.user_id == uid).first()
    deadlines = (
        db.query(Deadline)
        .filter(Deadline.user_id == uid)
        .filter(Deadline.voided_at.is_(None))
        .filter(Deadline.state.in_(("planned", "active", "missed")))
        .filter(Deadline.due_at_utc >= overdue_floor)
        .filter(Deadline.due_at_utc <= window_end)
        .order_by(Deadline.due_at_utc.asc())
        .all()
    )

    items: list[AcademicPressureItem] = []
    for deadline in deadlines:
        due_at = strip_tz(deadline.due_at_utc) or deadline.due_at_utc
        estimate = _estimate(deadline)
        days_until = (due_at - generated_at).total_seconds() / 86400
        trust = _trust_state(deadline)
        warnings: list[str] = []
        if trust != "verified_exact":
            warnings.append("reachable/imported does not prove coverage correctness")
        if days_until < 0:
            warnings.append("deadline is overdue; do not infer completion from silence")
        items.append(
            AcademicPressureItem(
                obligation_id=deadline.deadline_id,
                title=deadline.title,
                due_at_utc=due_at,
                source=deadline.external_source or "lyra_native",
                obligation_type=_classify_obligation(deadline.title),
                trust_state=trust,
                complexity_tier=_complexity_tier(deadline.title, deadline.category_hint),
                complexity_source="heuristic_v1",
                pressure_level=_pressure_level(due_at, generated_at),
                days_until_due=round(days_until, 1),
                estimate=estimate,
                warnings=warnings,
            )
        )

    low_total = sum(item.estimate.low_minutes for item in items)
    high_total = sum(item.estimate.high_minutes for item in items)
    calendar_busy, gcal_connected = _calendar_busy_minutes(uid, user, generated_at, window_end)
    planned_minutes = _planned_task_minutes(db, uid, generated_at, window_end)
    native_count = sum(1 for d in deadlines if not d.external_source)
    moodle_count = sum(1 for d in deadlines if d.external_source == "moodle_ics")

    warnings = [
        "Pressure Map should create clarity and agency, not panic.",
        "Estimates are ranges from visible academic structure, not calibrated personal predictions.",
        "No completion is inferred when a scheduled study block passes without user response.",
    ]
    if any(item.trust_state != "verified_exact" for item in items):
        warnings.append("Some imported items need coverage confirmation before plan generation.")
    if not gcal_connected:
        warnings.append("Google Calendar is not connected, so free-time mismatch is incomplete.")

    return AcademicPressureMapResponse(
        generated_at_utc=generated_at,
        horizon_days=horizon_days,
        headline=_headline(items, low_total, high_total, horizon_days),
        items=items,
        estimated_low_minutes=low_total,
        estimated_high_minutes=high_total,
        source_summary=AcademicSourceSummary(
            deadlines_total=len(deadlines),
            moodle_deadlines=moodle_count,
            native_deadlines=native_count,
            google_calendar_connected=gcal_connected,
            calendar_busy_minutes=calendar_busy,
            planned_lyra_minutes=planned_minutes,
        ),
        methodology=[
            "deadline/resource structure first",
            "complexity tier as one signal, never final-hour authority",
            "rounded uncertainty ranges instead of exact-hour claims",
            "personal timer traces will override priors after enough evidence",
            "Baseet-ready provider boundary: metadata and canonical links only",
            "clarity-and-agency copy rule: name pressure points with recovery options, not doom",
        ],
        warnings=warnings,
    )
