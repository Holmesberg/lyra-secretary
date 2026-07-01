"""Read-only helper primitives for the operator dashboard."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Callable, Iterable

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models import (
    Deadline,
    ExposureAckEvent,
    ExposureDecisionEvent,
    ExposureRenderEvent,
    NotificationLifecycleEvent,
    StopwatchSession,
    SuppressionEvent,
    Task,
    User,
)
from app.services.exposure_ledger import classify_exposure_terminal_state
from app.utils.redis_client import RedisClient

READINESS_RED_TRACE_RATIO = 0.60
READINESS_GREEN_TRACE_RATIO = 0.80
GREEN_TIMER_CLOSURE_RATE = 0.70
STALE_PAUSE_HOURS = 72

MEANINGFUL_INCLUDED_EVENTS = [
    "task_created",
    "brain_dump_confirmed",
    "timer_started",
    "timer_stopped",
    "pressure_map_opened",
    "recovery_action_taken",
    "insight_opened",
    "export_requested",
]
MEANINGFUL_EXCLUDED_EVENTS = [
    "login_only",
    "page_refresh",
    "settings_view_only",
    "background_sync",
]

FORBIDDEN_WEB_MARKERS = (
    "[warn]",
    "[alert]",
    "calendar.sync",
    "affected provider/subsystem",
    "reply with",
    "operator",
    "openclaw",
)


def metric_meta(
    *,
    basis: str = "derived",
    confidence: str = "medium",
    readiness_impact: str = "informational",
    safe_to_ignore_when: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "basis": basis,
        "confidence": confidence,
        "readiness_impact": readiness_impact,
    }
    if safe_to_ignore_when:
        payload["safe_to_ignore_when"] = safe_to_ignore_when
    return payload


def short_hash(value: str | None) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:12]


def email_hash(email: str | None) -> str:
    return short_hash(email)


def is_test_or_synthetic_user(user: User) -> bool:
    email = (user.email or "").strip().lower()
    return (
        email.endswith(".test")
        or email.endswith("@example.test")
        or email.startswith(("test-", "synthetic-", "wave-", "wave1-", "wave2-", "wave3-"))
    )


def pct(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def dynamic_issue(
    *,
    issue_id: str,
    severity: str,
    message: str,
    suggested_action: str,
    related_section: str,
    blocks_cohort_expansion: bool,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": issue_id,
        "severity": severity,
        "message": message,
        "suggested_action": suggested_action,
        "related_section": related_section,
        "readiness_impact": "blocker" if blocks_cohort_expansion else "warning",
        "blocks_cohort_expansion": blocks_cohort_expansion,
        "tags": tags or [],
    }


def watchlist_status_from_issues(
    issues: list[dict[str, Any]],
    tag: str,
    *,
    default: str = "pass",
) -> str:
    tagged = [issue for issue in issues if tag in issue.get("tags", [])]
    if any(issue.get("blocks_cohort_expansion") for issue in tagged):
        return "fail"
    if tagged:
        return "unknown"
    return default


def last_non_null(values: Iterable[datetime | None]) -> datetime | None:
    return max((v for v in values if v is not None), default=None)


def dropoff_points(funnel: dict[str, int | None]) -> list[str]:
    points: list[str] = []
    keys = [
        "pulse_opened",
        "quick_capture_used",
        "brain_dump_submitted",
        "preview_confirmed",
        "task_created",
        "obligation_bound",
        "pressure_map_opened",
        "timer_started",
        "timer_stopped_cleanly",
        "recovery_surface_seen",
        "insight_seen",
        "returned_after_24h",
    ]
    previous_key: str | None = None
    previous_value: int | None = None
    for key in keys:
        value = funnel.get(key)
        if value is None:
            continue
        if previous_value is not None and previous_value > 0:
            drop = 1 - (value / previous_value)
            if drop >= 0.5:
                points.append(f"{previous_key}->{key}")
        previous_key = key
        previous_value = value
    return points


def activity_dates_by_user(db: Session, since: datetime) -> dict[int, set[str]]:
    """Read-time activity proxy from explicit Lyra state changes."""
    dates: dict[int, set[str]] = defaultdict(set)

    task_rows = (
        db.query(Task.user_id, Task.created_at, Task.last_modified_at)
        .filter(Task.voided_at.is_(None))
        .filter(or_(Task.created_at >= since, Task.last_modified_at >= since))
        .all()
    )
    for user_id, created_at, modified_at in task_rows:
        for stamp in (created_at, modified_at):
            if stamp and stamp >= since:
                dates[int(user_id)].add(stamp.date().isoformat())

    session_rows = (
        db.query(
            StopwatchSession.user_id,
            StopwatchSession.start_time_utc,
            StopwatchSession.end_time_utc,
        )
        .filter(
            or_(
                StopwatchSession.start_time_utc >= since,
                StopwatchSession.end_time_utc >= since,
            )
        )
        .all()
    )
    for user_id, start_at, end_at in session_rows:
        for stamp in (start_at, end_at):
            if stamp and stamp >= since:
                dates[int(user_id)].add(stamp.date().isoformat())

    deadline_rows = (
        db.query(Deadline.user_id, Deadline.created_at, Deadline.completed_at)
        .filter(Deadline.voided_at.is_(None))
        .filter(or_(Deadline.created_at >= since, Deadline.completed_at >= since))
        .all()
    )
    for user_id, created_at, completed_at in deadline_rows:
        for stamp in (created_at, completed_at):
            if stamp and stamp >= since:
                dates[int(user_id)].add(stamp.date().isoformat())

    exposure_rows = (
        db.query(ExposureAckEvent.user_id, ExposureAckEvent.acked_at)
        .filter(ExposureAckEvent.acked_at >= since)
        .all()
    )
    for user_id, acked_at in exposure_rows:
        if acked_at:
            dates[int(user_id)].add(acked_at.date().isoformat())

    return dates


def redis_notification_snapshot(
    user_ids: list[int],
    *,
    redis_client_factory: Callable[[], RedisClient] = RedisClient,
) -> dict[str, Any]:
    """Best-effort current queue snapshot; Redis is not the lifecycle ledger."""
    counts = {
        "web_queued": 0,
        "operator_pending": 0,
        "duplicate_prompt_count": 0,
        "internal_copy_leak_count": 0,
    }
    duplicate_breakdown: list[dict[str, Any]] = []
    duplicate_type_counts: Counter[str] = Counter()
    errors: list[str] = []

    def duplicate_identity(payload: dict[str, Any]) -> tuple[str, str, str, str, str]:
        """Privacy-safe identity for detecting repeated pending prompts.

        Canonical notifications should carry a dedupe key or stable target id.
        Older Redis payloads sometimes have only type/message/notification_id;
        for those, compare by content fingerprint so distinct legacy reminders
        do not collapse into one false duplicate bucket.
        """
        payload_type = str(payload.get("type") or "unknown")
        dedupe_key = str(payload.get("dedupe_key") or "")
        task_id = str(payload.get("task_id") or "")
        session_id = str(payload.get("session_id") or "")
        firing_id = str(payload.get("firing_id") or "")
        if dedupe_key:
            return (payload_type, "dedupe", dedupe_key, "", "")
        if task_id or session_id or firing_id:
            return (
                payload_type,
                "target",
                task_id,
                session_id,
                firing_id,
            )

        content_basis = {
            "type": payload_type,
            "message": payload.get("message") or "",
            "body": payload.get("body") or "",
            "title": payload.get("title") or "",
            "description": payload.get("description") or "",
        }
        if not any(value for key, value in content_basis.items() if key != "type"):
            content_basis = {
                key: value
                for key, value in payload.items()
                if key not in {"notification_id", "exposure_id"}
            }
        return (
            payload_type,
            "legacy_content",
            short_hash(json.dumps(content_basis, sort_keys=True, default=str)),
            "",
            "",
        )

    try:
        redis = redis_client_factory()
        for user_id in user_ids:
            key = f"notifications:pending:{int(user_id)}"
            seen = Counter()
            examples: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
            for raw in redis.client.lrange(key, 0, -1):
                try:
                    payload = json.loads(raw)
                except Exception:
                    continue
                payload_type = str(payload.get("type") or "unknown")
                body = " ".join(
                    str(payload.get(k) or "")
                    for k in ("message", "body", "title", "description")
                ).lower()
                stable_key = duplicate_identity(payload)
                seen[stable_key] += 1
                if len(examples[stable_key]) < 3:
                    examples[stable_key].append({
                        "notification_id_hash": short_hash(
                            str(payload.get("notification_id") or "")
                        ),
                        "has_message": bool(payload.get("message")),
                        "field_count": len(payload.keys()),
                    })
                if payload_type == "operator_alert":
                    counts["operator_pending"] += 1
                else:
                    counts["web_queued"] += 1
                    if any(marker in body for marker in FORBIDDEN_WEB_MARKERS):
                        counts["internal_copy_leak_count"] += 1
            for stable_key, count in seen.items():
                if count <= 1:
                    continue
                duplicate_count = count - 1
                payload_type, identity_source, identity_value, session_id, firing_id = stable_key
                task_id = identity_value if identity_source == "target" else ""
                duplicate_type_counts[payload_type] += duplicate_count
                duplicate_breakdown.append({
                    "source": "redis_pending",
                    "type": payload_type,
                    "identity_source": identity_source,
                    "user_hash": short_hash(str(user_id)),
                    "task_hash": short_hash(task_id) if task_id else "",
                    "session_hash": short_hash(session_id) if session_id else "",
                    "firing_hash": short_hash(firing_id) if firing_id else "",
                    "count": duplicate_count,
                    "has_stable_target": identity_source in {"dedupe", "target"},
                    "examples": examples[stable_key],
                })
        counts["duplicate_prompt_count"] = sum(duplicate_type_counts.values())
    except Exception as exc:  # noqa: BLE001 - dashboard should degrade.
        errors.append(type(exc).__name__)
    return {
        "counts": counts,
        "errors": errors,
        "duplicate_breakdown": duplicate_breakdown,
        "duplicate_type_counts": dict(sorted(duplicate_type_counts.items())),
    }


def notification_lifecycle_snapshot(
    db: Session,
    *,
    user_ids: list[int],
    since: datetime,
    redis_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Read-only notification and exposure lifecycle health snapshot."""
    notification_counts = redis_snapshot["counts"]
    lifecycle_rows = (
        db.query(NotificationLifecycleEvent)
        .filter(NotificationLifecycleEvent.created_at >= since)
        .filter(NotificationLifecycleEvent.channel == "web")
        .filter(NotificationLifecycleEvent.user_id.in_(user_ids) if user_ids else False)
        .all()
    )
    lifecycle_status_counts = Counter(row.status for row in lifecycle_rows)
    lifecycle_dedupe_counts = Counter(
        (row.user_id, row.dedupe_key)
        for row in lifecycle_rows
        if row.dedupe_key
        and row.status in {"queued", "reserved"}
    )
    lifecycle_duplicate_count = sum(
        max(0, count - 1) for count in lifecycle_dedupe_counts.values()
    )
    lifecycle_duplicate_breakdown: list[dict[str, Any]] = []
    lifecycle_duplicate_type_counts: Counter[str] = Counter()
    for (row_user_id, row_dedupe_key), count in lifecycle_dedupe_counts.items():
        if count <= 1:
            continue
        row = next(
            (
                candidate
                for candidate in lifecycle_rows
                if candidate.user_id == row_user_id
                and candidate.dedupe_key == row_dedupe_key
            ),
            None,
        )
        if row is None:
            continue
        duplicate_count = count - 1
        lifecycle_duplicate_type_counts[row.notification_type] += duplicate_count
        lifecycle_duplicate_breakdown.append({
            "source": "notification_lifecycle",
            "type": row.notification_type,
            "user_hash": short_hash(str(row.user_id)),
            "dedupe_key_hash": short_hash(row.dedupe_key or ""),
            "count": duplicate_count,
            "has_stable_target": bool(row.task_id or row.session_id or row.firing_id),
        })

    exposure_without_render_rows = (
        db.query(
            ExposureDecisionEvent.decision_status,
            ExposureDecisionEvent.content_template_id,
            ExposureDecisionEvent.exposure_category,
            ExposureDecisionEvent.trigger_source,
            SuppressionEvent.suppression_id,
        )
        .outerjoin(
            ExposureRenderEvent,
            ExposureRenderEvent.exposure_id == ExposureDecisionEvent.exposure_id,
        )
        .outerjoin(
            SuppressionEvent,
            SuppressionEvent.exposure_id == ExposureDecisionEvent.exposure_id,
        )
        .filter(
            or_(
                ExposureDecisionEvent.created_at >= since,
                ExposureDecisionEvent.eligible_at >= since,
                ExposureDecisionEvent.delivered_at >= since,
            )
        )
        .filter(ExposureDecisionEvent.user_id.in_(user_ids) if user_ids else False)
        .filter(ExposureRenderEvent.render_id.is_(None))
        .all()
    )
    terminal_classified_rows = [
        (
            row,
            classify_exposure_terminal_state(
                decision_status=row.decision_status,
                has_render=False,
                has_suppression=row.suppression_id is not None,
            ),
        )
        for row in exposure_without_render_rows
    ]
    suppressed_without_render = sum(
        1
        for _row, classification in terminal_classified_rows
        if classification.state == "suppressed"
    )
    queued_without_render = sum(
        1
        for _row, classification in terminal_classified_rows
        if classification.state == "queued_without_render"
    )
    actionable_missing_render_rows = [
        row
        for row, classification in terminal_classified_rows
        if classification.is_actionable_missing_render
    ]
    exposure_without_render = len(actionable_missing_render_rows)
    exposure_missing_render_breakdown = {
        "actionable_by_template": dict(sorted(Counter(
            row.content_template_id or "unknown"
            for row in actionable_missing_render_rows
        ).items())),
        "actionable_by_trigger": dict(sorted(Counter(
            row.trigger_source or "unknown"
            for row in actionable_missing_render_rows
        ).items())),
        "actionable_by_decision_status": dict(sorted(Counter(
            row.decision_status or "unknown"
            for row in actionable_missing_render_rows
        ).items())),
        "suppressed_by_template": dict(sorted(Counter(
            row.content_template_id or "unknown"
            for row in exposure_without_render_rows
            if row.decision_status == "suppressed" or row.suppression_id is not None
        ).items())),
    }
    render_without_exposure = 0  # FK-enforced by schema when tables are migrated.

    return {
        **metric_meta(basis="mixed", confidence="medium", readiness_impact="warning"),
        "web_created": len(lifecycle_rows),
        "web_queued": lifecycle_status_counts.get("queued", 0),
        "web_reserved": lifecycle_status_counts.get("reserved", 0),
        "web_rendered": sum(1 for row in lifecycle_rows if row.rendered_at is not None),
        "web_acted": sum(1 for row in lifecycle_rows if row.acted_at is not None),
        "web_dismissed": sum(1 for row in lifecycle_rows if row.dismissed_at is not None),
        "web_expired": sum(1 for row in lifecycle_rows if row.expired_at is not None),
        "web_lost_unrendered": sum(
            1 for row in lifecycle_rows if row.lost_unrendered_at is not None
        ),
        "duplicate_prompt_count": max(
            notification_counts["duplicate_prompt_count"],
            lifecycle_duplicate_count,
        ),
        "render_without_exposure_count": render_without_exposure,
        "exposure_without_render_count": exposure_without_render,
        "suppressed_without_render_count": suppressed_without_render,
        "queued_without_render_count": queued_without_render,
        "exposure_missing_render_breakdown": exposure_missing_render_breakdown,
        "operator_created": notification_counts["operator_pending"],
        "operator_pending": notification_counts["operator_pending"],
        "duplicate_prompt_breakdown": (
            redis_snapshot["duplicate_breakdown"]
            + lifecycle_duplicate_breakdown
        )[:20],
        "duplicate_prompt_type_counts": dict(sorted((
            Counter(redis_snapshot["duplicate_type_counts"])
            + lifecycle_duplicate_type_counts
        ).items())),
        "redis_duplicate_prompt_type_counts": redis_snapshot["duplicate_type_counts"],
        "lifecycle_duplicate_prompt_type_counts": dict(
            sorted(lifecycle_duplicate_type_counts.items())
        ),
        "not_instrumented_fields": [],
        "redis_errors": redis_snapshot["errors"],
    }


def data_freshness_snapshot(
    db: Session,
    *,
    generated_at: datetime,
) -> dict[str, Any]:
    """Read-only timestamp coverage for operator source freshness."""

    def iso(value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    payload = {
        **metric_meta(basis="direct", confidence="high", readiness_impact="informational"),
        "generated_at": iso(generated_at),
        "source_windows": {
            "tasks_last_seen_at": iso(
                db.query(func.max(Task.last_modified_at)).scalar()
            ),
            "sessions_last_seen_at": iso(
                last_non_null([
                    db.query(func.max(StopwatchSession.start_time_utc)).scalar(),
                    db.query(func.max(StopwatchSession.end_time_utc)).scalar(),
                ])
            ),
            "notifications_last_seen_at": None,
            "exposures_last_seen_at": iso(
                last_non_null([
                    db.query(func.max(ExposureDecisionEvent.created_at)).scalar(),
                    db.query(func.max(ExposureRenderEvent.created_at)).scalar(),
                    db.query(func.max(ExposureAckEvent.created_at)).scalar(),
                ])
            ),
            "providers_last_seen_at": iso(
                last_non_null([
                    db.query(func.max(Deadline.imported_at)).scalar(),
                    db.query(func.max(User.moodle_last_synced_at)).scalar(),
                    db.query(func.max(User.moodle_ws_last_synced_at)).scalar(),
                ])
            ),
        },
        "stale_sources": [],
    }
    for source, stamp in payload["source_windows"].items():
        if stamp is None:
            payload["stale_sources"].append(source)
    return payload


def product_loop_funnel_snapshot(
    *,
    task_created: int,
    obligation_bound: int,
    pressure_map_opened: int,
    recovery_plan_confirmed: int,
    timer_started: int,
    timer_stopped_cleanly: int,
    recovery_surface_seen: int,
    insight_seen: int,
    returned_after_24h: int,
) -> dict[str, Any]:
    """Read-only product-loop funnel using already-computed counts."""
    payload = {
        **metric_meta(basis="mixed", confidence="medium", readiness_impact="warning"),
        "pulse_opened": None,
        "quick_capture_used": None,
        "brain_dump_submitted": None,
        "preview_confirmed": None,
        "task_created": int(task_created),
        "obligation_bound": int(obligation_bound),
        "pressure_map_opened": int(pressure_map_opened),
        "recovery_plan_previewed": None,
        "recovery_plan_confirmed": int(recovery_plan_confirmed),
        "timer_started": int(timer_started),
        "timer_stopped_cleanly": int(timer_stopped_cleanly),
        "recovery_surface_seen": int(recovery_surface_seen),
        "insight_seen": int(insight_seen),
        "returned_after_24h": int(returned_after_24h),
    }
    payload["dropoff_points"] = dropoff_points(payload)
    payload["not_instrumented_fields"] = [
        "pulse_opened",
        "quick_capture_used",
        "brain_dump_submitted",
        "preview_confirmed",
        "recovery_plan_previewed",
    ]
    return payload


def user_last_activity_maps(db: Session) -> dict[int, datetime]:
    values: dict[int, list[datetime]] = defaultdict(list)
    for user_id, stamp in db.query(Task.user_id, func.max(Task.last_modified_at)).group_by(Task.user_id):
        if stamp:
            values[int(user_id)].append(stamp)
    for user_id, stamp in db.query(StopwatchSession.user_id, func.max(StopwatchSession.end_time_utc)).group_by(StopwatchSession.user_id):
        if stamp:
            values[int(user_id)].append(stamp)
    for user_id, stamp in db.query(StopwatchSession.user_id, func.max(StopwatchSession.start_time_utc)).group_by(StopwatchSession.user_id):
        if stamp:
            values[int(user_id)].append(stamp)
    for user_id, stamp in db.query(Deadline.user_id, func.max(Deadline.created_at)).group_by(Deadline.user_id):
        if stamp:
            values[int(user_id)].append(stamp)
    for user_id, stamp in db.query(ExposureAckEvent.user_id, func.max(ExposureAckEvent.acked_at)).group_by(ExposureAckEvent.user_id):
        if stamp:
            values[int(user_id)].append(stamp)
    return {uid: max(stamps) for uid, stamps in values.items() if stamps}
