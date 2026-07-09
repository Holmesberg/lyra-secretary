"""Academic pressure map service.

V1 deliberately avoids new persistence. It reads existing deadlines,
planned LyraOS tasks, and read-only calendar context to produce a bounded,
transparent workload-pressure snapshot. It does not claim behavioral
personalization and does not feed clean learning paths.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil

from sqlalchemy.orm import Session

from app.core.kill_switches import (
    baseet_pressure_input_enabled,
    read_only_pressure_mode_enabled,
    recovery_nudges_enabled,
)
from app.db.models import Deadline, Task, TaskState, User
from app.db.scoping import get_current_user_id
from app.schemas.academic import (
    AcademicCapacityContext,
    AcademicComplexityTier,
    AcademicCompressionPoint,
    AcademicCoverageQuestion,
    AcademicPressureEstimate,
    AcademicPressureItem,
    AcademicPressureMapResponse,
    AcademicPressureLevel,
    AcademicRecoveryOption,
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

ACADEMIC_PRESSURE_TASK_CATEGORIES = {"academic", "study"}
ACADEMIC_SCHEDULE_TASK_TOKENS = {
    "class",
    "course",
    "lab",
    "labs",
    "lec",
    "lecture",
    "lectures",
    "practical",
    "section",
    "seminar",
    "tut",
    "tutorial",
    "tutorials",
}


@dataclass(frozen=True)
class _TypePrior:
    low: int
    high: int
    assumption: str


@dataclass(frozen=True)
class _ProviderBoundary:
    source: str
    source_class: str
    evidence_class: str
    provider_kind: str | None
    raw_authority_level: str
    redaction_status: str


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


def is_academic_pressure_task_category(category: str | None) -> bool:
    """True for LyraOS task categories that belong on the academic map.

    Governance distinction:
      - academic = institutional/prescheduled academic obligations
        (deadlines, lectures, tutorials, labs, classes).
      - study = user-owned self-study sessions.

    They share the same pressure surface, but their source labels and
    trust wording stay separate so provider-imported structure does not
    collapse into self-study behavior.
    """
    return (category or "").strip().lower() in ACADEMIC_PRESSURE_TASK_CATEGORIES


def _academic_pressure_task_kind(task: Task) -> str:
    """Return `academic` or `study` for pressure-map projection.

    Existing rows may predate the 2026-05-20 category boundary. If a
    stored `study` task is clearly a prescheduled lab/lecture/tutorial
    block, project it as academic on this surface without rewriting the
    historical task row.
    """
    category = (task.category or "").strip().lower()
    tokens = set(re.findall(r"[a-z0-9]+", (task.title or "").lower()))
    if category == "academic" or tokens & ACADEMIC_SCHEDULE_TASK_TOKENS:
        return "academic"
    return "study"


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


def _classify_task_obligation(task: Task) -> str:
    if _academic_pressure_task_kind(task) == "study":
        return "self_study"
    return _classify_obligation(task.title)


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


def _provider_kind(external_source: str | None) -> str | None:
    source = (external_source or "").strip().lower()
    if not source:
        return None
    if source.startswith("moodle"):
        return "moodle"
    if source.startswith("baseet"):
        return "baseet"
    if source.startswith("google"):
        return "calendar"
    return "external_provider"


def _deadline_boundary(deadline: Deadline) -> _ProviderBoundary:
    if deadline.external_source:
        return _ProviderBoundary(
            source="external_obligation",
            source_class="external",
            evidence_class="external_obligation",
            provider_kind=_provider_kind(deadline.external_source),
            raw_authority_level="provider_reachable",
            redaction_status="metadata_only",
        )
    return _ProviderBoundary(
        source="native_obligation",
        source_class="native",
        evidence_class="native_obligation",
        provider_kind="lyra",
        raw_authority_level="self_reported",
        redaction_status="not_provider_payload",
    )


def _task_boundary(kind: str) -> _ProviderBoundary:
    return _ProviderBoundary(
        source="lyra_self_study_task" if kind == "study" else "lyra_academic_task",
        source_class="lyra_task",
        evidence_class="scheduled_intention",
        provider_kind="lyra",
        raw_authority_level=(
            "user_planned" if kind == "study" else "scheduled_structure"
        ),
        redaction_status="not_provider_payload",
    )


def _trust_state(deadline: Deadline) -> AcademicTrustState:
    if deadline.external_source:
        # Imported provider entries are reachable/imported, but coverage
        # correctness is not guaranteed by provider metadata alone.
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
        assumptions.append("external obligation metadata; provider source remains canonical")
    else:
        assumptions.append("manually/native LyraOS deadline; coverage needs user confirmation")
    return AcademicPressureEstimate(
        low_minutes=low,
        high_minutes=max(high, low + 30),
        confidence="low",
        assumptions=assumptions,
    )


def _task_estimate(task: Task) -> AcademicPressureEstimate:
    planned = int(task.planned_duration_minutes or 0)
    if planned <= 0 and task.planned_start_utc and task.planned_end_utc:
        planned = max(
            0,
            int((task.planned_end_utc - task.planned_start_utc).total_seconds() / 60),
        )
    planned = max(planned, 5)
    kind = _academic_pressure_task_kind(task)
    if kind == "study":
        assumptions = [
            "self-study task scheduled by the user",
            "planned duration is visible intention, not completed work",
            "no passive/provider activity is used as execution truth",
        ]
        confidence = "medium"
    else:
        assumptions = [
            "prescheduled academic task in LyraOS",
            "planned duration is visible schedule structure",
            "coverage/source still needs confirmation before auto-plan generation",
        ]
        confidence = "low"
    return AcademicPressureEstimate(
        low_minutes=planned,
        high_minutes=planned,
        confidence=confidence,
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


def _planned_academic_task_rows(
    db: Session,
    user_id: int,
    start: datetime,
    end: datetime,
) -> list[Task]:
    return (
        db.query(Task)
        .filter(Task.user_id == user_id)
        .filter(Task.voided_at.is_(None))
        .filter(Task.is_anchor.is_(False))
        .filter(Task.state.in_([TaskState.PLANNED, TaskState.EXECUTING, TaskState.PAUSED]))
        .filter(Task.planned_start_utc < end)
        .filter(Task.planned_end_utc > start)
        .filter(Task.category.in_(tuple(ACADEMIC_PRESSURE_TASK_CATEGORIES)))
        .order_by(Task.planned_start_utc.asc())
        .all()
    )


def _headline(items: list[AcademicPressureItem], low: int, high: int, horizon_days: int) -> str:
    if not items:
        return f"No active academic obligations in the next {horizon_days} days."
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


def _pressure_summary(
    items: list[AcademicPressureItem],
    low: int,
    high: int,
    planned_minutes: int,
    calendar_busy: int,
    gcal_connected: bool,
) -> str:
    if not items:
        return "No visible academic pressure in this window."
    high_pressure = sum(1 for item in items if item.pressure_level in ("high", "overdue"))
    uncertain = sum(1 for item in items if item.trust_state != "verified_exact")
    hours_low = round(low / 60)
    hours_high = round(high / 60)
    load_phrase = f"{hours_low}-{hours_high}h of visible academic load"
    if high_pressure and uncertain:
        return (
            f"This week looks compressed: {high_pressure} pressure points, "
            f"{uncertain} coverage questions, and {load_phrase}."
        )
    if high_pressure:
        return f"This week looks compressed: {high_pressure} pressure points and {load_phrase}."
    if planned_minutes or calendar_busy:
        source = "calendar and LyraOS tasks" if gcal_connected else "LyraOS tasks"
        return f"{load_phrase} sits beside known scheduled load from {source}."
    return f"{load_phrase}; confirm coverage before turning it into a plan."


def _clustered_due_items(items: list[AcademicPressureItem]) -> list[AcademicPressureItem]:
    clusters: list[AcademicPressureItem] = []
    sorted_items = sorted(items, key=lambda item: item.due_at_utc)
    for idx, item in enumerate(sorted_items):
        neighbors = sorted_items[max(0, idx - 1): idx] + sorted_items[idx + 1: idx + 2]
        if any(abs((item.due_at_utc - other.due_at_utc).total_seconds()) <= 48 * 3600 for other in neighbors):
            clusters.append(item)
    return clusters


def _compression_points(
    items: list[AcademicPressureItem],
    low: int,
    high: int,
    planned_minutes: int,
    calendar_busy: int,
    gcal_connected: bool,
) -> list[AcademicCompressionPoint]:
    points: list[AcademicCompressionPoint] = []
    overdue = [item for item in items if item.pressure_level == "overdue"]
    high_pressure = [item for item in items if item.pressure_level == "high"]
    uncertain = [item for item in items if item.trust_state != "verified_exact"]
    clustered = _clustered_due_items(items)

    if overdue:
        points.append(
            AcademicCompressionPoint(
                kind="overdue",
                title="Overdue academic pressure",
                detail=(
                    f"{len(overdue)} item(s) are overdue. LyraOS does not infer completion "
                    "from silence; confirm, reschedule, or clear them."
                ),
                obligation_ids=[item.obligation_id for item in overdue],
            )
        )
    if high_pressure:
        points.append(
            AcademicCompressionPoint(
                kind="due_soon",
                title="Due-soon pressure",
                detail=f"{len(high_pressure)} item(s) are due within 3 days and may need recovery blocks.",
                obligation_ids=[item.obligation_id for item in high_pressure],
            )
        )
    if len(clustered) >= 2:
        points.append(
            AcademicCompressionPoint(
                kind="cluster",
                title="Deadline cluster",
                detail=f"{len(clustered)} item(s) land within 48-hour clusters.",
                obligation_ids=[item.obligation_id for item in clustered],
            )
        )
    if uncertain:
        points.append(
            AcademicCompressionPoint(
                kind="uncertain_coverage",
                title="Coverage still needs confirmation",
                detail=(
                    f"{len(uncertain)} item(s) are imported or inferred enough to plan around, "
                    "but not enough to treat as exact coverage truth."
                ),
                obligation_ids=[item.obligation_id for item in uncertain],
            )
        )
    if items and (planned_minutes or calendar_busy):
        known_load = planned_minutes + calendar_busy
        total_low = low + known_load
        total_high = high + known_load
        caveat = "Google Calendar is connected." if gcal_connected else "Calendar coverage is incomplete."
        points.append(
            AcademicCompressionPoint(
                kind="known_load",
                title="Known scheduled load",
                detail=(
                    f"Known busy/planned load plus academic ranges is "
                    f"{round(total_low / 60)}-{round(total_high / 60)}h in this window. {caveat}"
                ),
                obligation_ids=[],
            )
        )
    return points[:5]


def _coverage_questions(items: list[AcademicPressureItem]) -> list[AcademicCoverageQuestion]:
    questions: list[AcademicCoverageQuestion] = []
    for item in items:
        if item.trust_state == "verified_exact":
            continue
        questions.append(
            AcademicCoverageQuestion(
                obligation_id=item.obligation_id,
                question=f"What exactly does {item.title} cover?",
                reason=(
                    "Coverage must be confirmed by source metadata, moderator answer, "
                    "3-5 student confirmations, or this user's correction before strong planning."
                ),
                trust_state=item.trust_state,
            )
        )
    return questions[:5]


def _recovery_options(
    items: list[AcademicPressureItem],
    coverage_questions: list[AcademicCoverageQuestion],
    gcal_connected: bool,
) -> list[AcademicRecoveryOption]:
    if not recovery_nudges_enabled():
        return []

    if not items:
        return [
            AcademicRecoveryOption(
                action="clear_or_ignore",
                label="Keep the window clean",
                detail="No active academic pressure is visible here. Add or import deadlines, lectures, labs, tutorials, or study blocks if something is missing.",
                obligation_ids=[],
            )
        ]

    options: list[AcademicRecoveryOption] = []
    high_or_overdue = [item for item in items if item.pressure_level in ("high", "overdue")]
    largest = sorted(items, key=lambda item: item.estimate.high_minutes, reverse=True)[:2]
    if coverage_questions:
        options.append(
            AcademicRecoveryOption(
                action="confirm_coverage",
                label="Confirm coverage",
                detail="Lock what these deadlines actually cover before LyraOS turns them into study blocks.",
                obligation_ids=[q.obligation_id for q in coverage_questions],
            )
        )
    if high_or_overdue:
        options.append(
            AcademicRecoveryOption(
                action="create_plan",
                label="Create a recovery plan",
                detail="Turn the due-soon pressure points into editable study blocks.",
                obligation_ids=[item.obligation_id for item in high_or_overdue],
            )
        )
    if largest:
        options.append(
            AcademicRecoveryOption(
                action="split_into_blocks",
                label="Split the biggest work",
                detail="Break the largest visible obligations into smaller blocks before they compress the week.",
                obligation_ids=[item.obligation_id for item in largest],
            )
        )
    if not gcal_connected:
        options.append(
            AcademicRecoveryOption(
                action="review_calendar",
                label="Review schedule context",
                detail="Calendar is not connected, so LyraOS can show academic load but not true free-time mismatch.",
                obligation_ids=[],
            )
        )
    return options[:4]


def _capacity_context(
    low: int,
    high: int,
    planned_minutes: int,
    calendar_busy: int,
    gcal_connected: bool,
) -> AcademicCapacityContext:
    if gcal_connected:
        caveat = (
            "Known busy time comes from connected Google Calendar and planned LyraOS tasks; "
            "unscheduled real-life constraints may still be missing."
        )
    else:
        caveat = (
            "Calendar is not connected, so LyraOS shows visible academic pressure and planned LyraOS load, "
            "not true free time."
        )
    return AcademicCapacityContext(
        known_busy_minutes=calendar_busy,
        planned_lyra_minutes=planned_minutes,
        estimated_academic_low_minutes=low,
        estimated_academic_high_minutes=high,
        google_calendar_connected=gcal_connected,
        caveat=caveat,
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
    if not baseet_pressure_input_enabled():
        deadlines = [
            deadline
            for deadline in deadlines
            if _provider_kind(deadline.external_source) != "baseet"
        ]

    items: list[AcademicPressureItem] = []
    for deadline in deadlines:
        due_at = strip_tz(deadline.due_at_utc) or deadline.due_at_utc
        boundary = _deadline_boundary(deadline)
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
                source=boundary.source,
                source_class=boundary.source_class,
                evidence_class=boundary.evidence_class,
                provider_kind=boundary.provider_kind,
                raw_authority_level=boundary.raw_authority_level,
                redaction_status=boundary.redaction_status,
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

    academic_tasks = _planned_academic_task_rows(db, uid, generated_at, window_end)
    for task in academic_tasks:
        scheduled_at = strip_tz(task.planned_start_utc) or task.planned_start_utc
        kind = _academic_pressure_task_kind(task)
        boundary = _task_boundary(kind)
        estimate = _task_estimate(task)
        days_until = (scheduled_at - generated_at).total_seconds() / 86400
        trust: AcademicTrustState = (
            "verified_exact" if kind == "study" else "requires_user_confirmation"
        )
        warnings = [
            "scheduled task is intention, not completion evidence",
        ]
        if kind == "academic":
            warnings.append("academic scheduled block needs provider/user coverage confirmation")
        items.append(
            AcademicPressureItem(
                obligation_id=task.task_id,
                title=task.title,
                due_at_utc=scheduled_at,
                source=boundary.source,
                source_class=boundary.source_class,
                evidence_class=boundary.evidence_class,
                provider_kind=boundary.provider_kind,
                raw_authority_level=boundary.raw_authority_level,
                redaction_status=boundary.redaction_status,
                obligation_type=_classify_task_obligation(task),
                trust_state=trust,
                complexity_tier=_complexity_tier(task.title, task.category),
                complexity_source="task_category_v1",
                pressure_level=_pressure_level(scheduled_at, generated_at),
                days_until_due=round(days_until, 1),
                estimate=estimate,
                warnings=warnings,
            )
        )

    items.sort(key=lambda item: item.due_at_utc)

    low_total = sum(item.estimate.low_minutes for item in items)
    high_total = sum(item.estimate.high_minutes for item in items)
    calendar_busy, gcal_connected = _calendar_busy_minutes(uid, user, generated_at, window_end)
    planned_minutes = _planned_task_minutes(db, uid, generated_at, window_end)
    native_count = sum(1 for d in deadlines if not d.external_source)
    external_count = sum(1 for d in deadlines if d.external_source)
    academic_task_minutes = sum(
        int(t.planned_duration_minutes or 0)
        for t in academic_tasks
        if _academic_pressure_task_kind(t) == "academic"
    )
    study_task_minutes = sum(
        int(t.planned_duration_minutes or 0)
        for t in academic_tasks
        if _academic_pressure_task_kind(t) == "study"
    )

    warnings = [
        "Pressure Map should create clarity and agency, not panic.",
        "Estimates are ranges from visible academic structure, not calibrated personal predictions.",
        "No completion is inferred when a scheduled study block passes without user response.",
    ]
    if any(item.trust_state != "verified_exact" for item in items):
        warnings.append("Some imported items need coverage confirmation before plan generation.")
    if not gcal_connected:
        warnings.append("Google Calendar is not connected, so free-time mismatch is incomplete.")
    if read_only_pressure_mode_enabled():
        warnings.append(
            "Read-only pressure safe mode is active; recovery nudges and mutations are disabled."
        )
    elif not recovery_nudges_enabled():
        warnings.append("Recovery nudges are disabled by operator safety switch.")
    if not baseet_pressure_input_enabled():
        warnings.append("Baseet pressure inputs are disabled by operator safety switch.")

    coverage_questions = _coverage_questions(items)
    return AcademicPressureMapResponse(
        generated_at_utc=generated_at,
        horizon_days=horizon_days,
        headline=_headline(items, low_total, high_total, horizon_days),
        pressure_summary=_pressure_summary(
            items,
            low_total,
            high_total,
            planned_minutes,
            calendar_busy,
            gcal_connected,
        ),
        items=items,
        compression_points=_compression_points(
            items,
            low_total,
            high_total,
            planned_minutes,
            calendar_busy,
            gcal_connected,
        ),
        recovery_options=_recovery_options(items, coverage_questions, gcal_connected),
        coverage_questions=coverage_questions,
        capacity_context=_capacity_context(
            low_total,
            high_total,
            planned_minutes,
            calendar_busy,
            gcal_connected,
        ),
        estimated_low_minutes=low_total,
        estimated_high_minutes=high_total,
        source_summary=AcademicSourceSummary(
            deadlines_total=len(deadlines),
            external_obligation_count=external_count,
            native_obligation_count=native_count,
            academic_task_count=sum(
                1 for t in academic_tasks
                if _academic_pressure_task_kind(t) == "academic"
            ),
            study_task_count=sum(
                1 for t in academic_tasks
                if _academic_pressure_task_kind(t) == "study"
            ),
            academic_task_minutes=academic_task_minutes,
            study_task_minutes=study_task_minutes,
            google_calendar_connected=gcal_connected,
            calendar_busy_minutes=calendar_busy,
            planned_lyra_minutes=planned_minutes,
        ),
        methodology=[
            "deadline/resource structure first",
            "complexity tier as one signal, never final-hour authority",
            "rounded uncertainty ranges instead of exact-hour claims",
            "personal timer traces will override priors after enough evidence",
            "provider-boundary ready: metadata and canonical links only",
            "clarity-and-agency copy rule: name pressure points with recovery options, not doom",
            "trust-state copy is governed by docs/academic_pressure_map_contract.md",
            "validity threats and research integrity are checked before calibration admission",
            "pre-scale kill switches may suppress Baseet inputs or recovery nudges",
        ],
        warnings=warnings,
    )
