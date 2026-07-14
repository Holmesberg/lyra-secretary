"""Rule 11 reopen helpers for analytics Insights.

This module owns the read-only evidence gate for reopening an Insights surface
after a no-nudge control hold. It does not create exposure decisions or commit
database writes.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import ExposureDecisionEvent, Task
from app.services.output_surfaces import RULE11_CONTROL_ARM, RULE11_POLICY_VERSION
from app.utils.time_utils import strip_tz

ANALYTICS_INSIGHTS_SURFACE_ID = "analytics.insights"
ANALYTICS_INSIGHTS_TEMPLATE_ID = "analytics_insights"
INSIGHTS_RULE11_REOPEN_CLEAN_SESSIONS = 3


def insights_rule11_reopen_gate(
    db: Session,
    *,
    user_id: int,
    delta_sessions: list[Task],
    eligible_at,
) -> dict:
    """Return the concrete evidence gate for an active Rule 11 insights hold.

    Rule 11 can decide that an eligible insights card should be withheld. For
    Insights, that hold must not become a purely calendar-periodic surface.
    Once the user sees a hold, reopening is based on new clean stopped sessions
    completed after the first unresolved hold since the last rendered Insights
    card. Repeated refreshes append suppression rows, but must not reset this
    threshold.
    """
    latest_rendered_at = (
        db.query(func.max(ExposureDecisionEvent.eligible_at))
        .filter(
            ExposureDecisionEvent.user_id == user_id,
            ExposureDecisionEvent.trigger_source == ANALYTICS_INSIGHTS_SURFACE_ID,
            ExposureDecisionEvent.content_template_id == ANALYTICS_INSIGHTS_TEMPLATE_ID,
            ExposureDecisionEvent.decision_status == "rendered",
        )
        .scalar()
    )

    hold_query = (
        db.query(func.min(ExposureDecisionEvent.eligible_at))
        .filter(
            ExposureDecisionEvent.user_id == user_id,
            ExposureDecisionEvent.trigger_source == ANALYTICS_INSIGHTS_SURFACE_ID,
            ExposureDecisionEvent.content_template_id == ANALYTICS_INSIGHTS_TEMPLATE_ID,
            ExposureDecisionEvent.decision_status == "suppressed",
            ExposureDecisionEvent.randomization_arm == RULE11_CONTROL_ARM,
            ExposureDecisionEvent.randomization_policy_version == RULE11_POLICY_VERSION,
        )
    )
    if latest_rendered_at is not None:
        hold_query = hold_query.filter(
            ExposureDecisionEvent.eligible_at > latest_rendered_at
        )
    hold_started_at = hold_query.scalar()
    threshold_start = strip_tz(hold_started_at or eligible_at)

    new_clean_sessions = 0
    for task in delta_sessions:
        completed_at = getattr(task, "effective_executed_end_utc", None) or getattr(
            task,
            "executed_end_utc",
            None,
        )
        if completed_at is None:
            continue
        if strip_tz(completed_at) > threshold_start:
            new_clean_sessions += 1

    remaining = max(
        0,
        INSIGHTS_RULE11_REOPEN_CLEAN_SESSIONS - new_clean_sessions,
    )
    return {
        "hold_started_at": threshold_start,
        "reopen_after_clean_sessions": INSIGHTS_RULE11_REOPEN_CLEAN_SESSIONS,
        "new_clean_sessions_since_hold": new_clean_sessions,
        "clean_sessions_until_reopen": remaining,
        "should_hold": remaining > 0,
    }


def insights_rule11_hold_message(remaining: int) -> str:
    noun = "session" if remaining == 1 else "sessions"
    return (
        "Insights are unlocked. LyraOS is holding these cards until there is "
        "new clean evidence after this hold. Complete "
        f"{remaining} more cleanly stopped {noun} to reopen this surface."
    )
