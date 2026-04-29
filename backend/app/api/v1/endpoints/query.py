"""Task query endpoint."""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
import logging

from app.api.deps import get_db
from app.db.models import Task, TaskState, StopwatchSession
from app.db.scoping import get_current_user_id
from app.utils.time_utils import to_utc, to_local
from app.utils.redis_client import RedisClient

router = APIRouter()
logger = logging.getLogger(__name__)

# Hard ceiling — prevents browser death on "All time" at scale.
ROW_LIMIT = 1000


@router.get("/tasks/query")
def query_tasks(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    days: int = Query(1, ge=1, le=62, description="Number of days starting at `date` to include (default 1). 62 cap = ~2 months, enough for the calendar month view."),
    date_from: Optional[str] = Query(None, description="Range start (YYYY-MM-DD). Takes precedence over `date` when set."),
    date_to: Optional[str] = Query(None, description="Range end inclusive (YYYY-MM-DD). Defaults to today if date_from is set without date_to."),
    category: Optional[str] = Query(None, description="Filter by category"),
    state: Optional[str] = Query("planned", description="Filter by state. Pass 'all' to return every state (PLANNED, EXECUTING, PAUSED, EXECUTED, SKIPPED, DELETED). The 'all' sentinel skips the state filter entirely — it is not a real TaskState enum value."),
    initiation_status: Optional[str] = Query(None, description="Filter by initiation_status (e.g. system_error, retroactive)"),
    limit: int = Query(ROW_LIMIT, ge=1, le=ROW_LIMIT, description=f"Max rows returned (hard cap {ROW_LIMIT})."),
    db: Session = Depends(get_db)
):
    """
    Query tasks with optional filters.

    Returns tasks matching filters, ordered by start time descending.

    **Range modes** (checked in priority order):
    1. ``date_from`` set → range query ``[date_from, date_to]`` inclusive.
       ``date_to`` defaults to today when omitted.
    2. ``date`` set → window query ``[date, date + days)`` (legacy single-day
       and calendar-month mode).
    3. Neither set → no date filter (all tasks matching other filters).
    """
    try:
        query = db.query(Task)

        # Filter by state — 'all' sentinel skips the filter.
        if state and state.lower() != "all":
            try:
                task_state = TaskState(state)
                query = query.filter(Task.state == task_state)
            except ValueError:
                pass  # Invalid state, skip filter

        # Date filtering: date_from/date_to takes precedence over date/days.
        # Times stored as naive datetimes representing Cairo local (TIMEZONE
        # CONTRACT). Filter comparisons use to_utc which localises the naive
        # midnight to Cairo then converts to UTC — matching the storage format.
        if date_from:
            try:
                start_dt = datetime.strptime(date_from, "%Y-%m-%d")
                day_start = to_utc(start_dt)
                if date_to:
                    end_dt = datetime.strptime(date_to, "%Y-%m-%d")
                else:
                    end_dt = datetime.utcnow()
                # +1 day for inclusive end
                day_end = to_utc(end_dt + timedelta(days=1))
                query = query.filter(
                    Task.planned_start_utc >= day_start,
                    Task.planned_start_utc < day_end,
                )
            except ValueError:
                pass  # Invalid date format, skip filter
        elif date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
                day_start = to_utc(target_date)
                day_end = to_utc(target_date + timedelta(days=days))
                query = query.filter(
                    Task.planned_start_utc >= day_start,
                    Task.planned_start_utc < day_end
                )
            except ValueError:
                pass  # Invalid date format, skip filter

        # Filter by category
        if category:
            query = query.filter(Task.category == category)

        # Filter by initiation_status
        if initiation_status:
            query = query.filter(Task.initiation_status == initiation_status)

        # Combined count + page in one SQL pass via window function
        # (me_cache 2026-04-29 latency sweep). The previous shape did
        # `query.count()` then `query.all()` — two Cairo→eu-west-1
        # round-trips at ~600ms each. `count() OVER ()` ships the total
        # alongside every row in a single query. Standard Postgres
        # window function; SQLite (test backend) supports it from 3.25+
        # which the project requires for other features.
        #
        # Order by start time descending (newest first for table view).
        # Legacy callers that relied on ascending order use date/days
        # mode which naturally returns a small window — reordering is
        # harmless.
        rows = (
            query
            .add_columns(func.count().over().label("total_count"))
            .order_by(Task.planned_start_utc.desc())
            .limit(limit)
            .all()
        )
        if rows:
            # Each row is a (Task, total_count) tuple per add_columns.
            tasks = [r[0] for r in rows]
            total_count = int(rows[0][1])
        else:
            tasks = []
            total_count = 0
        truncated = total_count > limit

        # Batch-load session aggregates to avoid N+1.
        task_ids = [t.task_id for t in tasks]
        session_agg: dict[str, dict] = {}
        if task_ids:
            agg_rows = (
                db.query(
                    StopwatchSession.task_id,
                    func.sum(StopwatchSession.total_paused_minutes).label("total_paused"),
                    func.count(StopwatchSession.session_id).label("session_count"),
                    func.max(StopwatchSession.task_completion_percentage).label("task_completion_percentage"),
                )
                .filter(StopwatchSession.task_id.in_(task_ids))
                .group_by(StopwatchSession.task_id)
                .all()
            )
            for row in agg_rows:
                session_agg[row.task_id] = {
                    "total_paused_minutes": round(row.total_paused or 0, 1),
                    "pause_count": row.session_count or 0,
                    "task_completion_percentage": row.task_completion_percentage,
                }

        task_list = []
        for t in tasks:
            agg = session_agg.get(t.task_id, {})
            task_list.append({
                "task_id": t.task_id,
                "title": t.title,
                "description": t.description,
                "start": to_local(t.planned_start_utc).isoformat() if t.planned_start_utc else None,
                "end": to_local(t.planned_end_utc).isoformat() if t.planned_end_utc else None,
                "state": t.state.value if hasattr(t.state, 'value') else str(t.state),
                "category": t.category,
                "initiation_status": t.initiation_status,
                "session_index_in_day": t.session_index_in_day if t.session_index_in_day is not None else 0,
                "pre_task_readiness": t.pre_task_readiness,
                "post_task_reflection": t.post_task_reflection,
                "planned_duration_minutes": t.planned_duration_minutes,
                "executed_duration_minutes": t.executed_duration_minutes,
                "duration_delta_minutes": t.duration_delta_minutes,
                "executed_start": to_local(t.executed_start_utc).isoformat() if t.executed_start_utc else None,
                "executed_end": to_local(t.executed_end_utc).isoformat() if t.executed_end_utc else None,
                "voided_at": to_local(t.voided_at).isoformat() if t.voided_at else None,
                # Extended fields for CSV export / research schema
                "discrepancy_score": t.discrepancy_score,
                "signed_discrepancy": t.signed_discrepancy,
                "initiation_delay_minutes": t.initiation_delay_minutes,
                "total_paused_minutes": agg.get("total_paused_minutes", 0),
                "pause_count": agg.get("pause_count", 0),
                "task_completion_percentage": agg.get("task_completion_percentage"),
                "voided_reason": t.voided_reason,
                "notion_page_id": t.notion_page_id,
                # Loop 11 deadline binding fields (alembic 033).
                "deadline_id": t.deadline_id,
                "deadline_match_source": t.deadline_match_source,
                "deadline_match_confidence": t.deadline_match_confidence,
                # Workstream 1 LLM enrichment (alembic 036, 2026-04-28).
                # Without these, the LlmEnrichmentChip cannot render.
                "llm_parse_status": t.llm_parse_status,
                "llm_inferred_deadline_id": t.llm_inferred_deadline_id,
                "llm_deadline_match_confidence": t.llm_deadline_match_confidence,
                "llm_deadline_candidates": t.llm_deadline_candidates,
                "llm_priority": t.llm_priority,
                "llm_binding_rejected_at": (
                    to_local(t.llm_binding_rejected_at).isoformat()
                    if t.llm_binding_rejected_at else None
                ),
                # Trust-not-rewrite contract (alembic 039, 2026-04-28).
                # Set by llm_enrichment when the LLM disagrees with an
                # existing user/heuristic binding. Chip renders
                # "Possible better match" when present.
                "llm_alternative_suggestion": t.llm_alternative_suggestion,
            })

        return {"tasks": task_list, "total": total_count, "truncated": truncated}

    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        return {"tasks": [], "total": 0, "truncated": False}


@router.get("/tasks/last")
def get_last_task(db: Session = Depends(get_db)):
    """
    Return the most recently created, rescheduled, or completed task (1-hour window).

    Used by the agent to resolve follow-up corrections like "actually make that
    next week" without requiring the user to repeat the task name or ID.
    Returns 404 if no task was operated in the last hour.
    """
    redis = RedisClient()
    last = redis.get_last_task(user_id=str(get_current_user_id() or 1))
    if not last:
        raise HTTPException(
            status_code=404,
            detail="No task operated in the last hour. Please specify the task.",
        )
    # Verify task still exists and isn't voided
    task = db.query(Task).filter(Task.task_id == last["task_id"]).first()
    if not task or task.voided_at is not None:
        raise HTTPException(status_code=404, detail="Last task no longer exists.")
    return {
        "task_id": task.task_id,
        "title": task.title,
        "state": task.state.value if hasattr(task.state, "value") else str(task.state),
        "start": to_local(task.planned_start_utc).isoformat() if task.planned_start_utc else None,
        "end": to_local(task.planned_end_utc).isoformat() if task.planned_end_utc else None,
    }
