"""Operator-only product health dashboard.

This endpoint is a read-only cohort-readiness cockpit. It reports product-loop
and measurement-integrity health without exposing task content, provider
secrets, or behavioral labels.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_db, operator_user_from_scope
from app.db.models import (
    Deadline,
    DeadlineCompletionEvent,
    ExposureDecisionEvent,
    Feedback,
    StopwatchSession,
    Task,
    TaskExecutionCorrection,
    TaskState,
    User,
)
from app.db.scoping import get_current_user_id, set_current_user_id
from app.services.exposure_ledger import exposure_results_for_task
from app.services.operator_dashboard_metrics import (
    READINESS_GREEN_TRACE_RATIO,
    READINESS_RED_TRACE_RATIO,
    STALE_PAUSE_HOURS,
    activity_dates_by_user as _activity_dates_by_user,
    bug_watchlist_snapshot as _bug_watchlist_snapshot,
    cohort_readiness_snapshot as _cohort_readiness_snapshot,
    data_freshness_snapshot as _data_freshness_snapshot,
    is_test_or_synthetic_user as _is_test_or_synthetic_user,
    meaningful_activity_definition_snapshot as _meaningful_activity_definition_snapshot,
    metric_confidence_snapshot as _metric_confidence_snapshot,
    metric_meta as _metric_meta,
    notification_lifecycle_snapshot as _notification_lifecycle_snapshot,
    operator_recommendations_snapshot as _operator_recommendations_snapshot,
    operator_dynamic_issues_snapshot as _operator_dynamic_issues_snapshot,
    operator_user_rows_snapshot as _operator_user_rows_snapshot,
    pct as _pct,
    privacy_boundary_snapshot as _privacy_boundary_snapshot,
    product_loop_funnel_snapshot as _product_loop_funnel_snapshot,
    provider_integrity_snapshot as _provider_integrity_snapshot,
    redis_notification_snapshot as _redis_notification_snapshot_impl,
    short_hash as _short_hash,
    state_invariants_snapshot as _state_invariants_snapshot,
    user_last_activity_maps as _user_last_activity_maps,
)
from app.utils.redis_client import RedisClient
from app.utils.time_utils import now_utc

router = APIRouter()


def _require_operator(db: Session, request: Request) -> User:
    return operator_user_from_scope(db, request=request)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _redis_notification_snapshot(user_ids: list[int]) -> dict[str, Any]:
    return _redis_notification_snapshot_impl(
        user_ids,
        redis_client_factory=RedisClient,
    )


@router.get("/operator/dashboard")
def operator_dashboard_v12(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Decision-grade cohort readiness snapshot.

    Operator-only. Read-only. Content-minimized. This endpoint answers whether
    the current product loop is ready for more trusted users.
    """
    _require_operator(db, request)
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

        task_total = db.query(func.count(Task.task_id)).filter(Task.voided_at.is_(None)).scalar() or 0
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

        provider_only = (
            db.query(func.count(Deadline.deadline_id))
            .filter(Deadline.user_id.in_(non_op_ids) if non_op_ids else False)
            .filter(Deadline.external_source.isnot(None), Deadline.voided_at.is_(None))
            .scalar()
            or 0
        )
        all_session_task_ids = {
            row[0]
            for row in (
                db.query(StopwatchSession.task_id)
                .join(Task, Task.task_id == StopwatchSession.task_id)
                .filter(Task.user_id.in_(non_op_ids) if non_op_ids else False)
                .all()
            )
        }
        non_session_tasks = (
            db.query(Task)
            .filter(Task.user_id.in_(non_op_ids) if non_op_ids else False)
            .filter(Task.voided_at.is_(None))
            .filter(Task.state != TaskState.DELETED)
            .filter(or_(Task.created_at >= two_weeks_ago, Task.last_modified_at >= two_weeks_ago))
            .all()
        )
        non_session_task_count = sum(
            1 for task in non_session_tasks if task.task_id not in all_session_task_ids
        )

        closed_sessions_14d_all = (
            db.query(StopwatchSession, Task, User)
            .join(Task, Task.task_id == StopwatchSession.task_id)
            .join(User, User.user_id == StopwatchSession.user_id)
            .filter(StopwatchSession.end_time_utc.isnot(None))
            .filter(StopwatchSession.end_time_utc >= two_weeks_ago)
            .all()
        )
        denominator_exclusions = Counter(
            {
                "operator_user_sessions": 0,
                "test_or_synthetic_user_sessions": 0,
                "voided_or_deleted_task_sessions": 0,
                "deleted_retained_sessions": 0,
                "provider_only_rows": int(provider_only),
                "non_session_tasks": int(non_session_task_count),
            }
        )
        closed_sessions_14d: list[tuple[StopwatchSession, Task]] = []
        for session, task, user in closed_sessions_14d_all:
            if user.is_operator:
                denominator_exclusions["operator_user_sessions"] += 1
                continue
            if _is_test_or_synthetic_user(user):
                denominator_exclusions["test_or_synthetic_user_sessions"] += 1
                continue
            if session.post_deletion_retained_at or task.post_deletion_retained_at:
                denominator_exclusions["deleted_retained_sessions"] += 1
                continue
            if task.voided_at is not None or task.state == TaskState.DELETED:
                denominator_exclusions["voided_or_deleted_task_sessions"] += 1
                continue
            closed_sessions_14d.append((session, task))
        closed_count = len(closed_sessions_14d)
        corrected_task_ids = {
            row[0]
            for row in (
                db.query(TaskExecutionCorrection.task_id)
                .filter(TaskExecutionCorrection.created_at >= two_weeks_ago)
                .all()
            )
        }

        dirty_reasons = Counter(
            {
                "auto_closed": 0,
                "stale_recovered": 0,
                "retroactive": 0,
                "corrected": 0,
                "voided": 0,
                "missing_timestamps": 0,
                "impossible_duration": 0,
                "unknown_exposure": 0,
                "provider_only": 0,
                "exposure_contaminated": 0,
            }
        )
        clean_closed = 0
        clean_session_ids: set[str] = set()
        dirty_session_reason_map: dict[str, list[str]] = {}
        for session, task in closed_sessions_14d:
            reasons: set[str] = set()
            if session.auto_closed:
                reasons.add("auto_closed")
            if session.data_quality_flag:
                reasons.add("stale_recovered")
            if task.initiation_status == "retroactive":
                reasons.add("retroactive")
            if task.task_id in corrected_task_ids:
                reasons.add("corrected")
            if task.voided_at is not None:
                reasons.add("voided")
            if not session.start_time_utc or not session.end_time_utc:
                reasons.add("missing_timestamps")
            if (
                session.start_time_utc
                and session.end_time_utc
                and session.end_time_utc < session.start_time_utc
            ):
                reasons.add("impossible_duration")
            exposure_results = exposure_results_for_task(
                db,
                task=task,
                signal_targets=["planning_estimate", "duration_behavior"],
            )
            if any(result.state == "UNKNOWN" for result in exposure_results):
                reasons.add("unknown_exposure")
            if any(
                result.state in {"EXPOSED", "INTERVENTION"}
                for result in exposure_results
            ):
                reasons.add("exposure_contaminated")
            if reasons:
                dirty_reasons.update(reasons)
                dirty_session_reason_map[session.session_id] = sorted(reasons)
            else:
                clean_closed += 1
                clean_session_ids.add(session.session_id)
        dirty_reasons["provider_only"] = int(provider_only)

        clean_trace_ratio = _pct(clean_closed, closed_count) if closed_count else None
        dirty_trace_count = closed_count - clean_closed

        open_sessions = (
            db.query(StopwatchSession, Task)
            .join(Task, Task.task_id == StopwatchSession.task_id)
            .filter(StopwatchSession.end_time_utc.is_(None))
            .filter(StopwatchSession.user_id.in_(non_op_ids) if non_op_ids else False)
            .all()
        )
        open_by_task = Counter(session.task_id for session, _task in open_sessions)
        tasks_by_id = {
            task.task_id: task
            for task in (
                db.query(Task)
                .filter(Task.user_id.in_(non_op_ids) if non_op_ids else False)
                .filter(Task.voided_at.is_(None))
                .all()
            )
        }
        open_session_task_ids = {session.task_id for session, _task in open_sessions}
        duplicate_open_sessions = sum(1 for count in open_by_task.values() if count > 1)
        executing_without_open = sum(
            1
            for task in tasks_by_id.values()
            if task.state == TaskState.EXECUTING and task.task_id not in open_session_task_ids
        )
        paused_without_open = sum(
            1
            for task in tasks_by_id.values()
            if task.state == TaskState.PAUSED and task.task_id not in open_session_task_ids
        )
        executed_missing = sum(
            1
            for task in tasks_by_id.values()
            if task.state == TaskState.EXECUTED
            and (
                task.executed_start_utc is None
                or task.executed_end_utc is None
                or task.executed_duration_minutes is None
            )
        )
        open_for_executed = sum(
            1
            for session, task in open_sessions
            if task.state == TaskState.EXECUTED and session.end_time_utc is None
        )
        stale_reentry_candidates = sum(
            1
            for session, _task in open_sessions
            if session.paused_at_utc is not None
            and session.paused_at_utc <= stale_pause_cutoff
        )

        task_counts_by_user = {
            row.user_id: row.count
            for row in (
                db.query(Task.user_id, func.count(Task.task_id).label("count"))
                .filter(Task.voided_at.is_(None))
                .group_by(Task.user_id)
                .all()
            )
        }
        executed_counts_by_user = {
            row.user_id: row.count
            for row in (
                db.query(Task.user_id, func.count(Task.task_id).label("count"))
                .filter(Task.voided_at.is_(None), Task.state == TaskState.EXECUTED)
                .group_by(Task.user_id)
                .all()
            )
        }
        sessions_by_user = {
            row.user_id: row.count
            for row in (
                db.query(
                    StopwatchSession.user_id,
                    func.count(StopwatchSession.session_id).label("count"),
                )
                .group_by(StopwatchSession.user_id)
                .all()
            )
        }

        clean_sessions_by_user = Counter()
        closed_sessions_by_user = Counter()
        for session, task in closed_sessions_14d:
            closed_sessions_by_user[int(session.user_id)] += 1
            if session.session_id in clean_session_ids:
                clean_sessions_by_user[int(session.user_id)] += 1

        stale_open_by_user = Counter()
        open_timer_by_user = Counter()
        for session, _task in open_sessions:
            open_timer_by_user[int(session.user_id)] += 1
            if session.paused_at_utc and session.paused_at_utc <= stale_pause_cutoff:
                stale_open_by_user[int(session.user_id)] += 1

        activated_users = [
            u for u in non_operator_users
            if task_counts_by_user.get(u.user_id, 0) > 0
            and sessions_by_user.get(u.user_id, 0) > 0
        ]
        meaningful_active_7d = [
            u for u in non_operator_users if active_dates_7d.get(u.user_id)
        ]
        users_with_clean_sessions = [
            u for u in non_operator_users if clean_sessions_by_user.get(u.user_id, 0) > 0
        ]
        users_with_dirty_data_only = [
            u for u in non_operator_users
            if closed_sessions_by_user.get(u.user_id, 0) > 0
            and clean_sessions_by_user.get(u.user_id, 0) == 0
        ]

        session_started_count = (
            db.query(func.count(StopwatchSession.session_id))
            .filter(StopwatchSession.user_id.in_(non_op_ids) if non_op_ids else False)
            .scalar()
            or 0
        )
        clean_stop_count_all = (
            db.query(func.count(StopwatchSession.session_id))
            .join(Task, Task.task_id == StopwatchSession.task_id)
            .filter(StopwatchSession.user_id.in_(non_op_ids) if non_op_ids else False)
            .filter(StopwatchSession.end_time_utc.isnot(None))
            .filter(StopwatchSession.auto_closed.is_(False))
            .filter(StopwatchSession.data_quality_flag.is_(None))
            .filter(Task.voided_at.is_(None))
            .scalar()
            or 0
        )
        timer_start_to_clean_stop_rate = _pct(clean_stop_count_all, session_started_count)

        pressure_map_opened = (
            db.query(func.count(func.distinct(ExposureDecisionEvent.user_id)))
            .filter(ExposureDecisionEvent.content_template_id == "academic_pressure_map")
            .filter(ExposureDecisionEvent.user_id.in_(non_op_ids) if non_op_ids else False)
            .scalar()
            or 0
        )
        insight_seen = (
            db.query(func.count(func.distinct(ExposureDecisionEvent.user_id)))
            .filter(ExposureDecisionEvent.content_template_id == "analytics_insights")
            .filter(ExposureDecisionEvent.user_id.in_(non_op_ids) if non_op_ids else False)
            .scalar()
            or 0
        )
        recovery_surface_seen = (
            db.query(func.count(func.distinct(ExposureDecisionEvent.user_id)))
            .filter(
                ExposureDecisionEvent.content_template_id.in_(
                    ["resume_prediction", "pause_prediction"]
                )
            )
            .filter(ExposureDecisionEvent.user_id.in_(non_op_ids) if non_op_ids else False)
            .scalar()
            or 0
        )
        recovery_plan_confirmed = (
            db.query(func.count(Task.task_id))
            .filter(Task.user_id.in_(non_op_ids) if non_op_ids else False)
            .filter(Task.voided_at.is_(None))
            .filter(Task.notes.ilike("%Pressure Map recovery preview%"))
            .scalar()
            or 0
        )

        product_loop_funnel = _product_loop_funnel_snapshot(
            task_created=non_op_task_total,
            obligation_bound=bound_task_count,
            pressure_map_opened=pressure_map_opened,
            recovery_plan_confirmed=recovery_plan_confirmed,
            timer_started=session_started_count,
            timer_stopped_cleanly=clean_stop_count_all,
            recovery_surface_seen=recovery_surface_seen,
            insight_seen=insight_seen,
            returned_after_24h=sum(1 for u in non_operator_users if u.d1_return_at),
        )

        redis_snapshot = _redis_notification_snapshot(non_op_ids)
        notification_counts = redis_snapshot["counts"]
        notification_lifecycle = _notification_lifecycle_snapshot(
            db,
            user_ids=non_op_ids,
            since=two_weeks_ago,
            redis_snapshot=redis_snapshot,
        )

        provider_rows_total = int(provider_only) + (
            db.query(func.count(DeadlineCompletionEvent.event_id))
            .filter(DeadlineCompletionEvent.user_id.in_(non_op_ids) if non_op_ids else False)
            .filter(DeadlineCompletionEvent.completion_source.ilike("moodle%"))
            .scalar()
            or 0
        )
        provider_rows_missing_provenance = (
            db.query(func.count(Deadline.deadline_id))
            .filter(Deadline.user_id.in_(non_op_ids) if non_op_ids else False)
            .filter(Deadline.external_source.isnot(None))
            .filter(
                or_(
                    Deadline.external_id.is_(None),
                    Deadline.imported_at.is_(None),
                )
            )
            .scalar()
            or 0
        )
        provider_completion_candidates = (
            db.query(func.count(DeadlineCompletionEvent.event_id))
            .filter(DeadlineCompletionEvent.user_id.in_(non_op_ids) if non_op_ids else False)
            .filter(DeadlineCompletionEvent.completion_source.ilike("moodle%"))
            .scalar()
            or 0
        )
        user_confirmed_deadline_ids = (
            db.query(DeadlineCompletionEvent.deadline_id)
            .filter(DeadlineCompletionEvent.user_id.in_(non_op_ids) if non_op_ids else False)
            .filter(
                DeadlineCompletionEvent.completion_source.in_(
                    ("user_deadline_done", "task_retroactive_done")
                )
            )
            .subquery()
        )
        provider_truth_violations = (
            db.query(func.count(func.distinct(Deadline.deadline_id)))
            .join(
                DeadlineCompletionEvent,
                DeadlineCompletionEvent.deadline_id == Deadline.deadline_id,
            )
            .filter(Deadline.user_id.in_(non_op_ids) if non_op_ids else False)
            .filter(Deadline.external_source.ilike("moodle%"))
            .filter(Deadline.state == "completed")
            .filter(DeadlineCompletionEvent.completion_source.ilike("moodle%"))
            .filter(Deadline.deadline_id.notin_(user_confirmed_deadline_ids))
            .scalar()
            or 0
        )
        duplicate_import_candidates = 0
        import_groups = (
            db.query(
                Deadline.user_id,
                Deadline.external_source,
                Deadline.external_id,
                func.count(Deadline.deadline_id).label("count"),
            )
            .filter(Deadline.external_source.isnot(None))
            .filter(Deadline.external_id.isnot(None))
            .filter(Deadline.voided_at.is_(None))
            .filter(Deadline.user_id.in_(non_op_ids) if non_op_ids else False)
            .group_by(Deadline.user_id, Deadline.external_source, Deadline.external_id)
            .all()
        )
        duplicate_import_candidates = sum(max(0, int(row.count) - 1) for row in import_groups)
        sync_failures = sum(
            1
            for u in non_operator_users
            if u.moodle_disconnect_reason or u.moodle_ws_disconnect_reason
        )

        provider_integrity = _provider_integrity_snapshot(
            provider_rows_total=provider_rows_total,
            provider_rows_missing_provenance=provider_rows_missing_provenance,
            provider_completion_candidates=provider_completion_candidates,
            provider_truth_violations=provider_truth_violations,
            duplicate_import_candidates=duplicate_import_candidates,
            sync_failures_24h=sync_failures,
            user_visible_provider_errors_24h=notification_counts[
                "internal_copy_leak_count"
            ],
        )

        feedback_bug_24h = (
            db.query(func.count(Feedback.feedback_id))
            .filter(Feedback.submitted_at >= day_ago)
            .filter(Feedback.kind == "bug")
            .scalar()
            or 0
        )

        measurement_integrity = {
            **_metric_meta(basis="derived", confidence="high", readiness_impact="blocker"),
            "clean_trace_ratio": clean_trace_ratio,
            "dirty_trace_count": dirty_trace_count,
            "dirty_reasons": {k: int(v) for k, v in dirty_reasons.items()},
            "dirty_reason_distribution": {k: int(v) for k, v in dirty_reasons.items()},
            "clean_trace_ratio_basis": {
                "definition": "clean eligible explicit stopwatch sessions / all eligible explicit stopwatch sessions",
                "window_days": 14,
                "numerator": clean_closed,
                "denominator": closed_count,
                "excluded_from_denominator": {
                    k: int(v) for k, v in denominator_exclusions.items()
                },
            },
            "dirty_session_reason_sample": dict(
                (_short_hash(session_id), reasons)
                for session_id, reasons in list(dirty_session_reason_map.items())[:5]
            ),
            "analytic_blockers": [],
            "calibration_safe": bool(clean_trace_ratio is not None and clean_trace_ratio >= READINESS_GREEN_TRACE_RATIO),
            "insights_safe": bool(clean_trace_ratio is not None and clean_trace_ratio >= READINESS_RED_TRACE_RATIO),
        }
        if closed_count == 0:
            measurement_integrity["analytic_blockers"].append("no_closed_sessions_last_14d")
        if dirty_reasons["missing_timestamps"] or dirty_reasons["impossible_duration"]:
            measurement_integrity["analytic_blockers"].append("timestamp_or_duration_integrity")

        state_invariants = _state_invariants_snapshot(
            duplicate_open_sessions=duplicate_open_sessions,
            executing_tasks_without_open_session=executing_without_open,
            paused_tasks_without_open_session=paused_without_open,
            executed_tasks_missing_start_or_end=executed_missing,
            open_sessions_for_executed_tasks=open_for_executed,
            stale_reentry_candidates=stale_reentry_candidates,
        )

        privacy_boundary = _privacy_boundary_snapshot()

        activity_counts_7d = [len(active_dates_7d.get(u.user_id, set())) for u in non_operator_users]
        activity_counts_14d = [len(active_dates_14d.get(u.user_id, set())) for u in non_operator_users]

        cohort_segments = {
            **_metric_meta(basis="derived", confidence="high", readiness_impact="informational"),
            "operator_users_excluded": len(operator_users),
            "test_or_synthetic_users_excluded": len(test_or_synthetic_users),
            "trusted_users": len(non_operator_users),
            "new_users_7d": sum(1 for u in non_operator_users if u.created_at >= week_ago),
            "activated_users": len(activated_users),
            "dormant_users": sum(
                1 for u in non_operator_users
                if last_activity.get(u.user_id) is None
                or last_activity[u.user_id] < week_ago
            ),
            "users_with_dirty_data_only": len(users_with_dirty_data_only),
            "users_with_clean_sessions": len(users_with_clean_sessions),
            "users_with_open_stale_sessions": sum(
                1 for u in non_operator_users if stale_open_by_user.get(u.user_id, 0) > 0
            ),
        }

        first_clean_stop_users = len(users_with_clean_sessions)
        first_pressure_users = int(pressure_map_opened)
        first_recovery_action_users = (
            db.query(func.count(func.distinct(Task.user_id)))
            .filter(Task.user_id.in_(non_op_ids) if non_op_ids else False)
            .filter(Task.notes.ilike("%Pressure Map recovery preview%"))
            .scalar()
            or 0
        )
        activation_quality = {
            **_metric_meta(basis="derived", confidence="medium", readiness_impact="warning"),
            "first_task_created_count": sum(1 for u in non_operator_users if u.first_task_at),
            "first_timer_started_count": sum(1 for u in non_operator_users if u.first_timer_started_at),
            "first_clean_stop_count": first_clean_stop_users,
            "first_pressure_map_action_count": first_pressure_users,
            "first_recovery_action_count": int(first_recovery_action_users),
            "median_time_to_first_clean_loop": None,
            "not_instrumented_fields": ["median_time_to_first_clean_loop"],
        }

        full_loop_users = sum(
            1
            for u in non_operator_users
            if task_counts_by_user.get(u.user_id, 0) > 0
            and sessions_by_user.get(u.user_id, 0) > 0
            and clean_sessions_by_user.get(u.user_id, 0) > 0
        )
        full_loop_rate = _pct(full_loop_users, len(activated_users))

        cohort = {
            **_metric_meta(basis="derived", confidence="medium", readiness_impact="informational"),
            "non_operator_users": len(non_operator_users),
            "trusted_users_total": len(non_operator_users),
            "activated_users": len(activated_users),
            "meaningful_active_users_7d": len(meaningful_active_7d),
            "weekly_active_users": len(meaningful_active_7d),
            "dormant_users_7d": cohort_segments["dormant_users"],
            "dormant_users_14d": sum(
                1 for u in non_operator_users
                if last_activity.get(u.user_id) is None
                or last_activity[u.user_id] < two_weeks_ago
            ),
        }

        d7_eligible = [u for u in non_operator_users if u.created_at <= generated_at - timedelta(days=7)]
        d14_eligible = [u for u in non_operator_users if u.created_at <= generated_at - timedelta(days=14)]
        retention = {
            **_metric_meta(basis="proxy", confidence="medium", readiness_impact="informational"),
            "d1_return_rate": _pct(sum(1 for u in non_operator_users if u.d1_return_at), len(non_operator_users)),
            "d7_return_rate": _pct(
                sum(1 for u in d7_eligible if last_activity.get(u.user_id) and last_activity[u.user_id] >= u.created_at + timedelta(days=7)),
                len(d7_eligible),
            ),
            "d14_return_rate": _pct(
                sum(1 for u in d14_eligible if last_activity.get(u.user_id) and last_activity[u.user_id] >= u.created_at + timedelta(days=14)),
                len(d14_eligible),
            ),
            "returning_today": sum(
                1 for u in non_operator_users
                if last_activity.get(u.user_id) and last_activity[u.user_id] >= day_ago
            ),
            "returning_7d": len(meaningful_active_7d),
            "returning_14d": sum(1 for u in non_operator_users if active_dates_14d.get(u.user_id)),
            "basis_note": "meaningful_activity_proxy",
        }

        activity_frequency = {
            **_metric_meta(basis="proxy", confidence="medium", readiness_impact="informational"),
            "active_days_last_7d": sum(activity_counts_7d),
            "active_days_last_14d": sum(activity_counts_14d),
            "median_days_between_activity": None,
            "login_frequency_status": "not_instrumented",
            "proxy": "active_days_from_explicit_lyra_events",
        }

        reliability = {
            **_metric_meta(basis="derived", confidence="medium", readiness_impact="warning"),
            "user_visible_error_count_24h": int(feedback_bug_24h),
            "failed_api_count_24h": None,
            "calendar_token_warning_user_visible_count": notification_counts["internal_copy_leak_count"],
            "task_state_rejection_count": None,
            "export_success_count": None,
            "delete_success_count": None,
            "not_instrumented_fields": [
                "failed_api_count_24h",
                "task_state_rejection_count",
                "export_success_count",
                "delete_success_count",
            ],
        }

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
            activated_user_count=len(activated_users),
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
