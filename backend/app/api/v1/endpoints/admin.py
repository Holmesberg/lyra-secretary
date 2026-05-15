"""Operator-only admin endpoints.

These surface retention/funnel/VT-progress data the operator uses to
decide product next-steps. Every endpoint checks `user.is_operator`
and returns 403 otherwise — no other role has access.

The /admin/dashboard endpoint is the Apr 22 retention-visibility loop
(feedback_loops_closure_plan.md §Loop 8): closes the operator's
decision loop by routing what's otherwise manual psycopg2 queries into
a single JSON response consumed by the /admin/dashboard page.

Performance note: this endpoint is O(users × recent_tasks). At n<20
users the query cost is negligible. When that changes, batch the
per-user stats into a single grouped SQL query.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import (
    ExternalEventOutcome,
    PauseEvent,
    PausePredictionLog,
    StopwatchSession,
    Task,
    TaskState,
    User,
)
from app.db.scoping import get_current_user_id, set_current_user_id
from app.utils.time_utils import now_utc

router = APIRouter()


def _require_operator(db: Session) -> User:
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    user = db.query(User).filter(User.user_id == uid).first()
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    if not user.is_operator:
        raise HTTPException(status_code=403, detail="operator only")
    return user


@router.get("/admin/dashboard")
def operator_dashboard(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Per-user retention + funnel + VT-progress snapshot.

    Operator-only. Returns:
      - totals (all users, non-operator users, returning-today, returning-7d)
      - funnel progression counts (signup → onboarded → first-task →
        first-execution → returned-d2)
      - per-user row for every non-operator user with last-activity
        timestamps + task counts + tour status + GCal-connected flag
      - VT-NN progress indicators for each active research question
        (currently VT-17 pause prediction, VT-22 scope inflation
        preparation, VT-23 external-source attendance, IMP-3 GCal
        retention lift)
    """
    _require_operator(db)

    # Disable user scoping — we're querying across all users.
    original_uid = get_current_user_id()
    set_current_user_id(None)
    try:
        now = now_utc()
        day_ago = now - timedelta(hours=24)
        week_ago = now - timedelta(days=7)

        users = (
            db.query(User)
            .order_by(User.user_id.asc())
            .all()
        )
        non_operator_users = [u for u in users if not u.is_operator]

        task_stats = {
            row.user_id: row
            for row in (
                db.query(
                    Task.user_id.label("user_id"),
                    func.count(Task.task_id).label("task_total"),
                    func.count(Task.task_id)
                    .filter(Task.state == TaskState.EXECUTED)
                    .label("executed_count"),
                    func.count(Task.task_id)
                    .filter(Task.state.notin_([TaskState.SKIPPED, TaskState.DELETED]))
                    .label("active_task_count"),
                    func.count(Task.task_id)
                    .filter(Task.state == TaskState.SKIPPED)
                    .label("skipped_count"),
                    func.count(Task.task_id)
                    .filter(Task.state == TaskState.PLANNED)
                    .filter(Task.planned_start_utc > now + timedelta(days=14))
                    .label("far_future_planned_count"),
                    func.min(Task.created_at).label("first_task_created"),
                    func.min(Task.last_modified_at)
                    .filter(Task.state == TaskState.EXECUTED)
                    .label("first_executed"),
                    func.max(Task.last_modified_at).label("last_task_mod"),
                )
                .filter(Task.voided_at.is_(None))
                .group_by(Task.user_id)
                .all()
            )
        }
        session_stats = {
            row.user_id: row
            for row in (
                db.query(
                    StopwatchSession.user_id.label("user_id"),
                    func.max(StopwatchSession.end_time_utc).label(
                        "last_session_end"
                    ),
                    func.count(StopwatchSession.session_id)
                    .filter(StopwatchSession.end_time_utc.is_(None))
                    .label("open_timer_count"),
                )
                .group_by(StopwatchSession.user_id)
                .all()
            )
        }

        # Per-user aggregates are precomputed above so the operator dashboard
        # stays fast even when the public DB is reached over the tunnel.
        rows: list[dict[str, Any]] = []
        for u in users:
            task_row = task_stats.get(u.user_id)
            session_row = session_stats.get(u.user_id)
            last_task_mod = task_row.last_task_mod if task_row else None
            last_session_end = session_row.last_session_end if session_row else None
            last_activity = max(
                (t for t in (last_task_mod, last_session_end) if t is not None),
                default=None,
            )
            task_total = task_row.task_total if task_row else 0
            executed_count = task_row.executed_count if task_row else 0
            active_task_count = task_row.active_task_count if task_row else 0
            skipped_count = task_row.skipped_count if task_row else 0
            far_future_planned_count = (
                task_row.far_future_planned_count if task_row else 0
            )
            open_timer_count = session_row.open_timer_count if session_row else 0
            first_task_created = task_row.first_task_created if task_row else None
            first_executed = task_row.first_executed if task_row else None
            tutorial_status = (
                "completed"
                if u.tutorial_completed_at
                else "skipped"
                if u.tutorial_skipped_at
                else "pending"
            )
            if u.is_operator:
                activation_stage = "operator"
            elif u.terms_accepted_at is None:
                activation_stage = "needs_terms"
            elif u.onboarding_completed_at is None:
                activation_stage = "brain_dump_not_completed"
            elif task_total == 0:
                activation_stage = "onboarding_skipped_or_empty"
            elif active_task_count == 0:
                activation_stage = "all_tasks_skipped"
            elif far_future_planned_count > 0 and executed_count == 0:
                activation_stage = "planned_far_future"
            elif u.first_timer_started_at is None:
                activation_stage = "planned_no_timer"
            elif executed_count == 0:
                activation_stage = "timer_started_no_completion"
            else:
                activation_stage = "activated"
            rows.append(
                {
                    "user_id": u.user_id,
                    "email": u.email,
                    "is_operator": u.is_operator,
                    "signed_up_at": u.created_at.isoformat(),
                    "onboarded_at": u.onboarding_completed_at.isoformat()
                    if u.onboarding_completed_at
                    else None,
                    "tutorial_status": tutorial_status,
                    "gcal_connected": u.google_refresh_token is not None,
                    "task_total": task_total,
                    "active_task_count": active_task_count,
                    "skipped_count": skipped_count,
                    "far_future_planned_count": far_future_planned_count,
                    "open_timer_count": open_timer_count,
                    "executed_count": executed_count,
                    "first_task_created_at": first_task_created.isoformat()
                    if first_task_created
                    else None,
                    "first_executed_at": first_executed.isoformat()
                    if first_executed
                    else None,
                    "last_activity_at": last_activity.isoformat()
                    if last_activity
                    else None,
                    "returning_today": bool(
                        last_activity and last_activity >= day_ago
                    ),
                    "returning_7d": bool(
                        last_activity and last_activity >= week_ago
                    ),
                    "activation_stage": activation_stage,
                }
            )

        non_op_rows = [r for r in rows if not r["is_operator"]]
        funnel = {
            "signed_up": len(non_op_rows),
            "onboarded": sum(1 for r in non_op_rows if r["onboarded_at"]),
            "meaningful_plan": sum(
                1 for r in non_op_rows if r["active_task_count"] > 0
            ),
            "first_task": sum(
                1 for r in non_op_rows if r["first_task_created_at"]
            ),
            "first_execution": sum(
                1 for r in non_op_rows if r["first_executed_at"]
            ),
            "returning_7d": sum(1 for r in non_op_rows if r["returning_7d"]),
        }

        # VT progress — count users meeting each research question's
        # per-user data threshold. These are not kill-criterion
        # evaluations (those are run at analysis time, not live); these
        # are coverage indicators — "how many users have enough data
        # for VT-N to run."
        vt_17_threshold_users = (
            db.query(func.count(func.distinct(PauseEvent.user_id)))
            .scalar()
            or 0
        )
        vt_17_users_at_threshold = _count_users_with_pause_history(
            db, days=7
        )
        vt_22_macro_with_deadline = 0  # No deadline_utc column yet — Loop 11.
        vt_23_connected_users = (
            db.query(func.count(User.user_id))
            .filter(User.google_refresh_token.isnot(None))
            .scalar()
            or 0
        )
        vt_23_outcome_rows = (
            db.query(func.count(ExternalEventOutcome.id)).scalar() or 0
        )
        imp_3_connected_users = vt_23_connected_users

        vt_progress = {
            "vt_17_pause_prediction": {
                "label": "Pause prediction acceptance-rate readiness",
                "users_with_pause_history": vt_17_threshold_users,
                "users_with_7d_pause_history": vt_17_users_at_threshold,
                "threshold_users": 20,
                "note": "Per-user 7-day pause history required before acceptance-rate evaluation",
            },
            "vt_22_scope_inflation": {
                "label": "Scope inflation mediation (macro tasks w/ deadlines)",
                "macro_tasks_with_deadline": vt_22_macro_with_deadline,
                "threshold_tasks": 50,
                "note": "Requires deadline_utc + scope_bullet schema (Loop 11, alembic 029+) — not yet shipped",
            },
            "vt_23_external_attendance": {
                "label": "External-source attendance self-report",
                "connected_users": vt_23_connected_users,
                "outcome_rows": vt_23_outcome_rows,
                "threshold_users": 20,
                "threshold_rows_per_user": 1,
                "note": "Kill if <15% of past events marked within 7d at n≥20",
            },
            "imp_3_retention_lift": {
                "label": "GCal-connected retention lift",
                "connected_users": imp_3_connected_users,
                "threshold_users": 20,
                "threshold_ratio": 1.25,
                "note": "D7 session ratio ≥1.25× vs unconnected required",
            },
        }

        return {
            "calculated_at": now.isoformat(),
            "totals": {
                "users_all": len(users),
                "users_non_operator": len(non_op_rows),
                "returning_today": sum(
                    1 for r in non_op_rows if r["returning_today"]
                ),
                "returning_7d": funnel["returning_7d"],
            },
            "funnel": funnel,
            "users": rows,
            "vt_progress": vt_progress,
        }
    finally:
        set_current_user_id(original_uid)


def _count_users_with_pause_history(db: Session, days: int) -> int:
    """Users whose pause_event history spans at least `days` calendar days.

    Coverage indicator for VT-17, not an acceptance-rate calculation.
    """
    cutoff = now_utc() - timedelta(days=days)
    # Users with a pause_event ≥ `days` days ago — implies they had enough
    # sustained usage to have accumulated a window worth evaluating.
    result = (
        db.query(func.count(func.distinct(PauseEvent.user_id)))
        .filter(PauseEvent.paused_at_utc <= cutoff)
        .scalar()
        or 0
    )
    return result


@router.get("/admin/alpha_funnel")
def alpha_funnel(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Alpha North Star + funnel snapshot.

    The North Star (operator-set 2026-04-28): % of new users who create a
    task AND start a timer within their first 3 minutes. Without this
    measurement, the magic-for-alpha features are flying blind — we can't
    tell if onboarding revival actually worked. Built from three lazy-stamp
    columns on User: `first_task_at`, `first_timer_started_at`,
    `d1_return_at` (alembic 037, 2026-04-28).

    Research-integrity caveats (per docs/manifesto_alignment_audit_2026_04_28.md
    audit item #7):
      - Per VT-15 (anonymized retention trust-correlated bias), report
        opt-out rate alongside any aggregate finding from this endpoint.
      - Per VT-16 (cross-population methodology error), this is Population 2
        (product research) data, NOT Population 1 (H1 hypothesis research).
        Cross-population contamination is forbidden — DO NOT feed funnel
        statistics into H1 correlation analyses.

    Operator-only.

    Response shape:
      {
        "calculated_at": ISO-8601,
        "north_star": {
          "metric": "task_created+timer_started within 3min",
          "n_eligible": int,         # users with both stamps
          "n_met": int,              # users who hit the 3-min target
          "rate": float,             # n_met / n_eligible
        },
        "funnel": {
          "signed_up": int,
          "completed_onboarding": int,
          "first_task_within_60s": int,
          "first_timer_within_180s": int,
          "returned_d1": int,
        },
        "users": [
          { user_id, email_hash, created_at, onboarding_completed_at,
            first_task_at, first_timer_started_at, d1_return_at,
            seconds_to_first_task, seconds_to_first_timer, met_north_star },
          ...
        ],
      }
    """
    _require_operator(db)
    original_uid = get_current_user_id()
    set_current_user_id(None)
    try:
        users = (
            db.query(User)
            .filter(User.is_operator.is_(False))  # exclude operator from cohort metrics
            .order_by(User.user_id.asc())
            .all()
        )

        rows: list[dict[str, Any]] = []
        signed_up = len(users)
        completed_onboarding = 0
        first_task_within_60s = 0
        first_timer_within_180s = 0
        returned_d1 = 0
        n_eligible = 0
        n_met = 0

        import hashlib as _hashlib

        for u in users:
            secs_to_task: Optional[int] = None
            secs_to_timer: Optional[int] = None
            if u.first_task_at:
                secs_to_task = int((u.first_task_at - u.created_at).total_seconds())
            if u.first_timer_started_at:
                secs_to_timer = int(
                    (u.first_timer_started_at - u.created_at).total_seconds()
                )

            if u.onboarding_completed_at is not None:
                completed_onboarding += 1
            if secs_to_task is not None and secs_to_task <= 60:
                first_task_within_60s += 1
            if secs_to_timer is not None and secs_to_timer <= 180:
                first_timer_within_180s += 1
            if u.d1_return_at is not None:
                returned_d1 += 1

            met_north_star = (
                secs_to_task is not None
                and secs_to_timer is not None
                and secs_to_task <= 180
                and secs_to_timer <= 180
            )
            if u.first_task_at and u.first_timer_started_at:
                n_eligible += 1
                if met_north_star:
                    n_met += 1

            rows.append({
                "user_id": u.user_id,
                "email_hash": _hashlib.sha256(
                    (u.email or "").encode("utf-8")
                ).hexdigest()[:12],
                "created_at": u.created_at.isoformat(),
                "onboarding_completed_at": (
                    u.onboarding_completed_at.isoformat()
                    if u.onboarding_completed_at else None
                ),
                "first_task_at": (
                    u.first_task_at.isoformat() if u.first_task_at else None
                ),
                "first_timer_started_at": (
                    u.first_timer_started_at.isoformat()
                    if u.first_timer_started_at else None
                ),
                "d1_return_at": (
                    u.d1_return_at.isoformat() if u.d1_return_at else None
                ),
                "seconds_to_first_task": secs_to_task,
                "seconds_to_first_timer": secs_to_timer,
                "met_north_star": met_north_star,
            })

        return {
            "calculated_at": now_utc().isoformat(),
            "north_star": {
                "metric": "task_created+timer_started within 3min",
                "n_eligible": n_eligible,
                "n_met": n_met,
                "rate": (n_met / n_eligible) if n_eligible > 0 else None,
            },
            "funnel": {
                "signed_up": signed_up,
                "completed_onboarding": completed_onboarding,
                "first_task_within_60s": first_task_within_60s,
                "first_timer_within_180s": first_timer_within_180s,
                "returned_d1": returned_d1,
            },
            "users": rows,
            "research_integrity_note": (
                "Population 2 (product research) only. Per VT-15/VT-16, do NOT "
                "feed these statistics into H1 hypothesis-research analyses. "
                "Report opt-out rate alongside any aggregate finding."
            ),
        }
    finally:
        set_current_user_id(original_uid)
