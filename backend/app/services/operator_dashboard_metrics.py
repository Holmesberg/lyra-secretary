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


def metric_confidence_snapshot() -> dict[str, str]:
    """Static confidence tiers for operator dashboard metric groups."""
    return {
        "retention": "medium",
        "login_frequency": "not_instrumented",
        "clean_trace_ratio": "high",
        "notification_lifecycle": "medium",
        "provider_integrity": "medium",
        "product_loop_funnel": "medium",
        "state_invariants": "high",
    }


def meaningful_activity_definition_snapshot() -> dict[str, Any]:
    """Static operator-visible contract for meaningful activity proxies."""
    return {
        **metric_meta(
            basis="contract",
            confidence="high",
            readiness_impact="informational",
        ),
        "included_events": MEANINGFUL_INCLUDED_EVENTS,
        "excluded_events": MEANINGFUL_EXCLUDED_EVENTS,
    }


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


def operator_dynamic_issues_snapshot(
    *,
    privacy_boundary: dict[str, Any],
    notification_counts: dict[str, Any],
    notification_lifecycle: dict[str, Any],
    duplicate_open_sessions: int,
    executing_without_open: int,
    paused_without_open: int,
    executed_missing: int,
    open_for_executed: int,
    stale_reentry_candidates: int,
    clean_trace_ratio: float | None,
    data_freshness: dict[str, Any],
    state_invariants: dict[str, Any],
    product_loop_funnel: dict[str, Any],
    provider_integrity: dict[str, Any],
) -> list[dict[str, Any]]:
    """Project already-computed operator snapshots into dynamic issues."""
    issues: list[dict[str, Any]] = []

    if any(
        bool(privacy_boundary[key])
        for key in (
            "raw_task_titles_exposed",
            "raw_emails_exposed",
            "provider_tokens_exposed",
            "raw_provider_urls_exposed",
            "user_debug_mode_enabled",
        )
    ):
        issues.append(dynamic_issue(
            issue_id="privacy_boundary_violation",
            severity="critical",
            message="Privacy boundary violation detected.",
            suggested_action="Remove the leaking field before cohort expansion.",
            related_section="privacy_boundary",
            blocks_cohort_expansion=True,
        ))
    if notification_counts["internal_copy_leak_count"] > 0:
        issues.append(dynamic_issue(
            issue_id="operator_or_internal_copy_visible_to_users",
            severity="critical",
            message="Operator or internal diagnostic copy is visible in the web queue.",
            suggested_action="Split or filter notification channels before inviting users.",
            related_section="notification_lifecycle",
            blocks_cohort_expansion=True,
            tags=["K01"],
        ))

    duplicate_type_counts = notification_lifecycle["duplicate_prompt_type_counts"]
    timer_overflow_duplicate_count = int(duplicate_type_counts.get("timer_overflow", 0))
    non_timer_duplicate_count = (
        int(notification_lifecycle["duplicate_prompt_count"])
        - timer_overflow_duplicate_count
    )
    if timer_overflow_duplicate_count > 0:
        issues.append(dynamic_issue(
            issue_id="duplicate_timer_overflow_prompt",
            severity="critical",
            message=(
                f"Duplicate timer overflow prompts were detected ({timer_overflow_duplicate_count})."
            ),
            suggested_action="Fix timer overflow dedupe and lifecycle accounting.",
            related_section="notification_lifecycle",
            blocks_cohort_expansion=True,
            tags=["K02"],
        ))
    if non_timer_duplicate_count > 0:
        non_timer_types = {
            key: value
            for key, value in duplicate_type_counts.items()
            if key != "timer_overflow" and value
        }
        top_type = next(iter(non_timer_types), "notification")
        issues.append(dynamic_issue(
            issue_id=f"duplicate_pending_{top_type}_prompt",
            severity="critical",
            message=(
                f"Duplicate pending {top_type} prompts were detected ({non_timer_duplicate_count})."
            ),
            suggested_action=(
                "Fix source dedupe metadata or clear stale pending prompts after verification."
            ),
            related_section="notification_lifecycle",
            blocks_cohort_expansion=True,
        ))
    if notification_lifecycle["exposure_without_render_count"] > 0:
        issues.append(dynamic_issue(
            issue_id="exposure_records_without_render_evidence",
            severity="critical",
            message=(
                f"Exposure ledger contains {notification_lifecycle['exposure_without_render_count']} actionable exposure records without render or suppression evidence."
            ),
            suggested_action=(
                "Do not treat exposure-influenced metrics as valid until render linkage is reconciled."
            ),
            related_section="notification_lifecycle",
            blocks_cohort_expansion=True,
        ))

    if duplicate_open_sessions > 0:
        issues.append(dynamic_issue(
            issue_id="duplicate_open_sessions",
            severity="critical",
            message="A task has more than one open stopwatch session.",
            suggested_action="Repair the state transition path that created duplicate sessions.",
            related_section="state_invariants",
            blocks_cohort_expansion=True,
        ))
    if executing_without_open > 0:
        issues.append(dynamic_issue(
            issue_id="executing_tasks_without_open_session",
            severity="critical",
            message="Executing tasks exist without an open stopwatch session.",
            suggested_action="Repair task/session state coherence before cohort expansion.",
            related_section="state_invariants",
            blocks_cohort_expansion=True,
        ))
    if paused_without_open > 0:
        issues.append(dynamic_issue(
            issue_id="paused_tasks_without_open_session",
            severity="critical",
            message="Paused tasks exist without an open stopwatch session.",
            suggested_action="Repair task/session state coherence before cohort expansion.",
            related_section="state_invariants",
            blocks_cohort_expansion=True,
        ))
    if executed_missing > 0:
        issues.append(dynamic_issue(
            issue_id="executed_tasks_missing_execution_interval",
            severity="critical",
            message="Executed tasks are missing start, end, or duration fields.",
            suggested_action="Backfill or repair execution intervals before using the data.",
            related_section="state_invariants",
            blocks_cohort_expansion=True,
        ))
    if open_for_executed > 0:
        issues.append(dynamic_issue(
            issue_id="open_sessions_for_executed_tasks",
            severity="critical",
            message="Executed tasks still have open stopwatch sessions.",
            suggested_action="Close or repair the orphaned sessions before cohort expansion.",
            related_section="state_invariants",
            blocks_cohort_expansion=True,
        ))
    if stale_reentry_candidates > 0:
        issues.append(dynamic_issue(
            issue_id="stale_paused_sessions_need_resolution",
            severity="critical",
            message="Stale paused sessions need an explicit user resolution path.",
            suggested_action="Route stale pauses through reflection resolution.",
            related_section="state_invariants",
            blocks_cohort_expansion=True,
            tags=["K04"],
        ))

    if clean_trace_ratio is None:
        issues.append(dynamic_issue(
            issue_id="no_closed_sessions_for_trace_ratio",
            severity="warning",
            message="Clean trace ratio is not available because there are no eligible closed sessions.",
            suggested_action="Treat cohort readiness as dogfood-only until closed-session evidence exists.",
            related_section="measurement_integrity",
            blocks_cohort_expansion=False,
        ))
    elif clean_trace_ratio < READINESS_RED_TRACE_RATIO:
        issues.append(dynamic_issue(
            issue_id="clean_trace_ratio_below_60_percent",
            severity="critical",
            message="Clean trace ratio is below 60 percent.",
            suggested_action="Fix the largest dirty reason bucket before cohort expansion.",
            related_section="measurement_integrity",
            blocks_cohort_expansion=True,
        ))
    elif clean_trace_ratio < READINESS_GREEN_TRACE_RATIO:
        issues.append(dynamic_issue(
            issue_id="clean_trace_ratio_between_60_and_80_percent",
            severity="warning",
            message="Clean trace ratio is between 60 and 80 percent.",
            suggested_action="Dogfood only until clean trace ratio reaches the green threshold.",
            related_section="measurement_integrity",
            blocks_cohort_expansion=False,
        ))

    if notification_lifecycle["not_instrumented_fields"]:
        issues.append(dynamic_issue(
            issue_id="notification_lifecycle_partially_not_instrumented",
            severity="warning",
            message="Notification lifecycle has fields that are not instrumented.",
            suggested_action="Do not infer safety from missing lifecycle fields.",
            related_section="notification_lifecycle",
            blocks_cohort_expansion=False,
        ))
    if "notifications_last_seen_at" in data_freshness["stale_sources"]:
        issues.append(dynamic_issue(
            issue_id="notification_source_freshness_not_instrumented",
            severity="warning",
            message="Notification lifecycle freshness is not instrumented.",
            suggested_action=(
                "Treat notification lifecycle counts as incomplete until notification source freshness is recorded."
            ),
            related_section="data_freshness",
            blocks_cohort_expansion=False,
        ))
    if state_invariants["invalid_recovery_actions_seen"] is None:
        issues.append(dynamic_issue(
            issue_id="invalid_recovery_actions_not_instrumented",
            severity="warning",
            message="Invalid recovery actions are not instrumented.",
            suggested_action="Keep K03 as unknown until invalid recovery attempts are counted.",
            related_section="state_invariants",
            blocks_cohort_expansion=False,
            tags=["K03"],
        ))
    if product_loop_funnel["dropoff_points"]:
        issues.append(dynamic_issue(
            issue_id="product_loop_dropoff_detected",
            severity="warning",
            message="Product loop has a major funnel dropoff.",
            suggested_action="Inspect the dropoff before reading loop metrics as healthy.",
            related_section="product_loop_funnel",
            blocks_cohort_expansion=False,
        ))
    if provider_integrity["provider_rows_missing_provenance"] > 0:
        issues.append(dynamic_issue(
            issue_id="provider_rows_missing_provenance",
            severity="warning",
            message="Provider rows are missing provenance.",
            suggested_action="Fix provider provenance before relying on provider-derived metrics.",
            related_section="provider_integrity",
            blocks_cohort_expansion=False,
        ))
    if provider_integrity["provider_truth_violations"] > 0:
        issues.append(dynamic_issue(
            issue_id="provider_truth_violation",
            severity="critical",
            message="Provider evidence appears to have completed canonical deadlines.",
            suggested_action="Reconcile provider completion rows as candidates or add explicit user confirmation evidence.",
            related_section="provider_integrity",
            blocks_cohort_expansion=True,
        ))

    return issues


def operator_recommendations_snapshot(
    dynamic_issues: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Project dynamic issues into the dashboard recommendation rows."""
    return [
        {
            "severity": issue["severity"],
            "message": issue["message"],
            "suggested_action": issue["suggested_action"],
            "related_section": issue["related_section"],
            "blocks_cohort_expansion": issue["blocks_cohort_expansion"],
        }
        for issue in dynamic_issues
    ]


def operator_user_rows_snapshot(
    *,
    users: Iterable[User],
    closed_sessions_by_user: dict[int, int],
    clean_sessions_by_user: dict[int, int],
    task_counts_by_user: dict[int, int],
    sessions_by_user: dict[int, int],
    executed_counts_by_user: dict[int, int],
    open_timer_by_user: dict[int, int],
    stale_open_by_user: dict[int, int],
    active_dates_7d: dict[int, set[str]],
    active_dates_14d: dict[int, set[str]],
    last_activity: dict[int, datetime | None],
) -> list[dict[str, Any]]:
    """Project admitted non-operator users into dashboard rows."""
    rows: list[dict[str, Any]] = []
    for user in users:
        closed_for_user = closed_sessions_by_user.get(user.user_id, 0)
        clean_for_user = clean_sessions_by_user.get(user.user_id, 0)
        if task_counts_by_user.get(user.user_id, 0) == 0:
            stage = "signed_up"
        elif sessions_by_user.get(user.user_id, 0) == 0:
            stage = "task_created"
        elif clean_for_user == 0:
            stage = "timer_started"
        else:
            stage = "clean_loop"
        rows.append({
            "user_id": user.user_id,
            "first_name": user.google_first_name,
            "name_source": "google_profile" if user.google_first_name else None,
            "email_hash": email_hash(user.email),
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_meaningful_activity_at": (
                last_activity[user.user_id].isoformat()
                if last_activity.get(user.user_id)
                else None
            ),
            "active_days_7d": len(active_dates_7d.get(user.user_id, set())),
            "active_days_14d": len(active_dates_14d.get(user.user_id, set())),
            "task_count": task_counts_by_user.get(user.user_id, 0),
            "executed_task_count": executed_counts_by_user.get(user.user_id, 0),
            "stopwatch_session_count": sessions_by_user.get(user.user_id, 0),
            "clean_trace_ratio": pct(clean_for_user, closed_for_user),
            "open_timer_count": open_timer_by_user.get(user.user_id, 0),
            "paused_over_72h_count": stale_open_by_user.get(user.user_id, 0),
            "last_loop_stage": stage,
        })
    return rows


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


def bug_watchlist_snapshot(dynamic_issues: list[dict[str, Any]]) -> dict[str, Any]:
    """Project dynamic issues into the operator bug-watchlist status row."""
    return {
        **metric_meta(basis="derived", confidence="medium", readiness_impact="blocker"),
        "k01_calendar_warning_leak": watchlist_status_from_issues(dynamic_issues, "K01"),
        "k02_timer_overflow_duplicate": watchlist_status_from_issues(dynamic_issues, "K02"),
        "k03_invalid_mark_done_executed": watchlist_status_from_issues(
            dynamic_issues, "K03", default="unknown"
        ),
        "k04_parked_25h_stale": watchlist_status_from_issues(dynamic_issues, "K04"),
        "k05_pulse_quick_capture_anchor": "unknown",
    }


def cohort_readiness_snapshot(
    *,
    dynamic_issues: Iterable[dict[str, Any]],
    clean_trace_ratio: float | None,
    timer_start_to_clean_stop_rate: float | None,
    reliability: dict[str, Any],
    bug_watchlist: dict[str, Any],
    full_loop_users: int,
    activated_user_count: int,
) -> dict[str, Any]:
    """Project invariant findings and data volume into the stop/go contract."""
    issues = list(dynamic_issues)
    readiness_blockers = [
        issue["id"] for issue in issues if issue["blocks_cohort_expansion"]
    ]
    warnings = [
        issue["id"] for issue in issues if not issue["blocks_cohort_expansion"]
    ]

    green_loop_condition = (
        full_loop_users >= 3
        or (
            activated_user_count > 0
            and (full_loop_users / activated_user_count) >= 0.20
        )
    )
    green_conditions_met = (
        not readiness_blockers
        and clean_trace_ratio is not None
        and clean_trace_ratio >= READINESS_GREEN_TRACE_RATIO
        and timer_start_to_clean_stop_rate is not None
        and timer_start_to_clean_stop_rate >= GREEN_TIMER_CLOSURE_RATE
        and reliability["calendar_token_warning_user_visible_count"] == 0
        and all(
            bug_watchlist[key] == "pass"
            for key in (
                "k01_calendar_warning_leak",
                "k02_timer_overflow_duplicate",
                "k04_parked_25h_stale",
            )
        )
        and green_loop_condition
    )
    if readiness_blockers:
        readiness_status = "red"
    elif green_conditions_met:
        readiness_status = "green"
    else:
        readiness_status = "yellow"

    cohort_evidence_gaps = []
    if clean_trace_ratio is None:
        cohort_evidence_gaps.append("no_closed_sessions_last_14d")
    elif clean_trace_ratio < READINESS_GREEN_TRACE_RATIO:
        cohort_evidence_gaps.append("clean_trace_ratio_below_green_threshold")
    if timer_start_to_clean_stop_rate is None:
        cohort_evidence_gaps.append("timer_closure_rate_not_available")
    elif timer_start_to_clean_stop_rate < GREEN_TIMER_CLOSURE_RATE:
        cohort_evidence_gaps.append("timer_closure_rate_below_green_threshold")
    if not green_loop_condition:
        cohort_evidence_gaps.append("insufficient_full_loop_users")
    if reliability["calendar_token_warning_user_visible_count"] > 0:
        cohort_evidence_gaps.append("user_visible_calendar_warning_leak")
    for key in (
        "k01_calendar_warning_leak",
        "k02_timer_overflow_duplicate",
        "k04_parked_25h_stale",
    ):
        if bug_watchlist[key] != "pass":
            cohort_evidence_gaps.append(f"{key}_not_pass")

    blocking_cohort_gap_ids = list(dict.fromkeys(cohort_evidence_gaps))
    cohort_gap_ids = list(dict.fromkeys([*blocking_cohort_gap_ids, *warnings]))
    insufficient_real_data_gaps = {
        "no_closed_sessions_last_14d",
        "timer_closure_rate_not_available",
        "insufficient_full_loop_users",
    }
    implementation_green = not readiness_blockers
    cohort_green = readiness_status == "green"
    only_insufficient_real_data = (
        implementation_green
        and not cohort_green
        and bool(blocking_cohort_gap_ids)
        and set(blocking_cohort_gap_ids).issubset(insufficient_real_data_gaps)
    )

    minimum_fix_set = list(dict.fromkeys(readiness_blockers[:]))
    if not minimum_fix_set and warnings:
        minimum_fix_set = warnings[:3]

    return {
        **metric_meta(basis="derived", confidence="medium", readiness_impact="blocker"),
        "status": readiness_status,
        "blockers": list(dict.fromkeys(readiness_blockers)),
        "warnings": list(dict.fromkeys(warnings)),
        "minimum_fix_set": minimum_fix_set,
        "safe_to_invite_more_users": readiness_status == "green",
        "implementation_green": implementation_green,
        "implementation_status": "green" if implementation_green else "red",
        "implementation_blockers": list(dict.fromkeys(readiness_blockers)),
        "cohort_green": cohort_green,
        "cohort_status": readiness_status,
        "cohort_evidence_gaps": cohort_gap_ids,
        "controlled_evidence_collection_allowed": only_insufficient_real_data,
        "controlled_evidence_collection_reason": (
            "implementation_green_but_only_real_data_volume_missing"
            if only_insufficient_real_data
            else None
        ),
        "rationale": (
            "Ready for cautious trusted-user expansion."
            if readiness_status == "green"
            else "Fix blocker set before inviting more users."
            if readiness_status == "red"
            else "Dogfood only until warnings are resolved or explicitly accepted."
        ),
    }


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
    """Read-time activity proxy from explicit Barzakh state changes."""
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
            "notifications_last_seen_at": iso(
                last_non_null([
                    db.query(func.max(NotificationLifecycleEvent.last_transition_at)).scalar(),
                    db.query(func.max(NotificationLifecycleEvent.created_at)).scalar(),
                ])
            ),
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


def state_invariants_snapshot(
    *,
    duplicate_open_sessions: int,
    executing_tasks_without_open_session: int,
    paused_tasks_without_open_session: int,
    executed_tasks_missing_start_or_end: int,
    open_sessions_for_executed_tasks: int,
    stale_reentry_candidates: int,
) -> dict[str, Any]:
    """Read-only task/session coherence snapshot."""
    return {
        **metric_meta(basis="derived", confidence="high", readiness_impact="blocker"),
        "duplicate_open_sessions": int(duplicate_open_sessions),
        "executing_tasks_without_open_session": int(
            executing_tasks_without_open_session
        ),
        "paused_tasks_without_open_session": int(
            paused_tasks_without_open_session
        ),
        "executed_tasks_missing_start_or_end": int(
            executed_tasks_missing_start_or_end
        ),
        "open_sessions_for_executed_tasks": int(open_sessions_for_executed_tasks),
        "stale_reentry_candidates": int(stale_reentry_candidates),
        "invalid_recovery_actions_seen": None,
        "not_instrumented_fields": ["invalid_recovery_actions_seen"],
    }


def provider_integrity_snapshot(
    *,
    provider_rows_total: int,
    provider_rows_missing_provenance: int,
    provider_completion_candidates: int,
    provider_truth_violations: int,
    duplicate_import_candidates: int,
    sync_failures_24h: int,
    user_visible_provider_errors_24h: int,
) -> dict[str, Any]:
    """Read-only provider provenance and native-truth boundary snapshot."""
    return {
        **metric_meta(basis="derived", confidence="medium", readiness_impact="warning"),
        "provider_rows_total": int(provider_rows_total),
        "provider_rows_missing_provenance": int(provider_rows_missing_provenance),
        "provider_completion_candidates": int(provider_completion_candidates),
        "provider_truth_violations": int(provider_truth_violations),
        "duplicate_import_candidates": int(duplicate_import_candidates),
        "sync_failures_24h": int(sync_failures_24h),
        "user_visible_provider_errors_24h": int(user_visible_provider_errors_24h),
    }


def privacy_boundary_snapshot() -> dict[str, Any]:
    """Read-only dashboard privacy boundary packet."""
    return {
        **metric_meta(basis="direct", confidence="high", readiness_impact="blocker"),
        "raw_task_titles_exposed": False,
        "raw_emails_exposed": False,
        "provider_tokens_exposed": False,
        "raw_provider_urls_exposed": False,
        "user_debug_mode_enabled": False,
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
