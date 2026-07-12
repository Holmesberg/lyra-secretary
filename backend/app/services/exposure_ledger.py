"""Exposure Ledger v0 service.

The ledger is a measurement-validity firewall: it decides whether a behavior
row may be interpreted as baseline under the current exposure horizon policy.
It does not infer comprehension, intent, or causality.
"""
from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, Optional
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import (
    CalibrationNudgeEvent,
    ExposureDecisionEvent,
    ExposurePolicyEffectLog,
    ExposureRenderEvent,
    PausePredictionLog,
    ReflectionViewLog,
    ResumePredictionLog,
    SuppressionEvent,
    Task,
    TaskExecutionCorrection,
)
from app.services.exposure_policy import (
    DEFAULT_HORIZON_POLICY_VERSION,
    SIGNAL_TARGETS,
    affected_categories_for_target,
    load_horizon_policy,
)
from app.utils.time_utils import strip_tz

ExposureState = Literal["NONE", "EXPOSED", "INTERVENTION", "UNKNOWN"]
ExposureTerminalState = Literal[
    "rendered",
    "suppressed",
    "queued_without_render",
    "non_actionable_without_render",
    "actionable_missing_render",
]

NON_ACTIONABLE_MISSING_RENDER_STATUSES = frozenset(
    {"suppressed", "delayed", "failed", "queued", "reserved"}
)

UNCLAIMED_DECISION_STATUSES = frozenset({"reserved"})

LEGACY_REFLECTION_CATEGORY = {
    "micro_mirror": "behavioral_insight",
    "calibration_nudge": "behavioral_insight",
    "creation_nudge": "scheduling_suggestion",
    "pause_prediction": "predictive_alert",
    "resume_prediction": "predictive_alert",
    "archetype_proximity": "meta_inference",
}


@dataclass(frozen=True)
class ExposureContaminationResult:
    state: ExposureState
    exposure_ids: list[str]
    exposure_categories: list[str]
    signal_target: str
    checked_window_start: Optional[datetime]
    checked_window_end: Optional[datetime]
    horizon_policy_version: str
    unknown_reason: Optional[str]
    policy_effect_reason: str

    @property
    def baseline_clean(self) -> bool:
        """True only when exposure context was evaluated and returned NONE."""
        return self.state == "NONE"


@dataclass(frozen=True)
class ExposureTerminalClassification:
    state: ExposureTerminalState
    has_terminal_event: bool
    is_actionable_missing_render: bool


def classify_exposure_terminal_state(
    *,
    decision_status: str | None,
    has_render: bool,
    has_suppression: bool,
) -> ExposureTerminalClassification:
    """Classify decision/render/suppression evidence without changing it.

    This is a diagnostics primitive only. It does not decide exposure
    contamination, infer attention, or authorize a user-facing claim.
    """
    if has_render:
        return ExposureTerminalClassification(
            state="rendered",
            has_terminal_event=True,
            is_actionable_missing_render=False,
        )
    if has_suppression or decision_status == "suppressed":
        return ExposureTerminalClassification(
            state="suppressed",
            has_terminal_event=has_suppression,
            is_actionable_missing_render=False,
        )
    if decision_status == "queued":
        return ExposureTerminalClassification(
            state="queued_without_render",
            has_terminal_event=False,
            is_actionable_missing_render=False,
        )
    if decision_status in NON_ACTIONABLE_MISSING_RENDER_STATUSES:
        return ExposureTerminalClassification(
            state="non_actionable_without_render",
            has_terminal_event=False,
            is_actionable_missing_render=False,
        )
    return ExposureTerminalClassification(
        state="actionable_missing_render",
        has_terminal_event=False,
        is_actionable_missing_render=True,
    )


def content_hash(content_snapshot: str) -> str:
    """Deterministic hash of the exact rendered stimulus."""
    return hashlib.sha256(content_snapshot.encode("utf-8")).hexdigest()


def record_decision(
    db: Session,
    *,
    user_id: int,
    eligible_at: datetime,
    decision_status: str,
    exposure_category: str,
    task_id: Optional[str] = None,
    content_template_id: Optional[str] = None,
    initiative: str = "unknown",
    trigger_source: str = "unknown",
    generating_model: Optional[str] = None,
    generating_version: Optional[str] = None,
    prompt_hash: Optional[str] = None,
    data_snapshot_hash: Optional[str] = None,
    randomization_arm: str = "none",
    randomization_policy_version: Optional[str] = None,
    delivered_at: Optional[datetime] = None,
    exposure_id: Optional[str] = None,
) -> ExposureDecisionEvent:
    """Create an append-only exposure decision row inside the caller transaction."""
    row = ExposureDecisionEvent(
        exposure_id=exposure_id or str(uuid4()),
        user_id=user_id,
        task_id=task_id,
        eligible_at=strip_tz(eligible_at),
        decision_status=decision_status,
        initiative=initiative,
        exposure_category=exposure_category,
        content_template_id=content_template_id,
        trigger_source=trigger_source,
        generating_model=generating_model,
        generating_version=generating_version,
        prompt_hash=prompt_hash,
        data_snapshot_hash=data_snapshot_hash,
        randomization_arm=randomization_arm,
        randomization_policy_version=randomization_policy_version,
        delivered_at=strip_tz(delivered_at) if delivered_at is not None else None,
    )
    db.add(row)
    db.flush()
    return row


def record_render(
    db: Session,
    *,
    exposure_id: str,
    rendered_at: datetime,
    surface: str,
    channel: str,
    content_snapshot: str,
    render_policy_version: str,
    interruptiveness: str,
    salience_level: str,
    render_id: Optional[str] = None,
    rendered_content_hash: Optional[str] = None,
) -> ExposureRenderEvent:
    """Create an append-only exact-stimulus render row."""
    row = ExposureRenderEvent(
        render_id=render_id or str(uuid4()),
        exposure_id=exposure_id,
        rendered_at=strip_tz(rendered_at),
        surface=surface,
        channel=channel,
        content_hash=rendered_content_hash or content_hash(content_snapshot),
        content_snapshot=content_snapshot,
        render_policy_version=render_policy_version,
        interruptiveness=interruptiveness,
        salience_level=salience_level,
    )
    db.add(row)
    db.flush()
    return row


def record_suppression(
    db: Session,
    *,
    exposure_id: str,
    suppressed_at: datetime,
    suppression_reason: str,
    would_have_rendered_template_id: Optional[str] = None,
    generating_confidence: Optional[float] = None,
    suppression_id: Optional[str] = None,
) -> SuppressionEvent:
    """Create an append-only suppression row."""
    row = SuppressionEvent(
        suppression_id=suppression_id or str(uuid4()),
        exposure_id=exposure_id,
        suppressed_at=strip_tz(suppressed_at),
        suppression_reason=suppression_reason,
        would_have_rendered_template_id=would_have_rendered_template_id,
        generating_confidence=generating_confidence,
    )
    db.add(row)
    db.flush()
    return row


def is_exposed(
    db: Session,
    *,
    user_id: int,
    event_time: datetime,
    signal_target: str,
    horizon_policy_version: str = DEFAULT_HORIZON_POLICY_VERSION,
) -> ExposureContaminationResult:
    """Evaluate whether a behavioral measurement is baseline-clean.

    UNKNOWN fails closed. It is returned for unsupported signal targets,
    unavailable policy config, ledger query failures, or incomplete
    decision/render/suppression chains.
    """
    event_time = strip_tz(event_time)
    if event_time is None:
        return _unknown(
            signal_target=signal_target,
            horizon_policy_version=horizon_policy_version,
            reason="missing_event_time",
            effect="event_time_unavailable",
        )

    try:
        policy = load_horizon_policy(horizon_policy_version)
        categories = affected_categories_for_target(policy, signal_target)
    except Exception:
        return _unknown(
            signal_target=signal_target,
            horizon_policy_version=horizon_policy_version,
            reason="policy_unavailable",
            effect="horizon_policy_unavailable",
            end=event_time,
        )

    if not categories:
        return _unknown(
            signal_target=signal_target,
            horizon_policy_version=horizon_policy_version,
            reason="unsupported_or_unmeasured_signal_target",
            effect="signal_target_not_gated_by_policy",
            end=event_time,
        )

    checked_start = event_time - timedelta(minutes=max(categories.values()))

    try:
        v0_result = _check_v0_events(
            db,
            user_id=user_id,
            event_time=event_time,
            signal_target=signal_target,
            categories=categories,
            horizon_policy_version=horizon_policy_version,
            checked_start=checked_start,
        )
        if v0_result.state != "NONE":
            return v0_result

        legacy_result = _check_legacy_events(
            db,
            user_id=user_id,
            event_time=event_time,
            signal_target=signal_target,
            categories=categories,
            horizon_policy_version=horizon_policy_version,
            checked_start=checked_start,
        )
        if legacy_result.state != "NONE":
            return legacy_result
    except SQLAlchemyError:
        return _unknown(
            signal_target=signal_target,
            horizon_policy_version=horizon_policy_version,
            reason="ledger_unavailable",
            effect="ledger_query_failed",
            start=checked_start,
            end=event_time,
        )

    return ExposureContaminationResult(
        state="NONE",
        exposure_ids=[],
        exposure_categories=[],
        signal_target=signal_target,
        checked_window_start=checked_start,
        checked_window_end=event_time,
        horizon_policy_version=horizon_policy_version,
        unknown_reason=None,
        policy_effect_reason="no_relevant_exposure_within_policy_horizon",
    )


def task_signal_time(task: Task, signal_target: str) -> Optional[datetime]:
    """Return the timestamp to use when gating a task for a signal target."""
    if signal_target in {"planning_estimate", "deadline_behavior"}:
        return strip_tz(task.created_at) or strip_tz(task.planned_start_utc)
    if signal_target == "reflection_self_report":
        return strip_tz(task.executed_end_utc) or strip_tz(task.planned_end_utc)
    if signal_target in {
        "duration_behavior",
        "readiness_self_report",
        "pause_behavior",
    }:
        return strip_tz(task.executed_start_utc) or strip_tz(task.planned_start_utc)
    return None


def exposure_results_for_task(
    db: Session,
    *,
    task: Task,
    signal_targets: list[str],
    horizon_policy_version: str = DEFAULT_HORIZON_POLICY_VERSION,
) -> list[ExposureContaminationResult]:
    """Evaluate exposure state for each requested task signal target."""
    results: list[ExposureContaminationResult] = []
    for signal_target in signal_targets:
        event_time = task_signal_time(task, signal_target)
        if event_time is None:
            results.append(
                _unknown(
                    signal_target=signal_target,
                    horizon_policy_version=horizon_policy_version,
                    reason="missing_signal_event_time",
                    effect="task_signal_time_unavailable",
                )
            )
            continue
        results.append(
            is_exposed(
                db,
                user_id=task.user_id,
                event_time=event_time,
                signal_target=signal_target,
                horizon_policy_version=horizon_policy_version,
            )
        )
    return results


def baseline_clean_task(
    db: Session,
    *,
    task: Task,
    signal_targets: list[str],
    horizon_policy_version: str = DEFAULT_HORIZON_POLICY_VERSION,
) -> bool:
    """Return True only when every requested exposure gate returns NONE.

    Retroactive execution corrections are Layer D repair data. Any task with a
    correction row is excluded from clean baselines even when its exposure
    context is otherwise clean.
    """
    has_execution_correction = (
        db.query(TaskExecutionCorrection.correction_id)
        .filter(TaskExecutionCorrection.task_id == task.task_id)
        .first()
        is not None
    )
    if has_execution_correction:
        return False
    return all(
        result.state == "NONE"
        for result in exposure_results_for_task(
            db,
            task=task,
            signal_targets=signal_targets,
            horizon_policy_version=horizon_policy_version,
        )
    )


def baseline_clean_task_ids(
    db: Session,
    *,
    tasks: list[Task],
    signal_targets: list[str],
    horizon_policy_version: str = DEFAULT_HORIZON_POLICY_VERSION,
) -> set[str]:
    """Bulk equivalent of baseline_clean_task for task lists.

    User-facing analytics often filter dozens of candidate tasks at once. The
    single-row helper intentionally reads clearly, but calling it in a loop
    creates N x target x legacy-table queries. This helper keeps the same
    fail-closed semantics while prefetching the exposure rows for the full
    candidate window.
    """
    tasks = [task for task in tasks if task.task_id is not None]
    if not tasks:
        return set()
    if not signal_targets:
        return {task.task_id for task in tasks}

    clean_ids = {task.task_id for task in tasks}

    corrected_ids = {
        row[0]
        for row in (
            db.query(TaskExecutionCorrection.task_id)
            .filter(TaskExecutionCorrection.task_id.in_(clean_ids))
            .all()
        )
    }
    clean_ids -= corrected_ids
    if not clean_ids:
        return set()

    try:
        policy = load_horizon_policy(horizon_policy_version)
        categories_by_target = {
            target: affected_categories_for_target(policy, target)
            for target in signal_targets
        }
    except Exception:
        return set()
    if any(not categories for categories in categories_by_target.values()):
        return set()

    checks: list[tuple[str, int, str, datetime, dict[str, int]]] = []
    for task in tasks:
        if task.task_id not in clean_ids:
            continue
        for signal_target, categories in categories_by_target.items():
            event_time = task_signal_time(task, signal_target)
            if event_time is None:
                clean_ids.discard(task.task_id)
                break
            checks.append(
                (
                    task.task_id,
                    task.user_id,
                    signal_target,
                    strip_tz(event_time),
                    categories,
                )
            )

    if not checks:
        return clean_ids

    min_start = min(
        event_time - timedelta(minutes=max(categories.values()))
        for _, _, _, event_time, categories in checks
    )
    max_end = max(event_time for _, _, _, event_time, _ in checks)
    user_ids = {user_id for _, user_id, _, _, _ in checks}
    exposure_categories = {
        category
        for categories in categories_by_target.values()
        for category in categories
    }

    decisions = (
        db.query(ExposureDecisionEvent)
        .filter(
            ExposureDecisionEvent.user_id.in_(user_ids),
            ExposureDecisionEvent.eligible_at >= min_start,
            ExposureDecisionEvent.eligible_at <= max_end,
            ExposureDecisionEvent.exposure_category.in_(list(exposure_categories)),
        )
        .all()
    )
    decisions_by_user: dict[int, list[ExposureDecisionEvent]] = defaultdict(list)
    decision_ids = [decision.exposure_id for decision in decisions]
    for decision in decisions:
        decisions_by_user[decision.user_id].append(decision)

    renders_by_exposure: dict[str, list[datetime]] = defaultdict(list)
    suppression_ids: set[str] = set()
    if decision_ids:
        for exposure_id, rendered_at in (
            db.query(ExposureRenderEvent.exposure_id, ExposureRenderEvent.rendered_at)
            .filter(
                ExposureRenderEvent.exposure_id.in_(decision_ids),
                ExposureRenderEvent.rendered_at >= min_start,
                ExposureRenderEvent.rendered_at <= max_end,
            )
            .all()
        ):
            renders_by_exposure[exposure_id].append(strip_tz(rendered_at))

        suppression_ids = {
            row[0]
            for row in (
                db.query(SuppressionEvent.exposure_id)
                .filter(SuppressionEvent.exposure_id.in_(decision_ids))
                .all()
            )
        }

    reflection_types = [
        reflection_type
        for reflection_type, category in LEGACY_REFLECTION_CATEGORY.items()
        if category in exposure_categories
    ]
    reflections_by_user: dict[int, list[ReflectionViewLog]] = defaultdict(list)
    if reflection_types:
        reflections = (
            db.query(ReflectionViewLog)
            .filter(
                ReflectionViewLog.user_id.in_(user_ids),
                ReflectionViewLog.event_class == "impression",
                ReflectionViewLog.reflection_type.in_(reflection_types),
                ReflectionViewLog.fired_at >= min_start,
                ReflectionViewLog.fired_at <= max_end,
            )
            .all()
        )
        for reflection in reflections:
            reflections_by_user[reflection.user_id].append(reflection)

    calibrations_by_user: dict[int, list[CalibrationNudgeEvent]] = defaultdict(list)
    if {"scheduling_suggestion", "behavioral_insight"} & exposure_categories:
        calibrations = (
            db.query(CalibrationNudgeEvent)
            .filter(
                CalibrationNudgeEvent.user_id.in_(user_ids),
                CalibrationNudgeEvent.voided_at.is_(None),
                CalibrationNudgeEvent.decided_at >= min_start,
                CalibrationNudgeEvent.decided_at <= max_end,
            )
            .all()
        )
        for calibration in calibrations:
            calibrations_by_user[calibration.user_id].append(calibration)

    pauses_by_user: dict[int, list[PausePredictionLog]] = defaultdict(list)
    resumes_by_user: dict[int, list[ResumePredictionLog]] = defaultdict(list)
    if "predictive_alert" in exposure_categories:
        pauses = (
            db.query(PausePredictionLog)
            .filter(
                PausePredictionLog.user_id.in_(user_ids),
                PausePredictionLog.fired_at >= min_start,
                PausePredictionLog.fired_at <= max_end,
            )
            .all()
        )
        resumes = (
            db.query(ResumePredictionLog)
            .filter(
                ResumePredictionLog.user_id.in_(user_ids),
                ResumePredictionLog.fired_at >= min_start,
                ResumePredictionLog.fired_at <= max_end,
            )
            .all()
        )
        for pause in pauses:
            pauses_by_user[pause.user_id].append(pause)
        for resume in resumes:
            resumes_by_user[resume.user_id].append(resume)

    for task_id, user_id, signal_target, event_time, categories in checks:
        if task_id not in clean_ids:
            continue
        if _bulk_v0_state_dirty(
            decisions_by_user[user_id],
            renders_by_exposure,
            suppression_ids,
            event_time=event_time,
            signal_target=signal_target,
            categories=categories,
        ):
            clean_ids.discard(task_id)
            continue
        if _bulk_legacy_state_dirty(
            user_id=user_id,
            event_time=event_time,
            categories=categories,
            reflections=reflections_by_user[user_id],
            calibrations=calibrations_by_user[user_id],
            pauses=pauses_by_user[user_id],
            resumes=resumes_by_user[user_id],
        ):
            clean_ids.discard(task_id)

    return clean_ids


def _bulk_v0_state_dirty(
    decisions: list[ExposureDecisionEvent],
    renders_by_exposure: dict[str, list[datetime]],
    suppression_ids: set[str],
    *,
    event_time: datetime,
    signal_target: str,
    categories: dict[str, int],
) -> bool:
    for decision in decisions:
        if decision.decision_status in UNCLAIMED_DECISION_STATUSES:
            continue
        if decision.exposure_category not in categories:
            continue
        horizon = categories[decision.exposure_category]
        window_start = event_time - timedelta(minutes=horizon)
        eligible_at = strip_tz(decision.eligible_at)
        if eligible_at < window_start or eligible_at > event_time:
            continue

        if any(
            window_start <= rendered_at <= event_time
            for rendered_at in renders_by_exposure.get(decision.exposure_id, [])
        ):
            return True
        if decision.exposure_id in suppression_ids:
            continue
        return True
    return False


def _bulk_legacy_state_dirty(
    *,
    user_id: int,
    event_time: datetime,
    categories: dict[str, int],
    reflections: list[ReflectionViewLog],
    calibrations: list[CalibrationNudgeEvent],
    pauses: list[PausePredictionLog],
    resumes: list[ResumePredictionLog],
) -> bool:
    for reflection in reflections:
        category = LEGACY_REFLECTION_CATEGORY.get(
            reflection.reflection_type, "behavioral_insight"
        )
        if _within_category_horizon(
            reflection.fired_at, event_time, category, categories
        ):
            return True

    for calibration in calibrations:
        if _within_category_horizon(
            calibration.decided_at, event_time, "scheduling_suggestion", categories
        ) or _within_category_horizon(
            calibration.decided_at, event_time, "behavioral_insight", categories
        ):
            return True

    if "predictive_alert" in categories:
        for pause in pauses:
            if _within_category_horizon(
                pause.fired_at, event_time, "predictive_alert", categories
            ):
                return True
        for resume in resumes:
            if _within_category_horizon(
                resume.fired_at, event_time, "predictive_alert", categories
            ):
                return True

    return False


def record_policy_effect_snapshot(
    db: Session,
    *,
    user_id: int,
    tasks: list[Task],
    signal_targets: list[str],
    window_start: datetime,
    window_end: datetime,
    horizon_policy_version: str = DEFAULT_HORIZON_POLICY_VERSION,
) -> list[ExposurePolicyEffectLog]:
    """Persist a diagnostic snapshot of gate behavior for operator review.

    This is meta-instrumentation about the exposure policy, not behavioral
    learning data. It intentionally aggregates counts instead of storing per-row
    behavioral details.
    """
    rows: list[ExposurePolicyEffectLog] = []
    for signal_target in signal_targets:
        results = [
            result
            for task in tasks
            for result in exposure_results_for_task(
                db,
                task=task,
                signal_targets=[signal_target],
                horizon_policy_version=horizon_policy_version,
            )
        ]
        total = len(results)
        state_counts = Counter(result.state for result in results)
        ledger_incomplete = sum(
            1 for result in results if result.unknown_reason == "ledger_incomplete"
        )
        row = ExposurePolicyEffectLog(
            user_id=user_id,
            policy_version=horizon_policy_version,
            exposure_category="all",
            signal_target=signal_target,
            state_distribution_counts=dict(sorted(state_counts.items())),
            unknown_rate=(state_counts.get("UNKNOWN", 0) / total) if total else 0.0,
            ledger_incomplete_rate=(ledger_incomplete / total) if total else 0.0,
            sample_count=total,
            window_start=strip_tz(window_start),
            window_end=strip_tz(window_end),
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def _check_v0_events(
    db: Session,
    *,
    user_id: int,
    event_time: datetime,
    signal_target: str,
    categories: dict[str, int],
    horizon_policy_version: str,
    checked_start: datetime,
) -> ExposureContaminationResult:
    decisions = (
        db.query(ExposureDecisionEvent)
        .filter(
            ExposureDecisionEvent.user_id == user_id,
            ExposureDecisionEvent.eligible_at >= checked_start,
            ExposureDecisionEvent.eligible_at <= event_time,
            ExposureDecisionEvent.exposure_category.in_(list(categories)),
        )
        .all()
    )

    suppression_only = False
    for decision in decisions:
        if decision.decision_status in UNCLAIMED_DECISION_STATUSES:
            continue
        horizon = categories[decision.exposure_category]
        window_start = event_time - timedelta(minutes=horizon)
        if decision.eligible_at < window_start:
            continue

        renders = (
            db.query(ExposureRenderEvent)
            .filter(
                ExposureRenderEvent.exposure_id == decision.exposure_id,
                ExposureRenderEvent.rendered_at >= window_start,
                ExposureRenderEvent.rendered_at <= event_time,
            )
            .all()
        )
        if renders:
            return _exposed(
                state="EXPOSED",
                exposure_ids=[decision.exposure_id],
                exposure_categories=[decision.exposure_category],
                signal_target=signal_target,
                horizon_policy_version=horizon_policy_version,
                start=checked_start,
                end=event_time,
                effect="render_event_in_policy_horizon_attention_unconfirmed",
            )

        suppressions = (
            db.query(SuppressionEvent)
            .filter(SuppressionEvent.exposure_id == decision.exposure_id)
            .all()
        )
        if suppressions:
            suppression_only = True
            continue

        return _unknown(
            signal_target=signal_target,
            horizon_policy_version=horizon_policy_version,
            reason="ledger_incomplete",
            effect="decision_without_render_or_suppression",
            start=checked_start,
            end=event_time,
        )

    return ExposureContaminationResult(
        state="NONE",
        exposure_ids=[],
        exposure_categories=[],
        signal_target=signal_target,
        checked_window_start=checked_start,
        checked_window_end=event_time,
        horizon_policy_version=horizon_policy_version,
        unknown_reason=None,
        policy_effect_reason=(
            "only_suppressed_relevant_decisions"
            if suppression_only
            else "no_v0_exposure_decision_in_policy_horizon"
        ),
    )


def _check_legacy_events(
    db: Session,
    *,
    user_id: int,
    event_time: datetime,
    signal_target: str,
    categories: dict[str, int],
    horizon_policy_version: str,
    checked_start: datetime,
) -> ExposureContaminationResult:
    reflection = _first_legacy_reflection(
        db, user_id=user_id, event_time=event_time, categories=categories
    )
    if reflection is not None:
        category = LEGACY_REFLECTION_CATEGORY.get(
            reflection.reflection_type, "behavioral_insight"
        )
        return _exposed(
            state="EXPOSED",
            exposure_ids=[f"legacy_reflection:{reflection.view_id}"],
            exposure_categories=[category],
            signal_target=signal_target,
            horizon_policy_version=horizon_policy_version,
            start=checked_start,
            end=event_time,
            effect="legacy_reflection_view_log_impression",
        )

    calibration = _first_legacy_calibration_nudge(
        db, user_id=user_id, event_time=event_time, categories=categories
    )
    if calibration is not None:
        return _exposed(
            state="INTERVENTION" if calibration.user_decision == "accepted" else "EXPOSED",
            exposure_ids=[f"legacy_calibration_nudge:{calibration.event_id}"],
            exposure_categories=["scheduling_suggestion"],
            signal_target=signal_target,
            horizon_policy_version=horizon_policy_version,
            start=checked_start,
            end=event_time,
            effect="legacy_calibration_nudge_event",
        )

    pause_prediction = _first_legacy_pause_prediction(
        db, user_id=user_id, event_time=event_time, categories=categories
    )
    if pause_prediction is not None:
        return _exposed(
            state="INTERVENTION"
            if pause_prediction.user_response == "pause_now"
            else "EXPOSED",
            exposure_ids=[f"legacy_pause_prediction:{pause_prediction.firing_id}"],
            exposure_categories=["predictive_alert"],
            signal_target=signal_target,
            horizon_policy_version=horizon_policy_version,
            start=checked_start,
            end=event_time,
            effect="legacy_pause_prediction_log",
        )

    resume_prediction = _first_legacy_resume_prediction(
        db, user_id=user_id, event_time=event_time, categories=categories
    )
    if resume_prediction is not None:
        return _exposed(
            state="INTERVENTION"
            if resume_prediction.user_response == "resumed_within_window"
            else "EXPOSED",
            exposure_ids=[f"legacy_resume_prediction:{resume_prediction.firing_id}"],
            exposure_categories=["predictive_alert"],
            signal_target=signal_target,
            horizon_policy_version=horizon_policy_version,
            start=checked_start,
            end=event_time,
            effect="legacy_resume_prediction_log",
        )

    return ExposureContaminationResult(
        state="NONE",
        exposure_ids=[],
        exposure_categories=[],
        signal_target=signal_target,
        checked_window_start=checked_start,
        checked_window_end=event_time,
        horizon_policy_version=horizon_policy_version,
        unknown_reason=None,
        policy_effect_reason="no_legacy_exposure_in_policy_horizon",
    )


def _first_legacy_reflection(
    db: Session,
    *,
    user_id: int,
    event_time: datetime,
    categories: dict[str, int],
) -> Optional[ReflectionViewLog]:
    types = [
        reflection_type
        for reflection_type, category in LEGACY_REFLECTION_CATEGORY.items()
        if category in categories
    ]
    if not types:
        return None
    start = _minimum_window(event_time, categories)
    rows = (
        db.query(ReflectionViewLog)
        .filter(
            ReflectionViewLog.user_id == user_id,
            ReflectionViewLog.event_class == "impression",
            ReflectionViewLog.reflection_type.in_(types),
            ReflectionViewLog.fired_at >= start,
            ReflectionViewLog.fired_at <= event_time,
        )
        .order_by(ReflectionViewLog.fired_at.desc())
        .all()
    )
    for row in rows:
        category = LEGACY_REFLECTION_CATEGORY.get(row.reflection_type, "behavioral_insight")
        if _within_category_horizon(row.fired_at, event_time, category, categories):
            return row
    return None


def _first_legacy_calibration_nudge(
    db: Session,
    *,
    user_id: int,
    event_time: datetime,
    categories: dict[str, int],
) -> Optional[CalibrationNudgeEvent]:
    if not ({"scheduling_suggestion", "behavioral_insight"} & set(categories)):
        return None
    start = _minimum_window(event_time, categories)
    rows = (
        db.query(CalibrationNudgeEvent)
        .filter(
            CalibrationNudgeEvent.user_id == user_id,
            CalibrationNudgeEvent.voided_at.is_(None),
            CalibrationNudgeEvent.decided_at >= start,
            CalibrationNudgeEvent.decided_at <= event_time,
        )
        .order_by(CalibrationNudgeEvent.decided_at.desc())
        .all()
    )
    for row in rows:
        if _within_category_horizon(
            row.decided_at, event_time, "scheduling_suggestion", categories
        ) or _within_category_horizon(
            row.decided_at, event_time, "behavioral_insight", categories
        ):
            return row
    return None


def _first_legacy_pause_prediction(
    db: Session,
    *,
    user_id: int,
    event_time: datetime,
    categories: dict[str, int],
) -> Optional[PausePredictionLog]:
    if "predictive_alert" not in categories:
        return None
    start = event_time - timedelta(minutes=categories["predictive_alert"])
    return (
        db.query(PausePredictionLog)
        .filter(
            PausePredictionLog.user_id == user_id,
            PausePredictionLog.fired_at >= start,
            PausePredictionLog.fired_at <= event_time,
        )
        .order_by(PausePredictionLog.fired_at.desc())
        .first()
    )


def _first_legacy_resume_prediction(
    db: Session,
    *,
    user_id: int,
    event_time: datetime,
    categories: dict[str, int],
) -> Optional[ResumePredictionLog]:
    if "predictive_alert" not in categories:
        return None
    start = event_time - timedelta(minutes=categories["predictive_alert"])
    return (
        db.query(ResumePredictionLog)
        .filter(
            ResumePredictionLog.user_id == user_id,
            ResumePredictionLog.fired_at >= start,
            ResumePredictionLog.fired_at <= event_time,
        )
        .order_by(ResumePredictionLog.fired_at.desc())
        .first()
    )


def _minimum_window(event_time: datetime, categories: dict[str, int]) -> datetime:
    return event_time - timedelta(minutes=max(categories.values()))


def _within_category_horizon(
    happened_at: datetime,
    event_time: datetime,
    category: str,
    categories: dict[str, int],
) -> bool:
    if category not in categories:
        return False
    happened_at = strip_tz(happened_at)
    return event_time - timedelta(minutes=categories[category]) <= happened_at <= event_time


def _unknown(
    *,
    signal_target: str,
    horizon_policy_version: str,
    reason: str,
    effect: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> ExposureContaminationResult:
    return ExposureContaminationResult(
        state="UNKNOWN",
        exposure_ids=[],
        exposure_categories=[],
        signal_target=signal_target,
        checked_window_start=start,
        checked_window_end=end,
        horizon_policy_version=horizon_policy_version,
        unknown_reason=reason,
        policy_effect_reason=effect,
    )


def _exposed(
    *,
    state: Literal["EXPOSED", "INTERVENTION"],
    exposure_ids: list[str],
    exposure_categories: list[str],
    signal_target: str,
    horizon_policy_version: str,
    start: datetime,
    end: datetime,
    effect: str,
) -> ExposureContaminationResult:
    return ExposureContaminationResult(
        state=state,
        exposure_ids=exposure_ids,
        exposure_categories=exposure_categories,
        signal_target=signal_target,
        checked_window_start=start,
        checked_window_end=end,
        horizon_policy_version=horizon_policy_version,
        unknown_reason=None,
        policy_effect_reason=effect,
    )
