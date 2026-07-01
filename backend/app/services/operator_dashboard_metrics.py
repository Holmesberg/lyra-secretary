"""Read-only helper primitives for the operator dashboard."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Callable, Iterable

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models import Deadline, ExposureAckEvent, StopwatchSession, Task, User
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
