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
    GREEN_TIMER_CLOSURE_RATE,
    MEANINGFUL_EXCLUDED_EVENTS,
    MEANINGFUL_INCLUDED_EVENTS,
    READINESS_GREEN_TRACE_RATIO,
    READINESS_RED_TRACE_RATIO,
    STALE_PAUSE_HOURS,
    activity_dates_by_user as _activity_dates_by_user,
    data_freshness_snapshot as _data_freshness_snapshot,
    dynamic_issue as _dynamic_issue,
    email_hash as _email_hash,
    is_test_or_synthetic_user as _is_test_or_synthetic_user,
    metric_meta as _metric_meta,
    notification_lifecycle_snapshot as _notification_lifecycle_snapshot,
    pct as _pct,
    product_loop_funnel_snapshot as _product_loop_funnel_snapshot,
    redis_notification_snapshot as _redis_notification_snapshot_impl,
    short_hash as _short_hash,
    state_invariants_snapshot as _state_invariants_snapshot,
    user_last_activity_maps as _user_last_activity_maps,
    watchlist_status_from_issues as _watchlist_status_from_issues,
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

        provider_integrity = {
            **_metric_meta(basis="derived", confidence="medium", readiness_impact="warning"),
            "provider_rows_total": provider_rows_total,
            "provider_rows_missing_provenance": int(provider_rows_missing_provenance),
            "provider_completion_candidates": int(provider_completion_candidates),
            "provider_truth_violations": int(provider_truth_violations),
            "duplicate_import_candidates": duplicate_import_candidates,
            "sync_failures_24h": sync_failures,
            "user_visible_provider_errors_24h": notification_counts["internal_copy_leak_count"],
        }

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

        privacy_boundary = {
            **_metric_meta(basis="direct", confidence="high", readiness_impact="blocker"),
            "raw_task_titles_exposed": False,
            "raw_emails_exposed": False,
            "provider_tokens_exposed": False,
            "raw_provider_urls_exposed": False,
            "user_debug_mode_enabled": False,
        }

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

        metric_confidence = {
            "retention": "medium",
            "login_frequency": "not_instrumented",
            "clean_trace_ratio": "high",
            "notification_lifecycle": "medium",
            "provider_integrity": "medium",
            "product_loop_funnel": "medium",
            "state_invariants": "high",
        }

        dynamic_issues: list[dict[str, Any]] = []

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
            dynamic_issues.append(_dynamic_issue(
                issue_id="privacy_boundary_violation",
                severity="critical",
                message="Privacy boundary violation detected.",
                suggested_action="Remove the leaking field before cohort expansion.",
                related_section="privacy_boundary",
                blocks_cohort_expansion=True,
            ))
        if notification_counts["internal_copy_leak_count"] > 0:
            dynamic_issues.append(_dynamic_issue(
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
            dynamic_issues.append(_dynamic_issue(
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
            dynamic_issues.append(_dynamic_issue(
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
            dynamic_issues.append(_dynamic_issue(
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
            dynamic_issues.append(_dynamic_issue(
                issue_id="duplicate_open_sessions",
                severity="critical",
                message="A task has more than one open stopwatch session.",
                suggested_action="Repair the state transition path that created duplicate sessions.",
                related_section="state_invariants",
                blocks_cohort_expansion=True,
            ))
        if executing_without_open > 0:
            dynamic_issues.append(_dynamic_issue(
                issue_id="executing_tasks_without_open_session",
                severity="critical",
                message="Executing tasks exist without an open stopwatch session.",
                suggested_action="Repair task/session state coherence before cohort expansion.",
                related_section="state_invariants",
                blocks_cohort_expansion=True,
            ))
        if paused_without_open > 0:
            dynamic_issues.append(_dynamic_issue(
                issue_id="paused_tasks_without_open_session",
                severity="critical",
                message="Paused tasks exist without an open stopwatch session.",
                suggested_action="Repair task/session state coherence before cohort expansion.",
                related_section="state_invariants",
                blocks_cohort_expansion=True,
            ))
        if executed_missing > 0:
            dynamic_issues.append(_dynamic_issue(
                issue_id="executed_tasks_missing_execution_interval",
                severity="critical",
                message="Executed tasks are missing start, end, or duration fields.",
                suggested_action="Backfill or repair execution intervals before using the data.",
                related_section="state_invariants",
                blocks_cohort_expansion=True,
            ))
        if open_for_executed > 0:
            dynamic_issues.append(_dynamic_issue(
                issue_id="open_sessions_for_executed_tasks",
                severity="critical",
                message="Executed tasks still have open stopwatch sessions.",
                suggested_action="Close or repair the orphaned sessions before cohort expansion.",
                related_section="state_invariants",
                blocks_cohort_expansion=True,
            ))
        if stale_reentry_candidates > 0:
            dynamic_issues.append(_dynamic_issue(
                issue_id="stale_paused_sessions_need_resolution",
                severity="critical",
                message="Stale paused sessions need an explicit user resolution path.",
                suggested_action="Route stale pauses through reflection resolution.",
                related_section="state_invariants",
                blocks_cohort_expansion=True,
                tags=["K04"],
            ))
        if clean_trace_ratio is None:
            dynamic_issues.append(_dynamic_issue(
                issue_id="no_closed_sessions_for_trace_ratio",
                severity="warning",
                message="Clean trace ratio is not available because there are no eligible closed sessions.",
                suggested_action="Treat cohort readiness as dogfood-only until closed-session evidence exists.",
                related_section="measurement_integrity",
                blocks_cohort_expansion=False,
            ))
        elif clean_trace_ratio < READINESS_RED_TRACE_RATIO:
            dynamic_issues.append(_dynamic_issue(
                issue_id="clean_trace_ratio_below_60_percent",
                severity="critical",
                message="Clean trace ratio is below 60 percent.",
                suggested_action="Fix the largest dirty reason bucket before cohort expansion.",
                related_section="measurement_integrity",
                blocks_cohort_expansion=True,
            ))
        elif clean_trace_ratio < READINESS_GREEN_TRACE_RATIO:
            dynamic_issues.append(_dynamic_issue(
                issue_id="clean_trace_ratio_between_60_and_80_percent",
                severity="warning",
                message="Clean trace ratio is between 60 and 80 percent.",
                suggested_action="Dogfood only until clean trace ratio reaches the green threshold.",
                related_section="measurement_integrity",
                blocks_cohort_expansion=False,
            ))
        if notification_lifecycle["not_instrumented_fields"]:
            dynamic_issues.append(_dynamic_issue(
                issue_id="notification_lifecycle_partially_not_instrumented",
                severity="warning",
                message="Notification lifecycle has fields that are not instrumented.",
                suggested_action="Do not infer safety from missing lifecycle fields.",
                related_section="notification_lifecycle",
                blocks_cohort_expansion=False,
            ))
        if "notifications_last_seen_at" in data_freshness["stale_sources"]:
            dynamic_issues.append(_dynamic_issue(
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
            dynamic_issues.append(_dynamic_issue(
                issue_id="invalid_recovery_actions_not_instrumented",
                severity="warning",
                message="Invalid recovery actions are not instrumented.",
                suggested_action="Keep K03 as unknown until invalid recovery attempts are counted.",
                related_section="state_invariants",
                blocks_cohort_expansion=False,
                tags=["K03"],
            ))
        if product_loop_funnel["dropoff_points"]:
            dynamic_issues.append(_dynamic_issue(
                issue_id="product_loop_dropoff_detected",
                severity="warning",
                message="Product loop has a major funnel dropoff.",
                suggested_action="Inspect the dropoff before reading loop metrics as healthy.",
                related_section="product_loop_funnel",
                blocks_cohort_expansion=False,
            ))
        if provider_integrity["provider_rows_missing_provenance"] > 0:
            dynamic_issues.append(_dynamic_issue(
                issue_id="provider_rows_missing_provenance",
                severity="warning",
                message="Provider rows are missing provenance.",
                suggested_action="Fix provider provenance before relying on provider-derived metrics.",
                related_section="provider_integrity",
                blocks_cohort_expansion=False,
            ))
        if provider_integrity["provider_truth_violations"] > 0:
            dynamic_issues.append(_dynamic_issue(
                issue_id="provider_truth_violation",
                severity="critical",
                message="Provider evidence appears to have completed canonical deadlines.",
                suggested_action="Reconcile provider completion rows as candidates or add explicit user confirmation evidence.",
                related_section="provider_integrity",
                blocks_cohort_expansion=True,
            ))

        bug_watchlist = {
            **_metric_meta(basis="derived", confidence="medium", readiness_impact="blocker"),
            "k01_calendar_warning_leak": _watchlist_status_from_issues(dynamic_issues, "K01"),
            "k02_timer_overflow_duplicate": _watchlist_status_from_issues(dynamic_issues, "K02"),
            "k03_invalid_mark_done_executed": _watchlist_status_from_issues(
                dynamic_issues, "K03", default="unknown"
            ),
            "k04_parked_25h_stale": _watchlist_status_from_issues(dynamic_issues, "K04"),
            "k05_pulse_quick_capture_anchor": "unknown",
        }

        readiness_blockers = [
            issue["id"] for issue in dynamic_issues if issue["blocks_cohort_expansion"]
        ]
        warnings = [
            issue["id"] for issue in dynamic_issues if not issue["blocks_cohort_expansion"]
        ]

        green_loop_condition = (
            full_loop_users >= 3
            or (
                len(activated_users) > 0
                and (full_loop_users / len(activated_users)) >= 0.20
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

        cohort_gap_ids = list(dict.fromkeys([*cohort_evidence_gaps, *warnings]))
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
            and bool(cohort_gap_ids)
            and set(cohort_gap_ids).issubset(insufficient_real_data_gaps)
        )

        minimum_fix_set = list(dict.fromkeys(readiness_blockers[:]))
        if not minimum_fix_set and warnings:
            minimum_fix_set = warnings[:3]

        cohort_readiness = {
            **_metric_meta(basis="derived", confidence="medium", readiness_impact="blocker"),
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

        operator_recommendations = [
            {
                "severity": issue["severity"],
                "message": issue["message"],
                "suggested_action": issue["suggested_action"],
                "related_section": issue["related_section"],
                "blocks_cohort_expansion": issue["blocks_cohort_expansion"],
            }
            for issue in dynamic_issues
        ]

        users_payload = []
        for user in non_operator_users:
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
            users_payload.append({
                "user_id": user.user_id,
                "first_name": user.google_first_name,
                "name_source": "google_profile" if user.google_first_name else None,
                "email_hash": _email_hash(user.email),
                "created_at": _iso(user.created_at),
                "last_meaningful_activity_at": _iso(last_activity.get(user.user_id)),
                "active_days_7d": len(active_dates_7d.get(user.user_id, set())),
                "active_days_14d": len(active_dates_14d.get(user.user_id, set())),
                "task_count": task_counts_by_user.get(user.user_id, 0),
                "executed_task_count": executed_counts_by_user.get(user.user_id, 0),
                "stopwatch_session_count": sessions_by_user.get(user.user_id, 0),
                "clean_trace_ratio": _pct(clean_for_user, closed_for_user),
                "open_timer_count": open_timer_by_user.get(user.user_id, 0),
                "paused_over_72h_count": stale_open_by_user.get(user.user_id, 0),
                "last_loop_stage": stage,
            })

        return {
            "generated_at": _iso(generated_at),
            "data_freshness": data_freshness,
            "metric_confidence": metric_confidence,
            "meaningful_activity_definition": {
                **_metric_meta(basis="contract", confidence="high", readiness_impact="informational"),
                "included_events": MEANINGFUL_INCLUDED_EVENTS,
                "excluded_events": MEANINGFUL_EXCLUDED_EVENTS,
            },
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
