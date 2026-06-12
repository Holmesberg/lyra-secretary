"""Runtime contract for registered output surfaces."""
from __future__ import annotations

import json
from hashlib import sha256
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import (
    Deadline,
    ExposureAckEvent,
    ExposureDecisionEvent,
    ExposureRenderEvent,
    PauseEvent,
    ReflectionViewLog,
    StopwatchSession,
    SuppressionEvent,
    Task,
    TaskState,
    User,
)
from app.core.config import settings
from app.core.authority import authority_for_surface
from app.services.operator_notifier import notify_operator, redacted_user_ref
from app.services.exposure_ledger import (
    baseline_clean_task_ids,
    exposure_results_for_task,
    record_decision,
    record_render,
    record_suppression,
)
from app.utils.time_utils import now_utc, strip_tz, to_local


PROFILE_PROJECTIONS = {
    "measured_execution": "raw_observed",
    "planning_calibration": "raw_observed",
    "pause_process": "raw_observed",
    "descriptive_history": "correction_adjusted_effective",
    "deadline_completion_behavior": "external_submission_trace",
}

RULE11_POLICY_VERSION = "rule11_no_nudge_v1"
RULE11_ACTIVE_ARM = "rule11_active"
RULE11_CONTROL_ARM = "rule11_no_nudge"
RULE11_SUPPRESSION_REASON = "rule11_no_nudge_control_day"
RULE11_BASELINE_DAYS = 7
RULE11_SURFACE_IDS = {
    "analytics.insights",
    "stopwatch.calibration_nudge",
    "stopwatch.micro_mirror",
    "task.creation_nudge",
}
OPERATOR_MIRRORED_OUTPUT_CHANNELS = {"in_app_toast", "in_app_modal"}


@dataclass(frozen=True)
class OutputSurfaceSpec:
    surface_id: str
    truth_class: str
    usage_class: str
    channel: str
    exposure_category: str
    signal_targets: tuple[str, ...]
    clean_profile: Optional[str]
    min_n: int
    time_window_days: Optional[int]
    fallback_mode: str
    operator_only: bool
    legacy_adapter: Optional[str]
    render_policy_version: str
    interruptiveness: str
    salience_level: str

    def as_dict(self) -> dict[str, Any]:
        authority = authority_for_surface(self).as_dict()
        return {
            "surface_id": self.surface_id,
            "truth_class": self.truth_class,
            "usage_class": self.usage_class,
            "channel": self.channel,
            "exposure_category": self.exposure_category,
            "signal_targets": list(self.signal_targets),
            "clean_profile": self.clean_profile,
            "min_n": self.min_n,
            "time_window_days": self.time_window_days,
            "fallback_mode": self.fallback_mode,
            "operator_only": self.operator_only,
            "legacy_adapter": self.legacy_adapter,
            "render_policy_version": self.render_policy_version,
            "interruptiveness": self.interruptiveness,
            "salience_level": self.salience_level,
            **authority,
        }


@lru_cache(maxsize=1)
def load_output_surface_registry() -> dict[str, OutputSurfaceSpec]:
    path = Path(__file__).resolve().parents[1] / "core" / "output_surface_registry.json"
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    surfaces: dict[str, OutputSurfaceSpec] = {}
    for surface_id, row in payload["surfaces"].items():
        surfaces[surface_id] = OutputSurfaceSpec(
            surface_id=surface_id,
            truth_class=row["truth_class"],
            usage_class=row["usage_class"],
            channel=row["channel"],
            exposure_category=row["exposure_category"],
            signal_targets=tuple(row["signal_targets"]),
            clean_profile=row.get("clean_profile"),
            min_n=int(row["min_n"]),
            time_window_days=row.get("time_window_days"),
            fallback_mode=row["fallback_mode"],
            operator_only=bool(row["operator_only"]),
            legacy_adapter=row.get("legacy_adapter"),
            render_policy_version=row["render_policy_version"],
            interruptiveness=row["interruptiveness"],
            salience_level=row["salience_level"],
        )
    return surfaces


def get_output_surface_spec(surface_id: str) -> OutputSurfaceSpec:
    try:
        return load_output_surface_registry()[surface_id]
    except KeyError as exc:
        raise ValueError(f"unregistered_output_surface:{surface_id}") from exc


def registered_surface_ids() -> list[str]:
    return sorted(load_output_surface_registry().keys())


def projection_class_for_profile(clean_profile: Optional[str]) -> Optional[str]:
    """Return the deterministic mixed-row projection for a clean-data profile."""
    if clean_profile is None:
        return None
    try:
        return PROFILE_PROJECTIONS[clean_profile]
    except KeyError as exc:
        raise ValueError(f"missing_projection_for_profile:{clean_profile}") from exc


def rule11_no_nudge_control_active(
    db: Session,
    *,
    user_id: int,
    surface_id: str,
    eligible_at=None,
) -> bool:
    """Deterministic 1-in-7 no-nudge control day for VT-21.

    Activates only after a user's first 7 days so the baseline week remains
    nudge-active, then hashes (user_id, local date, policy version) to avoid
    hand-picked control days while staying perfectly reproducible.
    """
    if surface_id not in RULE11_SURFACE_IDS:
        return False
    eligible_at = strip_tz(eligible_at or now_utc())
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None or user.created_at is None:
        return False
    created_at = strip_tz(user.created_at)
    if eligible_at < created_at + timedelta(days=RULE11_BASELINE_DAYS):
        return False
    local_day = to_local(eligible_at).date().isoformat()
    digest = sha256(
        f"{RULE11_POLICY_VERSION}:{user_id}:{local_day}".encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16) % 7 == 0


def rule11_randomization_fields(
    db: Session,
    *,
    user_id: int,
    surface_id: str,
    eligible_at=None,
) -> tuple[str, Optional[str]]:
    """Return ExposureDecisionEvent randomization fields for Rule 11 surfaces."""
    if surface_id not in RULE11_SURFACE_IDS:
        return "none", None
    arm = (
        RULE11_CONTROL_ARM
        if rule11_no_nudge_control_active(
            db, user_id=user_id, surface_id=surface_id, eligible_at=eligible_at
        )
        else RULE11_ACTIVE_ARM
    )
    return arm, RULE11_POLICY_VERSION


def _snapshot_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, default=str)


def _short_ref(value: Any) -> str:
    return sha256(str(value).encode("utf-8")).hexdigest()[:10]


def mirror_output_surface_render_to_operator(
    *,
    spec: OutputSurfaceSpec,
    user_id: int,
    task_id: Optional[str],
    exposure_id: str,
    render_id: str,
    content_template_id: Optional[str],
    trigger_source: Optional[str],
) -> bool:
    """Mirror toast/modal render metadata to the OpenClaw operator channel.

    The rendered content can contain behavioral feedback, user task titles, or
    other private state. The operator channel gets metadata only. Dashboard
    pages/cards are deliberately excluded to avoid noisy surveillance-flavored
    mirroring.
    """
    if not getattr(settings, "OPENCLAW_MIRROR_USER_NOTIFICATIONS", True):
        return False
    if spec.channel not in OPERATOR_MIRRORED_OUTPUT_CHANNELS:
        return False

    lines = [
        "Output surface rendered.",
        f"User: {redacted_user_ref(user_id)}",
        f"Surface: `{spec.surface_id}`",
        f"Channel: `{spec.channel}`",
        f"Exposure: #{_short_ref(exposure_id)}",
        f"Render: #{_short_ref(render_id)}",
    ]
    if task_id:
        lines.append(f"Task: #{_short_ref(task_id)}")
    if content_template_id:
        lines.append(f"Template: `{content_template_id}`")
    if trigger_source:
        lines.append(f"Trigger: `{trigger_source}`")

    try:
        return notify_operator(
            "\n".join(lines),
            source="output.surface",
            severity="info",
        )
    except Exception:
        return False


def _assert_surface_allowed_for_user(
    db: Session,
    *,
    spec: OutputSurfaceSpec,
    user_id: int,
) -> None:
    if not spec.operator_only:
        return

    is_operator = (
        db.query(User.is_operator)
        .filter(User.user_id == user_id)
        .scalar()
    )
    if not is_operator:
        raise PermissionError(f"operator_only_output_surface:{spec.surface_id}")


def emit_surface_render(
    db: Session,
    *,
    surface_id: str,
    user_id: int,
    content_snapshot: Any,
    task_id: Optional[str] = None,
    eligible_at=None,
    rendered_at=None,
    content_template_id: Optional[str] = None,
    initiative: str = "system",
    trigger_source: Optional[str] = None,
    generating_model: Optional[str] = None,
    generating_version: Optional[str] = None,
    prompt_hash: Optional[str] = None,
    data_snapshot_hash: Optional[str] = None,
    randomization_arm: str = "none",
    randomization_policy_version: Optional[str] = None,
    delivered_at=None,
    create_legacy_view: bool = False,
    legacy_payload: Optional[Any] = None,
    legacy_viewed_at=None,
    legacy_dismissed_at=None,
    legacy_dwell_seconds: Optional[int] = None,
    legacy_outcome: Optional[str] = None,
) -> dict[str, Any]:
    spec = get_output_surface_spec(surface_id)
    _assert_surface_allowed_for_user(db, spec=spec, user_id=user_id)
    eligible_at = strip_tz(eligible_at or now_utc())
    rendered_at = strip_tz(rendered_at or eligible_at)
    content_snapshot_text = _snapshot_to_text(content_snapshot)
    decision = record_decision(
        db,
        user_id=user_id,
        task_id=task_id,
        eligible_at=eligible_at,
        decision_status="rendered",
        initiative=initiative,
        exposure_category=spec.exposure_category,
        content_template_id=content_template_id,
        trigger_source=trigger_source or surface_id,
        generating_model=generating_model,
        generating_version=generating_version,
        prompt_hash=prompt_hash,
        data_snapshot_hash=data_snapshot_hash,
        randomization_arm=randomization_arm,
        randomization_policy_version=randomization_policy_version,
        delivered_at=strip_tz(delivered_at) if delivered_at is not None else rendered_at,
    )
    render = record_render(
        db,
        exposure_id=decision.exposure_id,
        rendered_at=rendered_at,
        surface=surface_id,
        channel=spec.channel,
        content_snapshot=content_snapshot_text,
        render_policy_version=spec.render_policy_version,
        interruptiveness=spec.interruptiveness,
        salience_level=spec.salience_level,
    )
    mirror_output_surface_render_to_operator(
        spec=spec,
        user_id=user_id,
        task_id=task_id,
        exposure_id=decision.exposure_id,
        render_id=render.render_id,
        content_template_id=content_template_id,
        trigger_source=trigger_source or surface_id,
    )

    legacy_view_id: Optional[str] = None
    if create_legacy_view and spec.legacy_adapter:
        row = ReflectionViewLog(
            view_id=str(uuid4()),
            user_id=user_id,
            reflection_type=spec.legacy_adapter,
            event_class="impression",
            task_id=task_id,
            payload=_snapshot_to_text(legacy_payload) if legacy_payload is not None else content_snapshot_text,
            fired_at=rendered_at,
            viewed_at=strip_tz(legacy_viewed_at),
            dismissed_at=strip_tz(legacy_dismissed_at),
            dwell_seconds=legacy_dwell_seconds,
            outcome=legacy_outcome,
        )
        db.add(row)
        db.flush()
        legacy_view_id = row.view_id

    authority = authority_for_surface(spec).as_dict()
    return {
        "surface_id": surface_id,
        "truth_class": spec.truth_class,
        "usage_class": spec.usage_class,
        "clean_profile": spec.clean_profile,
        "fallback_mode": spec.fallback_mode,
        "legacy_adapter": spec.legacy_adapter,
        "signal_targets": list(spec.signal_targets),
        "exposure_id": decision.exposure_id,
        "render_id": render.render_id,
        "legacy_view_id": legacy_view_id,
        **authority,
    }


def emit_surface_suppression(
    db: Session,
    *,
    surface_id: str,
    user_id: int,
    suppression_reason: str,
    task_id: Optional[str] = None,
    eligible_at=None,
    suppressed_at=None,
    content_template_id: Optional[str] = None,
    initiative: str = "system",
    trigger_source: Optional[str] = None,
    generating_confidence: Optional[float] = None,
    randomization_arm: str = "none",
    randomization_policy_version: Optional[str] = None,
) -> dict[str, Any]:
    spec = get_output_surface_spec(surface_id)
    _assert_surface_allowed_for_user(db, spec=spec, user_id=user_id)
    eligible_at = strip_tz(eligible_at or now_utc())
    suppressed_at = strip_tz(suppressed_at or eligible_at)
    decision = record_decision(
        db,
        user_id=user_id,
        task_id=task_id,
        eligible_at=eligible_at,
        decision_status="suppressed",
        initiative=initiative,
        exposure_category=spec.exposure_category,
        content_template_id=content_template_id,
        trigger_source=trigger_source or surface_id,
        randomization_arm=randomization_arm,
        randomization_policy_version=randomization_policy_version,
        delivered_at=None,
    )
    suppression = record_suppression(
        db,
        exposure_id=decision.exposure_id,
        suppressed_at=suppressed_at,
        suppression_reason=suppression_reason,
        would_have_rendered_template_id=content_template_id,
        generating_confidence=generating_confidence,
    )
    authority = authority_for_surface(spec).as_dict()
    return {
        "surface_id": surface_id,
        "truth_class": spec.truth_class,
        "usage_class": spec.usage_class,
        "clean_profile": spec.clean_profile,
        "fallback_mode": spec.fallback_mode,
        "legacy_adapter": spec.legacy_adapter,
        "signal_targets": list(spec.signal_targets),
        "exposure_id": decision.exposure_id,
        "suppression_id": suppression.suppression_id,
        "suppressed_reason": suppression_reason,
        **authority,
    }


def create_output_surface_decision(
    db: Session,
    *,
    surface_id: str,
    user_id: int,
    decision_status: str,
    task_id: Optional[str] = None,
    eligible_at=None,
    content_template_id: Optional[str] = None,
    initiative: str = "system",
    trigger_source: Optional[str] = None,
    delivered_at=None,
    data_snapshot_hash: Optional[str] = None,
) -> ExposureDecisionEvent:
    """Create a registered output-surface decision without claiming render."""
    spec = get_output_surface_spec(surface_id)
    _assert_surface_allowed_for_user(db, spec=spec, user_id=user_id)
    eligible_at = strip_tz(eligible_at or now_utc())
    return record_decision(
        db,
        user_id=user_id,
        task_id=task_id,
        eligible_at=eligible_at,
        decision_status=decision_status,
        initiative=initiative,
        exposure_category=spec.exposure_category,
        content_template_id=content_template_id,
        trigger_source=trigger_source or surface_id,
        data_snapshot_hash=data_snapshot_hash,
        delivered_at=strip_tz(delivered_at) if delivered_at is not None else None,
    )


def acknowledge_surface_render(
    db: Session,
    *,
    exposure_id: str,
    user_id: int,
    acked_at=None,
    client_event_id: Optional[str] = None,
) -> tuple[ExposureAckEvent, bool]:
    """Acknowledge that an exposure reached the authenticated client render boundary.

    This is deliberately smaller than a delivery-state machine. It only proves:
    an authenticated user who owns the exposure acknowledged event_type=render.
    Retries are idempotent by (exposure_id, event_type).
    """
    decision = (
        db.query(ExposureDecisionEvent)
        .filter(ExposureDecisionEvent.exposure_id == exposure_id)
        .first()
    )
    if decision is None:
        raise LookupError("exposure_decision_not_found")
    if decision.user_id != user_id:
        raise PermissionError("exposure_ack_wrong_user")
    if decision.decision_status != "rendered":
        raise ValueError("exposure_decision_not_rendered")

    existing = (
        db.query(ExposureAckEvent)
        .filter(
            ExposureAckEvent.exposure_id == exposure_id,
            ExposureAckEvent.event_type == "render",
        )
        .first()
    )
    if existing is not None:
        return existing, False

    row = ExposureAckEvent(
        exposure_id=exposure_id,
        user_id=user_id,
        event_type="render",
        acked_at=strip_tz(acked_at or now_utc()),
        client_event_id=client_event_id,
    )
    db.add(row)
    db.flush()
    return row, True


def render_existing_surface_decision(
    db: Session,
    *,
    exposure_id: str,
    user_id: int,
    surface_id: str,
    content_snapshot: Any,
    rendered_at=None,
    client_event_id: Optional[str] = None,
) -> bool:
    """Complete a queued/delayed surface decision at browser-render time."""
    decision = (
        db.query(ExposureDecisionEvent)
        .filter(ExposureDecisionEvent.exposure_id == exposure_id)
        .first()
    )
    if decision is None or int(decision.user_id) != int(user_id):
        return False

    spec = get_output_surface_spec(surface_id)
    rendered_at = strip_tz(rendered_at or now_utc())
    existing_render = (
        db.query(ExposureRenderEvent)
        .filter(
            ExposureRenderEvent.exposure_id == exposure_id,
            ExposureRenderEvent.surface == surface_id,
        )
        .first()
    )
    if existing_render is None:
        record_render(
            db,
            exposure_id=exposure_id,
            rendered_at=rendered_at,
            surface=surface_id,
            channel=spec.channel,
            content_snapshot=_snapshot_to_text(content_snapshot),
            render_policy_version=spec.render_policy_version,
            interruptiveness=spec.interruptiveness,
            salience_level=spec.salience_level,
        )

    decision.decision_status = "rendered"
    decision.delivered_at = rendered_at
    acknowledge_surface_render(
        db,
        exposure_id=exposure_id,
        user_id=user_id,
        acked_at=rendered_at,
        client_event_id=client_event_id,
    )
    return True


def _candidate_tasks_for_profile(
    db: Session,
    *,
    user_id: int,
    clean_profile: Optional[str],
    cutoff,
) -> list[Task]:
    if clean_profile is None:
        return []

    q = db.query(Task).filter(
        Task.user_id == user_id,
        Task.voided_at.is_(None),
        or_(Task.planned_start_utc.is_(None), Task.planned_start_utc >= cutoff),
    )

    if clean_profile in {"measured_execution", "planning_calibration"}:
        clean_stopwatch_exists = (
            db.query(StopwatchSession.session_id)
            .filter(
                StopwatchSession.task_id == Task.task_id,
                StopwatchSession.user_id == user_id,
                StopwatchSession.end_time_utc.isnot(None),
                StopwatchSession.auto_closed.is_(False),
                StopwatchSession.data_quality_flag.is_(None),
            )
            .exists()
        )
        auto_closed_stopwatch_exists = (
            db.query(StopwatchSession.session_id)
            .filter(
                StopwatchSession.task_id == Task.task_id,
                StopwatchSession.user_id == user_id,
                StopwatchSession.auto_closed.is_(True),
            )
            .exists()
        )
        q = q.filter(
            Task.state == TaskState.EXECUTED,
            Task.is_anchor.is_(False),
            Task.initiation_status != "system_error",
            Task.initiation_status != "retroactive",
            Task.executed_duration_minutes.isnot(None),
            Task.planned_duration_minutes >= 5,
            clean_stopwatch_exists,
            ~auto_closed_stopwatch_exists,
        )
        if clean_profile == "planning_calibration":
            q = (
                q.outerjoin(Deadline, Task.deadline_id == Deadline.deadline_id)
                .filter(or_(Task.deadline_id.is_(None), Deadline.external_source.is_(None)))
            )
    elif clean_profile == "pause_process":
        q = (
            q.join(StopwatchSession, StopwatchSession.task_id == Task.task_id)
            .join(PauseEvent, PauseEvent.session_id == StopwatchSession.session_id)
            .filter(
                Task.state == TaskState.EXECUTED,
                PauseEvent.self_reported_retroactively.is_(False),
                StopwatchSession.auto_closed.is_(False),
                StopwatchSession.data_quality_flag.is_(None),
            )
            .distinct()
        )
    elif clean_profile == "descriptive_history":
        pass
    elif clean_profile == "deadline_completion_behavior":
        q = q.filter(Task.deadline_id.isnot(None))
    else:
        return []

    return q.all()


def _surface_activity_counts(
    *,
    spec: OutputSurfaceSpec,
    decisions: list[ExposureDecisionEvent],
    render_counts: Counter[str],
    suppression_exposure_ids: set[str],
) -> dict[str, Any]:
    spec_decisions = [
        row for row in decisions
        if row.trigger_source == spec.surface_id
        or row.content_template_id == spec.surface_id.replace(".", "_")
    ]
    decision_ids = {row.exposure_id for row in spec_decisions}
    rendered = render_counts.get(spec.surface_id, 0)
    suppressed = len(decision_ids & suppression_exposure_ids)
    missing_terminal = max(0, len(decision_ids) - rendered - suppressed)
    return {
        "decisions": len(spec_decisions),
        "renders": rendered,
        "suppressions": suppressed,
        "missing_terminal_events": missing_terminal,
    }


def _eligibility_audit_for_surface(
    db: Session,
    *,
    spec: OutputSurfaceSpec,
    user: User,
    cutoff,
) -> dict[str, Any]:
    projection_class = None
    missing_projection = None
    try:
        projection_class = projection_class_for_profile(spec.clean_profile)
    except ValueError as exc:
        missing_projection = str(exc)

    candidates = _candidate_tasks_for_profile(
        db,
        user_id=user.user_id,
        clean_profile=spec.clean_profile,
        cutoff=cutoff,
    )
    candidate_count = len(candidates)

    if missing_projection:
        clean_ids: set[str] = set()
    elif spec.clean_profile == "descriptive_history":
        clean_ids = {task.task_id for task in candidates if task.task_id}
    else:
        clean_ids = baseline_clean_task_ids(
            db,
            tasks=candidates,
            signal_targets=list(spec.signal_targets),
        )

    state_counts: Counter[str] = Counter()
    task_state_counts: Counter[str] = Counter()
    for task in candidates:
        results = exposure_results_for_task(
            db,
            task=task,
            signal_targets=list(spec.signal_targets),
        )
        states = {result.state for result in results}
        for result in results:
            state_counts[result.state] += 1
        if "UNKNOWN" in states:
            task_state_counts["unknown"] += 1
        elif "INTERVENTION" in states:
            task_state_counts["intervention"] += 1
        elif "EXPOSED" in states:
            task_state_counts["exposed"] += 1
        elif states == {"NONE"}:
            task_state_counts["none"] += 1

    clean_n = len(clean_ids)
    if missing_projection:
        suppression_reason = "missing_projection"
    elif clean_n < spec.min_n:
        suppression_reason = "insufficient_clean_samples"
    else:
        suppression_reason = None

    return {
        "surface_id": spec.surface_id,
        "truth_class": spec.truth_class,
        "usage_class": spec.usage_class,
        "clean_profile": spec.clean_profile,
        "projection_class": projection_class,
        "candidate_n": candidate_count,
        "clean_n": clean_n,
        "contaminated_n": max(0, candidate_count - clean_n),
        "unknown_n": task_state_counts.get("unknown", 0),
        "exposed_n": task_state_counts.get("exposed", 0),
        "intervention_n": task_state_counts.get("intervention", 0),
        "state_counts": dict(sorted(state_counts.items())),
        "min_n_required": spec.min_n,
        "suppression_reason": suppression_reason,
        "fallback_mode": spec.fallback_mode,
        "operator_only_skew": {
            "current_user_is_operator": bool(user.is_operator),
            "surface_operator_only": bool(spec.operator_only),
        },
    }


def output_surface_diagnostics(
    db: Session,
    *,
    user_id: int,
    window_days: int = 30,
) -> dict[str, Any]:
    """Operator diagnostic for Wave 4 registry and exposure-chain proof.

    This is meta-instrumentation. It does not render user-facing claims and does
    not create exposure rows.
    """
    user = db.query(User).filter(User.user_id == user_id).one()
    window_days = max(1, min(365, int(window_days)))
    cutoff = strip_tz(now_utc()) - timedelta(days=window_days)

    registry = load_output_surface_registry()
    registered = set(registry)
    decisions = (
        db.query(ExposureDecisionEvent)
        .filter(
            ExposureDecisionEvent.user_id == user_id,
            ExposureDecisionEvent.eligible_at >= cutoff,
        )
        .all()
    )
    decision_ids = [row.exposure_id for row in decisions]
    renders = []
    suppressions = []
    if decision_ids:
        renders = (
            db.query(ExposureRenderEvent)
            .filter(ExposureRenderEvent.exposure_id.in_(decision_ids))
            .all()
        )
        suppressions = (
            db.query(SuppressionEvent)
            .filter(SuppressionEvent.exposure_id.in_(decision_ids))
            .all()
        )

    render_counts = Counter(row.surface for row in renders)
    suppression_exposure_ids = {row.exposure_id for row in suppressions}
    terminal_exposure_ids = {row.exposure_id for row in renders} | suppression_exposure_ids
    missing_terminal_ids = sorted(
        row.exposure_id for row in decisions if row.exposure_id not in terminal_exposure_ids
    )

    legacy_adapter_reliance = []
    for spec in registry.values():
        if not spec.legacy_adapter:
            continue
        legacy_count = (
            db.query(ReflectionViewLog)
            .filter(
                ReflectionViewLog.user_id == user_id,
                ReflectionViewLog.reflection_type == spec.legacy_adapter,
                ReflectionViewLog.fired_at >= cutoff,
            )
            .count()
        )
        v0_activity = _surface_activity_counts(
            spec=spec,
            decisions=decisions,
            render_counts=render_counts,
            suppression_exposure_ids=suppression_exposure_ids,
        )
        legacy_adapter_reliance.append({
            "surface_id": spec.surface_id,
            "legacy_adapter": spec.legacy_adapter,
            "legacy_rows": legacy_count,
            "v0_renders": v0_activity["renders"],
            "parity_delta": legacy_count - v0_activity["renders"],
        })

    current_data_eligibility = [
        _eligibility_audit_for_surface(
            db,
            spec=spec,
            user=user,
            cutoff=cutoff,
        )
        for spec in registry.values()
        if spec.truth_class in {"interpretation", "intervention"}
    ]

    surface_activity = {
        surface_id: _surface_activity_counts(
            spec=spec,
            decisions=decisions,
            render_counts=render_counts,
            suppression_exposure_ids=suppression_exposure_ids,
        )
        for surface_id, spec in sorted(registry.items())
    }

    return {
        "schema_version": "output_surface_diagnostics_v1",
        "window_days": window_days,
        "registry": {
            "registered_surface_count": len(registry),
            "truth_class_counts": dict(sorted(Counter(spec.truth_class for spec in registry.values()).items())),
            "usage_class_counts": dict(sorted(Counter(spec.usage_class for spec in registry.values()).items())),
            "unregistered_render_surfaces": sorted(set(render_counts) - registered),
            "unregistered_decision_triggers": sorted(
                {
                    row.trigger_source
                    for row in decisions
                    if "." in row.trigger_source and row.trigger_source not in registered
                }
            ),
        },
        "dual_write": {
            "decisions": len(decisions),
            "renders": len(renders),
            "suppressions": len(suppressions),
            "decision_without_terminal_event_count": len(missing_terminal_ids),
            "decision_without_terminal_event_ids": missing_terminal_ids[:50],
            "surface_activity": surface_activity,
        },
        "legacy_adapter_reliance": legacy_adapter_reliance,
        "current_data_eligibility": current_data_eligibility,
    }
