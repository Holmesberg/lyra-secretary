"""Task management endpoints."""
import json
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.api.deps import get_db
from app.schemas.task import (
    TaskCreateRequest,
    TaskCreateResponse,
    TaskRescheduleRequest,
    TaskRescheduleResponse,
    TaskDeleteRequest,
    TaskDeleteResponse,
    TaskDetail,
    TaskVoidRequest,
    TaskVoidResponse,
    MarkAbandonedRequest,
    MarkAbandonedResponse,
    SwapRequest,
    SwapResponse,
    ConflictInfo,
    LlmConfirmRequest,
    LlmConfirmResponse,
    LlmRejectRequest,
    LlmRejectResponse,
)
from app.db.models import TaskState
from app.utils.time_utils import now_utc as _now_utc
from app.services.task_manager import TaskManager
from app.services.stopwatch_manager import StopwatchManager, NoActiveStopwatchError
from app.services.notion_client import NotionClient
from app.utils.redis_client import RedisClient
from app.core.exceptions import ImmutableTaskError
from app.db.models import Task
from app.utils.time_utils import to_local

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/create", response_model=TaskCreateResponse)
def create_task(
    request: TaskCreateRequest,
    db: Session = Depends(get_db),
    x_idempotency_key: Optional[str] = Header(None)
) -> TaskCreateResponse:
    """
    Create a new task.
    
    If conflicts detected and force=False, returns conflicts without creating.
    If force=True or no conflicts, creates task and syncs to Notion.
    
    Optional: Pass X-Idempotency-Key header to prevent duplicate creates
    within a 30-second window.
    """
    try:
        # FIX 4: Idempotency check
        redis = RedisClient()
        if x_idempotency_key:
            cached = redis.check_idempotency(x_idempotency_key)
            if cached:
                logger.info(f"Idempotency hit for key {x_idempotency_key}")
                return TaskCreateResponse(**json.loads(cached))

        manager = TaskManager(db)
        
        task, result, notion_synced = manager.create_task(
            title=request.title,
            start=request.start,
            end=request.end,
            category=request.category,
            description=request.description,
            state=request.state,
            source=request.source,
            confidence_score=request.confidence_score,
            force_conflicts=request.force,
            deadline_id=request.deadline_id,
            nudge_decision=request.nudge_decision,
            nudge_suggested_duration_minutes=request.nudge_suggested_duration_minutes,
            nudge_bias_factor=request.nudge_bias_factor,
            nudge_sample_size=request.nudge_sample_size,
            nudge_viewed_at=request.nudge_viewed_at,
        )

        if task is None:
            conflict_info: list[ConflictInfo] = []
            for c in result.hard:
                conflict_info.append(ConflictInfo(
                    task_id=c.task_id, title=c.title,
                    start=to_local(c.planned_start_utc),
                    end=to_local(c.planned_end_utc),
                    state=c.state, gate_id="active_overlap",
                ))
            for c in result.soft_overlap:
                gate = "executing_overlap" if c.state == TaskState.EXECUTING else "planned_overlap"
                conflict_info.append(ConflictInfo(
                    task_id=c.task_id, title=c.title,
                    start=to_local(c.planned_start_utc),
                    end=to_local(c.planned_end_utc),
                    state=c.state, gate_id=gate,
                ))
            for c in result.soft_duplicate:
                conflict_info.append(ConflictInfo(
                    task_id=c.task_id, title=c.title,
                    start=to_local(c.planned_start_utc),
                    end=to_local(c.planned_end_utc),
                    state=c.state, gate_id="duplicate_title",
                ))

            severity = result.severity()
            return TaskCreateResponse(
                task_id=None,
                created=False,
                notion_synced=False,
                conflicts=conflict_info,
                # HARD never overridable; SOFT is.
                can_proceed=(severity == "soft"),
                severity=severity,
                soft_reasons=result.soft_reasons(),
            )

        assert task is not None  # guaranteed by the None check above
        response = TaskCreateResponse(
            task_id=task.task_id,
            created=True,
            notion_synced=notion_synced,
            conflicts=[],
            can_proceed=True,
            severity=None,
            soft_reasons=[],
        )

        # FIX 4: Cache response for idempotency
        if x_idempotency_key:
            redis.set_idempotency(x_idempotency_key, response.model_dump_json())
        
        return response
        
    except ValueError as e:
        error_msg = str(e)
        if "start_in_past" in error_msg:
            raise HTTPException(
                status_code=400,
                detail={"error": "start_in_past", "message": "Task start time is in the past. Did you mean tomorrow?"}
            )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Task creation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/reschedule", response_model=TaskRescheduleResponse)
def reschedule_task(
    request: TaskRescheduleRequest,
    db: Session = Depends(get_db)
) -> TaskRescheduleResponse:
    """Reschedule task (preserves TaskID)."""
    try:
        manager = TaskManager(db)
        
        task, conflicts = manager.reschedule_task(
            task_id=request.task_id,
            new_start=request.new_start,
            new_end=request.new_end,
            title=request.title,
            category=request.category,
            description=request.description,
            deadline_id=request.deadline_id,
        )
        
        conflict_info = [
            ConflictInfo(
                task_id=c.task_id,
                title=c.title,
                start=to_local(c.planned_start_utc),
                end=to_local(c.planned_end_utc),
                state=c.state
            )
            for c in conflicts
        ]

        return TaskRescheduleResponse(
            task_id=task.task_id,
            rescheduled=True,
            new_start=to_local(task.planned_start_utc),
            new_end=to_local(task.planned_end_utc),
            conflicts=conflict_info
        )
        
    except (ImmutableTaskError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Reschedule error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/delete", response_model=TaskDeleteResponse)
def delete_task(
    request: TaskDeleteRequest,
    db: Session = Depends(get_db)
) -> TaskDeleteResponse:
    """Delete task (soft delete)."""
    try:
        manager = TaskManager(db)
        task = manager.delete_task(request.task_id)
        
        return TaskDeleteResponse(
            task_id=task.task_id,
            deleted=True
        )
        
    except ImmutableTaskError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Delete error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tasks/{task_id}/void", response_model=TaskVoidResponse)
def void_task(
    task_id: str,
    request: TaskVoidRequest,
    db: Session = Depends(get_db),
) -> TaskVoidResponse:
    """
    Void a task (any non-DELETED state) — Phase 3.2 redesign.

    The row is preserved (immutable history) but `voided_at` is stamped
    and analytics queries exclude it. `voided_reason` must be one of the
    VOID_REASONS enum; `void_reason_detail` is required when
    voided_reason='other'. EXECUTED tasks still get
    initiation_status='system_error' for backward compatibility with
    existing analytics filters.
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.state == TaskState.DELETED:
        raise HTTPException(
            status_code=400,
            detail="Cannot void a DELETED task",
        )
    previous_state = task.state.value if hasattr(task.state, "value") else str(task.state)
    previous_status = task.initiation_status
    task.voided_at = _now_utc()
    task.voided_reason = request.voided_reason
    task.void_reason_detail = request.void_reason_detail
    # Preserve legacy EXECUTED→system_error mapping so old analytics
    # filters that test initiation_status still exclude the row.
    if task.state == TaskState.EXECUTED:
        task.initiation_status = "system_error"
    db.commit()
    db.refresh(task)

    # Close any unclosed stopwatch session bound to this task and clear
    # the user's Redis active/pause keys. Without this, the frontend
    # /stopwatch/status banner keeps showing a PAUSED timer for the
    # voided task indefinitely (CO-block 65h incident, Apr 11). If the
    # cleanup itself errors we still return success — _get_active has a
    # defensive self-heal that will catch it on the next poll.
    try:
        StopwatchManager(db).void_cleanup(task.task_id)
    except Exception as e:
        logger.warning(
            f"void_cleanup failed for {task.task_id}: {e}. The _get_active "
            f"self-heal will recover on the next status poll."
        )

    return TaskVoidResponse(
        task_id=task.task_id,
        voided=True,
        previous_state=previous_state,
        previous_initiation_status=previous_status,
        voided_at=to_local(task.voided_at),
        voided_reason=task.voided_reason,
        void_reason_detail=task.void_reason_detail,
    )


@router.post("/tasks/{task_id}/mark-abandoned", response_model=MarkAbandonedResponse)
def mark_abandoned(
    task_id: str,
    request: MarkAbandonedRequest = None,
    db: Session = Depends(get_db),
) -> MarkAbandonedResponse:
    """
    Skip an EXECUTING, PAUSED, or PLANNED task (→ SKIPPED).

    EXECUTING/PAUSED: initiation_status='abandoned' (started but not finished).
    PLANNED: initiation_status='user_skipped' (explicitly declined before starting).
    Both preserve the task as a cascade data point.
    """
    if request is None:
        request = MarkAbandonedRequest()

    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.voided_at is not None:
        raise HTTPException(status_code=400, detail="Cannot skip a voided task")
    if task.state not in (TaskState.EXECUTING, TaskState.PAUSED, TaskState.PLANNED):
        raise HTTPException(
            status_code=400,
            detail=f"Only EXECUTING, PAUSED, or PLANNED tasks can be skipped (current state: {task.state})",
        )

    previous = task.state
    was_active = task.state in (TaskState.EXECUTING, TaskState.PAUSED)
    is_planned = task.state == TaskState.PLANNED
    default_reason = "user_skipped" if is_planned else "abandoned mid-session"
    try:
        manager = TaskManager(db)
        task = manager.skip_task(task_id, reason=request.reason or default_reason)
        task.initiation_status = "user_skipped" if is_planned else "abandoned"
        db.commit()
        db.refresh(task)
    except ImmutableTaskError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Close any unclosed stopwatch session and clear Redis active/pause
    # keys for EXECUTING/PAUSED tasks. Without this the frontend banner
    # keeps showing a PAUSED timer for the now-SKIPPED task (ghost banner
    # bug, Apr 12). Same pattern as void_task — _get_active self-heal is
    # the backup if this fails.
    if was_active:
        try:
            StopwatchManager(db).void_cleanup(task.task_id)
        except Exception as e:
            logger.warning(
                f"stopwatch cleanup failed for mark-abandoned {task.task_id}: {e}. "
                f"_get_active self-heal will recover on next status poll."
            )

    return MarkAbandonedResponse(
        task_id=task.task_id,
        abandoned=True,
        previous_state=previous,
        new_state=task.state,
    )


@router.post("/tasks/swap", response_model=SwapResponse)
def swap_tasks(
    request: SwapRequest,
    db: Session = Depends(get_db),
) -> SwapResponse:
    """
    Atomically swap a SKIPPED task and a PLANNED task.

    The SKIPPED task is reactivated as PLANNED at the PLANNED task's time slot.
    The PLANNED task is marked SKIPPED (initiation_status='user_skipped').
    Either task_id can be the SKIPPED or PLANNED one — order doesn't matter.
    """
    try:
        manager = TaskManager(db)
        reactivated, skipped = manager.swap_tasks(request.task_a_id, request.task_b_id)
        return SwapResponse(
            swapped=True,
            reactivated_task_id=reactivated.task_id,
            skipped_task_id=skipped.task_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Swap error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/schedule/clear")
def clear_schedule(
    db: Session = Depends(get_db),
) -> dict:
    """
    Delete all PLANNED tasks from the schedule.

    Blocked with 400 if a stopwatch session is active — the user must stop
    the timer first so the session is properly closed with reflection.
    EXECUTING / PAUSED / EXECUTED / SKIPPED tasks are never touched.
    """
    sw = StopwatchManager(db)
    status = sw.get_status()
    if status.get("active"):
        task_title = status.get("task_title", "current task")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "active_timer",
                "message": f"Stop timer for {task_title} before clearing schedule.",
            },
        )

    manager = TaskManager(db)
    planned = db.query(Task).filter(Task.state == TaskState.PLANNED).all()
    deleted_ids = []
    for t in planned:
        try:
            manager.delete_task(t.task_id)
            deleted_ids.append(t.task_id)
        except Exception as e:
            logger.warning(f"clear_schedule: could not delete {t.task_id}: {e}")

    return {
        "cleared": True,
        "planned_deleted": len(deleted_ids),
    }


@router.post("/tasks/{task_id}/sync")
def sync_task_to_notion(
    task_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """
    Force a Notion sync for a specific task.

    Use to backfill tasks created before the timezone pipeline fix (LYR-015),
    or to recover tasks that failed to sync due to transient Notion API errors.
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        notion = NotionClient()
        page_id = notion.sync_task(task, db=db)
        return {
            "task_id": task_id,
            "synced": True,
            "notion_page_id": page_id or task.notion_page_id,
        }
    except Exception as e:
        logger.error(f"Manual Notion sync failed for {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Notion sync failed: {e}")


@router.post("/tasks/{task_id}/llm-confirm", response_model=LlmConfirmResponse)
def confirm_llm_binding(
    task_id: str,
    request: LlmConfirmRequest,
    db: Session = Depends(get_db),
    x_idempotency_key: Optional[str] = Header(None),
) -> LlmConfirmResponse:
    """Magic-for-alpha Workstream 1 (2026-04-28). User clicked "keep" or
    "use this" on the LLM-suggested deadline / priority chip. Copy the
    selected suggestions into the canonical task fields.

    Tier flow:
      - Tier 1 (confidence ≥ 0.85): chip pre-selected; user clicks
        "keep" → request.chosen_deadline_id is None → use the LLM's
        top candidate (task.llm_inferred_deadline_id).
      - Tier 2 (0.45 ≤ confidence < 0.85): user picks one option;
        request.chosen_deadline_id is the picked deadline_id → must
        be in task.llm_deadline_candidates.

    Guardrail #2: never silently auto-bind. The user must POST here
    for the canonical deadline_id to change. The llm_inferred_*
    columns persist as audit trail.

    Idempotency (P1 stress-test 2026-04-28): pass an X-Idempotency-Key
    header to deduplicate double-taps within a 30-second window. Mirrors
    the existing /create pattern. Without this, a flaky network +
    eager user double-tap can cause two writes to deadline_match_source
    interleaving with async LLM enrichment.
    """
    redis = RedisClient()
    if x_idempotency_key:
        cached = redis.check_idempotency(f"llm_confirm:{task_id}:{x_idempotency_key}")
        if cached:
            logger.info(
                "llm-confirm idempotency hit for task=%s key=%s",
                task_id, x_idempotency_key,
            )
            return LlmConfirmResponse(**json.loads(cached))

    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.voided_at is not None:
        raise HTTPException(status_code=400, detail="Cannot modify voided task")

    deadline_id_after: Optional[str] = task.deadline_id
    priority_set = False

    if "deadline" in request.accepted_fields:
        # Resolve which deadline_id to commit. Either the user's pick
        # (Tier 2) or the LLM's top suggestion (Tier 1).
        target_deadline_id = (
            request.chosen_deadline_id
            if request.chosen_deadline_id is not None
            else task.llm_inferred_deadline_id
        )
        if target_deadline_id is None:
            raise HTTPException(
                status_code=400,
                detail="No deadline to bind: llm_inferred_deadline_id is null and no chosen_deadline_id provided",
            )
        # Validate the chosen deadline is in the candidate list (Tier 2)
        # OR matches the top candidate (Tier 1) OR matches the alternative
        # suggestion (trust-not-rewrite Switch path, 2026-04-28). Defensive
        # — prevents a malicious / stale frontend from binding to a
        # deadline the LLM never proposed.
        candidates = task.llm_deadline_candidates or []
        alt = task.llm_alternative_suggestion or {}
        in_candidates = any(c.get("deadline_id") == target_deadline_id for c in candidates)
        in_alt = alt.get("deadline_id") == target_deadline_id
        if not (in_candidates or in_alt):
            raise HTTPException(
                status_code=400,
                detail="chosen_deadline_id not in llm_deadline_candidates or llm_alternative_suggestion",
            )
        # Validate the deadline belongs to the user and is bindable
        # (mirror the existing TaskManager._validate_bindable_deadline guard).
        from app.db.models import Deadline
        d = db.query(Deadline).filter(
            Deadline.deadline_id == target_deadline_id,
            Deadline.user_id == task.user_id,
            Deadline.voided_at.is_(None),
            Deadline.state.in_(("planned", "active")),
        ).first()
        if d is None:
            raise HTTPException(
                status_code=400,
                detail="Deadline not bindable (not found, voided, or terminal)",
            )
        task.deadline_id = target_deadline_id
        # Look up confidence from candidates (Tier 1/2) or alt (Switch
        # path). Fall back to alt.confidence when candidates didn't
        # carry the chosen id.
        confidence = next(
            (c.get("confidence") for c in candidates
             if c.get("deadline_id") == target_deadline_id),
            None,
        )
        if confidence is None and in_alt:
            confidence = alt.get("confidence")
        task.deadline_match_confidence = confidence
        # Switch path uses 'user_corrected' (operator's override priority
        # list — user actively switched after seeing both); Tier 1/2 keep
        # the existing 'llm_auto_confirmed'.
        task.deadline_match_source = "user_corrected" if in_alt else "llm_auto_confirmed"
        # Clear the alternative now that the user resolved it
        task.llm_alternative_suggestion = None
        # Auto-transition the deadline to active if currently planned
        # (mirror TaskManager.create_task's pass 1 behavior).
        if d.state == "planned":
            d.state = "active"
        deadline_id_after = target_deadline_id

    # Priority commit deferred — Task.priority column not yet shipped.
    # Once it ships (Workstream 4 polish or follow-up), this branch
    # populates it. For now, we acknowledge the intent without effect.
    if "priority" in request.accepted_fields and task.llm_priority is not None:
        # task.priority = task.llm_priority  # uncomment when column exists
        priority_set = True

    db.commit()
    response = LlmConfirmResponse(
        task_id=task.task_id,
        deadline_id_after=deadline_id_after,
        deadline_match_source_after=task.deadline_match_source,
        priority_set=priority_set,
    )
    if x_idempotency_key:
        redis.set_idempotency(
            f"llm_confirm:{task_id}:{x_idempotency_key}",
            response.model_dump_json(),
            ttl_seconds=30,
        )
    return response


@router.post("/tasks/{task_id}/reject-llm-binding", response_model=LlmRejectResponse)
def reject_llm_binding(
    task_id: str,
    db: Session = Depends(get_db),
) -> LlmRejectResponse:
    """User clicked 'Not relevant' / 'None of these' on the binding chip.

    Records the rejection (`llm_binding_rejected_at = now()`) so the chip
    stops rendering. Then, source-aware unbind:

      - If `deadline_match_source` is system-auto — `heuristic_*`,
        `llm_auto_confirmed`, or legacy `parser_auto` — also clear
        `task.deadline_id` and reset `task.deadline_match_source` to
        NULL. The user is rejecting a binding the SYSTEM made, so
        "Not relevant" must actually unbind.
      - If source is `user_explicit` or `manual_user`, leave the
        binding alone — user owns it; the chip rejection only stops
        the LLM suggestion from re-appearing.

    Bug fix 2026-05-01 (operator: "I clicked no deadline, still
    binded"): prior version only set the rejection flag and left
    deadline_id intact for ALL sources, so heuristic-auto bindings
    quietly persisted after explicit user rejection.

    `llm_inferred_*` fields stay populated (audit trail) so future
    analysis can join llm_inferred_deadline_id × llm_binding_rejected_at
    × deadline_match_source for precision/recall by binding origin.
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.llm_binding_rejected_at = _now_utc()

    src = task.deadline_match_source
    SYSTEM_AUTO_SOURCES = {
        "heuristic_exact_title",
        "heuristic_startswith",
        "heuristic_substring",
        "heuristic_alias",
        "llm_auto_confirmed",
        "parser_auto",
    }
    if src in SYSTEM_AUTO_SOURCES:
        task.deadline_id = None
        task.deadline_match_source = None

    db.commit()
    return LlmRejectResponse(task_id=task.task_id, rejected_at=task.llm_binding_rejected_at)


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_task(
    task_id: str,
    db: Session = Depends(get_db)
) -> TaskDetail:
    """Fetch a single task by ID."""
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskDetail(
        task_id=task.task_id,
        title=task.title,
        category=task.category,
        planned_start=to_local(task.planned_start_utc),
        planned_end=to_local(task.planned_end_utc),
        planned_duration_minutes=task.planned_duration_minutes,
        executed_start=to_local(task.executed_start_utc) if task.executed_start_utc else None,
        executed_end=to_local(task.executed_end_utc) if task.executed_end_utc else None,
        executed_duration_minutes=task.executed_duration_minutes,
        state=task.state,
        source=task.source,
        confidence_score=task.confidence_score,
        notes=task.notes,
        created_at=task.created_at,
        last_modified_at=task.last_modified_at,
        duration_delta_minutes=task.duration_delta_minutes,
        is_mutable=task.is_mutable
    )

