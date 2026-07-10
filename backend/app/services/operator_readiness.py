"""Read-only readiness projections for the operator dashboard."""
from __future__ import annotations

from typing import Any, Iterable

from app.services.operator_metric_meta import metric_meta

READINESS_RED_TRACE_RATIO = 0.60
READINESS_GREEN_TRACE_RATIO = 0.80
GREEN_TIMER_CLOSURE_RATE = 0.70


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
