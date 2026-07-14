"""Read-only operator dashboard snapshot assembly."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Callable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Task, User
from app.db.scoping import get_current_user_id, set_current_user_id
from app.services.operator_dashboard_metrics import (
    STALE_PAUSE_HOURS,
    activity_dates_by_user as _activity_dates_by_user,
    cohort_activity_query_snapshot as _cohort_activity_query_snapshot,
    data_freshness_snapshot as _data_freshness_snapshot,
    is_test_or_synthetic_user as _is_test_or_synthetic_user,
    meaningful_activity_definition_snapshot as _meaningful_activity_definition_snapshot,
    measurement_integrity_snapshot as _measurement_integrity_snapshot,
    metric_confidence_snapshot as _metric_confidence_snapshot,
    operator_user_rows_snapshot as _operator_user_rows_snapshot,
    privacy_boundary_snapshot as _privacy_boundary_snapshot,
    product_loop_funnel_query_snapshot as _product_loop_funnel_query_snapshot,
    provider_integrity_query_snapshot as _provider_integrity_query_snapshot,
    state_invariants_snapshot as _state_invariants_snapshot,
    task_session_state_query_snapshot as _task_session_state_query_snapshot,
    user_last_activity_maps as _user_last_activity_maps,
)
from app.services.operator_notification_lifecycle import (
    notification_lifecycle_snapshot as _notification_lifecycle_snapshot,
)
from app.services.operator_notification_snapshot import (
    redis_notification_snapshot as _redis_notification_snapshot_impl,
)
from app.services.operator_readiness import (
    bug_watchlist_snapshot as _bug_watchlist_snapshot,
    cohort_readiness_snapshot as _cohort_readiness_snapshot,
    operator_dynamic_issues_snapshot as _operator_dynamic_issues_snapshot,
    operator_recommendations_snapshot as _operator_recommendations_snapshot,
)
from app.utils.time_utils import now_utc


RedisClientFactory = Callable[[], Any]


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _redis_notification_snapshot(
    user_ids: list[int],
    *,
    redis_client_factory: RedisClientFactory,
) -> dict[str, Any]:
    return _redis_notification_snapshot_impl(
        user_ids,
        redis_client_factory=redis_client_factory,
    )


def operator_dashboard_snapshot(
    db: Session,
    *,
    redis_client_factory: RedisClientFactory,
) -> dict[str, Any]:
    """Build the decision-grade cohort readiness snapshot.

    This function is read-only. It clears request-scoped user filters while
    reading operator-wide state, then restores the previous scoped identity.
    """
    original_uid = get_current_user_id()
    set_current_user_id(None)
    try:
        generated_at = now_utc()
        day_ago = generated_at - timedelta(days=1)
        week_ago = generated_at - timedelta(days=7)
        two_weeks_ago = generated_at - timedelta(days=14)
        stale_pause_cutoff = generated_at - timedelta(hours=STALE_PAUSE_HOURS)

        users = db.query(User).order_by(User.user_id.asc()).all()
        operator_users = [u for u in users if u.is_operator]
        test_or_synthetic_users = [
            u for u in users if not u.is_operator and _is_test_or_synthetic_user(u)
        ]
        non_operator_users = [
            u
            for u in users
            if not u.is_operator and not _is_test_or_synthetic_user(u)
        ]
        non_op_ids = [int(u.user_id) for u in non_operator_users]

        last_activity = _user_last_activity_maps(db)
        active_dates_14d = _activity_dates_by_user(db, two_weeks_ago)
        active_dates_7d = {
            uid: {d for d in days if d >= week_ago.date().isoformat()}
            for uid, days in active_dates_14d.items()
        }

        non_op_task_total = (
            db.query(func.count(Task.task_id))
            .filter(Task.voided_at.is_(None))
            .filter(Task.user_id.in_(non_op_ids) if non_op_ids else False)
            .scalar()
            or 0
        )
        bound_task_count = (
            db.query(func.count(Task.task_id))
            .filter(Task.voided_at.is_(None), Task.deadline_id.isnot(None))
            .filter(Task.user_id.in_(non_op_ids) if non_op_ids else False)
            .scalar()
            or 0
        )

        measurement_snapshot = _measurement_integrity_snapshot(
            db,
            user_ids=non_op_ids,
            since=two_weeks_ago,
        )
        provider_only = measurement_snapshot["provider_only_rows"]
        clean_trace_ratio = measurement_snapshot["clean_trace_ratio"]
        measurement_integrity = measurement_snapshot["measurement_integrity"]
        closed_sessions_by_user = Counter(
            measurement_snapshot["closed_sessions_by_user"]
        )
        clean_sessions_by_user = Counter(
            measurement_snapshot["clean_sessions_by_user"]
        )

        task_session_state = _task_session_state_query_snapshot(
            db,
            user_ids=non_op_ids,
            stale_pause_cutoff=stale_pause_cutoff,
        )
        duplicate_open_sessions = task_session_state["duplicate_open_sessions"]
        executing_without_open = task_session_state["executing_without_open"]
        paused_without_open = task_session_state["paused_without_open"]
        executed_missing = task_session_state["executed_missing"]
        open_for_executed = task_session_state["open_for_executed"]
        stale_reentry_candidates = task_session_state["stale_reentry_candidates"]
        task_counts_by_user = task_session_state["task_counts_by_user"]
        executed_counts_by_user = task_session_state["executed_counts_by_user"]
        sessions_by_user = task_session_state["sessions_by_user"]
        stale_open_by_user = task_session_state["stale_open_by_user"]
        open_timer_by_user = task_session_state["open_timer_by_user"]

        product_loop_snapshot = _product_loop_funnel_query_snapshot(
            db,
            user_ids=non_op_ids,
            users=non_operator_users,
            task_created=non_op_task_total,
            obligation_bound=bound_task_count,
        )
        product_loop_funnel = product_loop_snapshot["product_loop_funnel"]
        timer_start_to_clean_stop_rate = product_loop_snapshot[
            "timer_start_to_clean_stop_rate"
        ]
        pressure_map_opened = product_loop_snapshot["pressure_map_opened"]

        redis_snapshot = _redis_notification_snapshot(
            non_op_ids,
            redis_client_factory=redis_client_factory,
        )
        notification_counts = redis_snapshot["counts"]
        notification_lifecycle = _notification_lifecycle_snapshot(
            db,
            user_ids=non_op_ids,
            since=two_weeks_ago,
            redis_snapshot=redis_snapshot,
        )

        provider_integrity = _provider_integrity_query_snapshot(
            db,
            user_ids=non_op_ids,
            users=non_operator_users,
            provider_only_rows=int(provider_only),
            notification_counts=notification_counts,
        )

        state_invariants = _state_invariants_snapshot(
            duplicate_open_sessions=duplicate_open_sessions,
            executing_tasks_without_open_session=executing_without_open,
            paused_tasks_without_open_session=paused_without_open,
            executed_tasks_missing_start_or_end=executed_missing,
            open_sessions_for_executed_tasks=open_for_executed,
            stale_reentry_candidates=stale_reentry_candidates,
        )

        privacy_boundary = _privacy_boundary_snapshot()

        cohort_activity = _cohort_activity_query_snapshot(
            db,
            user_ids=non_op_ids,
            users=non_operator_users,
            operator_user_count=len(operator_users),
            test_or_synthetic_user_count=len(test_or_synthetic_users),
            generated_at=generated_at,
            day_ago=day_ago,
            week_ago=week_ago,
            two_weeks_ago=two_weeks_ago,
            last_activity=last_activity,
            active_dates_7d=active_dates_7d,
            active_dates_14d=active_dates_14d,
            task_counts_by_user=task_counts_by_user,
            sessions_by_user=sessions_by_user,
            closed_sessions_by_user=closed_sessions_by_user,
            clean_sessions_by_user=clean_sessions_by_user,
            stale_open_by_user=stale_open_by_user,
            pressure_map_opened=pressure_map_opened,
            notification_counts=notification_counts,
        )
        cohort_segments = cohort_activity["cohort_segments"]
        activation_quality = cohort_activity["activation_quality"]
        cohort = cohort_activity["cohort"]
        retention = cohort_activity["retention"]
        activity_frequency = cohort_activity["activity_frequency"]
        reliability = cohort_activity["reliability"]
        full_loop_users = cohort_activity["full_loop_users"]
        full_loop_rate = cohort_activity["full_loop_rate"]
        activated_user_count = cohort_activity["activated_user_count"]

        data_freshness = _data_freshness_snapshot(db, generated_at=generated_at)

        metric_confidence = _metric_confidence_snapshot()

        dynamic_issues = _operator_dynamic_issues_snapshot(
            privacy_boundary=privacy_boundary,
            notification_counts=notification_counts,
            notification_lifecycle=notification_lifecycle,
            duplicate_open_sessions=duplicate_open_sessions,
            executing_without_open=executing_without_open,
            paused_without_open=paused_without_open,
            executed_missing=executed_missing,
            open_for_executed=open_for_executed,
            stale_reentry_candidates=stale_reentry_candidates,
            clean_trace_ratio=clean_trace_ratio,
            data_freshness=data_freshness,
            state_invariants=state_invariants,
            product_loop_funnel=product_loop_funnel,
            provider_integrity=provider_integrity,
        )

        bug_watchlist = _bug_watchlist_snapshot(dynamic_issues)

        cohort_readiness = _cohort_readiness_snapshot(
            dynamic_issues=dynamic_issues,
            clean_trace_ratio=clean_trace_ratio,
            timer_start_to_clean_stop_rate=timer_start_to_clean_stop_rate,
            reliability=reliability,
            bug_watchlist=bug_watchlist,
            full_loop_users=full_loop_users,
            activated_user_count=activated_user_count,
        )
        readiness_status = cohort_readiness["status"]

        operator_recommendations = _operator_recommendations_snapshot(dynamic_issues)

        users_payload = _operator_user_rows_snapshot(
            users=non_operator_users,
            closed_sessions_by_user=closed_sessions_by_user,
            clean_sessions_by_user=clean_sessions_by_user,
            task_counts_by_user=task_counts_by_user,
            sessions_by_user=sessions_by_user,
            executed_counts_by_user=executed_counts_by_user,
            open_timer_by_user=open_timer_by_user,
            stale_open_by_user=stale_open_by_user,
            active_dates_7d=active_dates_7d,
            active_dates_14d=active_dates_14d,
            last_activity=last_activity,
        )

        return {
            "generated_at": _iso(generated_at),
            "data_freshness": data_freshness,
            "metric_confidence": metric_confidence,
            "meaningful_activity_definition": _meaningful_activity_definition_snapshot(),
            "cohort_readiness": cohort_readiness,
            "cohort_segments": cohort_segments,
            "cohort": cohort,
            "retention": retention,
            "activity_frequency": activity_frequency,
            "activation_quality": activation_quality,
            "product_loop_funnel": product_loop_funnel,
            "measurement_integrity": measurement_integrity,
            "state_invariants": state_invariants,
            "notification_lifecycle": notification_lifecycle,
            "provider_integrity": provider_integrity,
            "reliability": reliability,
            "privacy_boundary": privacy_boundary,
            "bug_watchlist": bug_watchlist,
            "dynamic_issues": dynamic_issues,
            "users": users_payload,
            "operator_recommendations": operator_recommendations,
            "derived_metrics": {
                "full_loop_users": full_loop_users,
                "full_loop_completion_rate": full_loop_rate,
                "timer_start_to_clean_stop_rate": timer_start_to_clean_stop_rate,
                "safe_to_invite_more_users": readiness_status == "green",
            },
        }
    finally:
        set_current_user_id(original_uid)
