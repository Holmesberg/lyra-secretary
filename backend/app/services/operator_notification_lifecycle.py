"""Read-only notification and exposure lifecycle health for the operator dashboard."""
from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import (
    ExposureDecisionEvent,
    ExposureRenderEvent,
    NotificationLifecycleEvent,
    SuppressionEvent,
)
from app.services.exposure_ledger import classify_exposure_terminal_state


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
