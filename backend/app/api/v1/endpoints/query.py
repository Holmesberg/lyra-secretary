"""Task query endpoint."""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
import logging

from app.api.deps import get_db
from app.db.models import Task, TaskExecutionCorrection, TaskState, StopwatchSession
from app.db.scoping import get_current_user_id
from app.utils.time_utils import to_utc, to_local
from app.utils.redis_client import RedisClient
from app.utils.tasks_range_cache import get_cached_range, set_cached_range

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
    include_voided: bool = Query(False, description="Include soft-voided rows. Default false (per voided_at_guard discipline). Audit/admin tools opt in by setting true."),
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
        # Cache fast-path for range queries (date_from set). The /pulse
        # v2 dashboard fires a 14-day range every page load to power
        # the Recovery + System Insight charts; this is the single
        # heaviest query on first paint. 60s TTL is invisible to the
        # chart aggregations (they resample at day-boundaries client-
        # side) and busts on TaskManager.create_task. See
        # `app/utils/tasks_range_cache.py` for the full rationale.
        # Only cache the canonical "state=all + no extra filters" shape
        # /pulse uses — otherwise we'd thrash the cache on every variant.
        cache_eligible = (
            date_from is not None
            and (state is None or state == "all")
            and category is None
            and initiation_status is None
            and limit == ROW_LIMIT
            and include_voided is False
        )
        if cache_eligible:
            uid = get_current_user_id()
            if uid is not None:
                effective_to = date_to or datetime.utcnow().strftime("%Y-%m-%d")
                cached = get_cached_range(uid, date_from, effective_to)
                if cached is not None:
                    return cached

        query = db.query(Task)

        # voided_at_guard discipline (per feedback memory): every Task
        # query/mutation must filter `voided_at IS NULL` by default.
        # Voiding doesn't change state — state-only filters leak voided
        # rows into research analytics + UI surfaces. The /v1/tasks/query
        # endpoint historically lacked this filter, leaking voided rows
        # to /pulse aggregations + /today + /table. Audit-flagged
        # 2026-04-30. Opt-in `include_voided=true` for admin/audit tools.
        if not include_voided:
            query = query.filter(Task.voided_at.is_(None))

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
        # Batch-load deadline titles for any tasks that have a binding.
        # Operator request 2026-05-01: surface the bound deadline title
        # in /today so the user can verify the explicit/confirmed binding
        # landed on the right deadline. Single SQL — same trick as session_agg.
        deadline_titles: dict[str, str] = {}
        bound_deadline_ids = [t.deadline_id for t in tasks if t.deadline_id]
        if bound_deadline_ids:
            from app.db.models import Deadline
            for did, title in (
                db.query(Deadline.deadline_id, Deadline.title)
                .filter(Deadline.deadline_id.in_(bound_deadline_ids))
                .all()
            ):
                deadline_titles[did] = title
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

        latest_correction: dict[str, TaskExecutionCorrection] = {}
        if task_ids:
            correction_rows = (
                db.query(TaskExecutionCorrection)
                .filter(TaskExecutionCorrection.task_id.in_(task_ids))
                .order_by(
                    TaskExecutionCorrection.task_id,
                    TaskExecutionCorrection.created_at.desc(),
                )
                .all()
            )
            for row in correction_rows:
                latest_correction.setdefault(row.task_id, row)

        task_list = []
        for t in tasks:
            agg = session_agg.get(t.task_id, {})
            correction = latest_correction.get(t.task_id)
            effective_executed_end = (
                correction.corrected_executed_end_utc
                if correction is not None
                else t.executed_end_utc
            )
            effective_executed_duration = (
                correction.corrected_executed_duration_minutes
                if correction is not None
                else t.executed_duration_minutes
            )
            effective_delta = (
                t.planned_duration_minutes - effective_executed_duration
                if effective_executed_duration is not None
                else None
            )
            execution_duration_provenance = (
                "retroactive"
                if correction is not None or t.initiation_status == "retroactive"
                else "observed"
            )
            task_list.append({
                "task_id": t.task_id,
                "title": t.title,
                "description": t.description,
                "start": to_local(t.planned_start_utc).isoformat() if t.planned_start_utc else None,
                "end": to_local(t.planned_end_utc).isoformat() if t.planned_end_utc else None,
                "state": t.state.value if hasattr(t.state, 'value') else str(t.state),
                "category": t.category,
                "is_anchor": t.is_anchor,
                "rct_arm": t.rct_arm,
                "initiation_status": t.initiation_status,
                "session_index_in_day": t.session_index_in_day if t.session_index_in_day is not None else 0,
                "pre_task_readiness": t.pre_task_readiness,
                "post_task_reflection": t.post_task_reflection,
                "planned_duration_minutes": t.planned_duration_minutes,
                "executed_duration_minutes": t.executed_duration_minutes,
                "duration_delta_minutes": t.duration_delta_minutes,
                "executed_start": to_local(t.executed_start_utc).isoformat() if t.executed_start_utc else None,
                "executed_end": to_local(t.executed_end_utc).isoformat() if t.executed_end_utc else None,
                "effective_executed_duration_minutes": effective_executed_duration,
                "effective_duration_delta_minutes": effective_delta,
                "effective_executed_end": (
                    to_local(effective_executed_end).isoformat()
                    if effective_executed_end else None
                ),
                "execution_duration_provenance": execution_duration_provenance,
                "execution_correction_id": (
                    correction.correction_id if correction is not None else None
                ),
                "voided_at": to_local(t.voided_at).isoformat() if t.voided_at else None,
                # Extended fields for CSV export / research schema
                "discrepancy_score": t.discrepancy_score,
                "signed_discrepancy": t.signed_discrepancy,
                "initiation_delay_minutes": t.initiation_delay_minutes,
                "total_paused_minutes": agg.get("total_paused_minutes", 0),
                "pause_count": agg.get("pause_count", 0),
                "task_completion_percentage": agg.get("task_completion_percentage"),
                "voided_reason": t.voided_reason,
                # Loop 11 deadline binding fields (alembic 033).
                "deadline_id": t.deadline_id,
                "deadline_match_source": t.deadline_match_source,
                "deadline_match_confidence": t.deadline_match_confidence,
                # Operator request 2026-05-01: bound deadline title so
                # /today + /calendar can render an inline chip
                # ("↳ Lab 8 due Fri") proving the binding landed.
                "deadline_title": (
                    deadline_titles.get(t.deadline_id)
                    if t.deadline_id else None
                ),
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

        response_payload = {
            "tasks": task_list,
            "total": total_count,
            "truncated": truncated,
        }
        # Cache the canonical-shape range response (computed lazily so
        # the cache miss path stays simple). Bust on TaskManager.create_task.
        if cache_eligible:
            uid = get_current_user_id()
            if uid is not None:
                effective_to = date_to or datetime.utcnow().strftime("%Y-%m-%d")
                set_cached_range(uid, date_from, effective_to, response_payload)
        return response_payload

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
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    last = redis.get_last_task(user_id=str(uid))
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
