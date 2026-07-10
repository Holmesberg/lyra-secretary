from app.services.operator_readiness import (
    bug_watchlist_snapshot,
    cohort_readiness_snapshot,
    dynamic_issue,
)


def _reliability(*, calendar_warning_count: int = 0) -> dict[str, int]:
    return {
        "calendar_token_warning_user_visible_count": calendar_warning_count,
    }


def _readiness(
    *,
    dynamic_issues=None,
    clean_trace_ratio=None,
    timer_start_to_clean_stop_rate=None,
    reliability=None,
    bug_watchlist=None,
    full_loop_users=0,
    activated_user_count=1,
):
    issues = list(dynamic_issues or [])
    return cohort_readiness_snapshot(
        dynamic_issues=issues,
        clean_trace_ratio=clean_trace_ratio,
        timer_start_to_clean_stop_rate=timer_start_to_clean_stop_rate,
        reliability=reliability or _reliability(),
        bug_watchlist=bug_watchlist or bug_watchlist_snapshot([]),
        full_loop_users=full_loop_users,
        activated_user_count=activated_user_count,
    )


def test_readiness_allows_controlled_alpha_only_for_real_data_volume_gap():
    snapshot = _readiness()

    assert snapshot["implementation_green"] is True
    assert snapshot["implementation_status"] == "green"
    assert snapshot["cohort_green"] is False
    assert snapshot["cohort_status"] == "yellow"
    assert snapshot["safe_to_invite_more_users"] is False
    assert snapshot["controlled_evidence_collection_allowed"] is True
    assert (
        snapshot["controlled_evidence_collection_reason"]
        == "implementation_green_but_only_real_data_volume_missing"
    )
    assert set(snapshot["cohort_evidence_gaps"]) == {
        "no_closed_sessions_last_14d",
        "timer_closure_rate_not_available",
        "insufficient_full_loop_users",
    }


def test_readiness_keeps_controlled_alpha_closed_for_quality_gap():
    snapshot = _readiness(
        clean_trace_ratio=0.7,
        timer_start_to_clean_stop_rate=0.8,
        full_loop_users=3,
        activated_user_count=3,
    )

    assert snapshot["implementation_green"] is True
    assert snapshot["cohort_status"] == "yellow"
    assert snapshot["controlled_evidence_collection_allowed"] is False
    assert "clean_trace_ratio_below_green_threshold" in snapshot["cohort_evidence_gaps"]


def test_readiness_blocker_keeps_implementation_red():
    blocker = dynamic_issue(
        issue_id="exposure_records_without_render_evidence",
        severity="critical",
        message="Exposure ledger contains renderless exposure rows.",
        suggested_action="Reconcile render evidence before reading exposure metrics.",
        related_section="notification_lifecycle",
        blocks_cohort_expansion=True,
    )

    snapshot = _readiness(
        dynamic_issues=[blocker],
        clean_trace_ratio=0.9,
        timer_start_to_clean_stop_rate=0.9,
        full_loop_users=3,
        activated_user_count=3,
    )

    assert snapshot["implementation_green"] is False
    assert snapshot["implementation_status"] == "red"
    assert snapshot["cohort_status"] == "red"
    assert snapshot["controlled_evidence_collection_allowed"] is False
    assert snapshot["implementation_blockers"] == [
        "exposure_records_without_render_evidence"
    ]
    assert snapshot["minimum_fix_set"] == ["exposure_records_without_render_evidence"]


def test_readiness_green_requires_clean_loop_evidence_and_watchlist_passes():
    snapshot = _readiness(
        clean_trace_ratio=0.85,
        timer_start_to_clean_stop_rate=0.8,
        full_loop_users=3,
        activated_user_count=3,
    )

    assert snapshot["implementation_green"] is True
    assert snapshot["cohort_green"] is True
    assert snapshot["cohort_status"] == "green"
    assert snapshot["safe_to_invite_more_users"] is True
    assert snapshot["controlled_evidence_collection_allowed"] is False
    assert snapshot["cohort_evidence_gaps"] == []
