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

        # Per-user aggregates — one query per user is fine at n<20.
        rows: list[dict[str, Any]] = []
        for u in users:
            last_task_mod = (
                db.query(func.max(Task.last_modified_at))
                .filter(Task.user_id == u.user_id)
                .filter(Task.voided_at.is_(None))
                .scalar()
            )
            last_session_end = (
                db.query(func.max(StopwatchSession.end_time_utc))
                .filter(StopwatchSession.user_id == u.user_id)
                .scalar()
            )
            last_activity = max(
                (t for t in (last_task_mod, last_session_end) if t is not None),
                default=None,
            )
            task_total = (
                db.query(func.count(Task.task_id))
                .filter(Task.user_id == u.user_id)
                .filter(Task.voided_at.is_(None))
                .scalar()
                or 0
            )
            executed_count = (
                db.query(func.count(Task.task_id))
                .filter(Task.user_id == u.user_id)
                .filter(Task.voided_at.is_(None))
                .filter(Task.state == TaskState.EXECUTED)
                .scalar()
                or 0
            )
            first_task_created = (
                db.query(func.min(Task.created_at))
                .filter(Task.user_id == u.user_id)
                .filter(Task.voided_at.is_(None))
                .scalar()
            )
            first_executed = (
                db.query(func.min(Task.last_modified_at))
                .filter(Task.user_id == u.user_id)
                .filter(Task.voided_at.is_(None))
                .filter(Task.state == TaskState.EXECUTED)
                .scalar()
            )
            tutorial_status = (
                "completed"
                if u.tutorial_completed_at
                else "skipped"
                if u.tutorial_skipped_at
                else "pending"
            )
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
                }
            )

        non_op_rows = [r for r in rows if not r["is_operator"]]
        funnel = {
            "signed_up": len(non_op_rows),
            "onboarded": sum(1 for r in non_op_rows if r["onboarded_at"]),
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
