"""Brain-dump multi-item parser endpoints (2026-04-28).

Two routes power the new onboarding surface:
    POST /v1/brain-dump/parse   — heuristic preview, no DB writes
    POST /v1/brain-dump/commit  — single-transaction write of confirmed
                                   items (deadlines first, then tasks,
                                   then bindings) + onboarding stamp.

Operator-locked design:
  - Deterministic over magic. Heuristic is the synchronous critical
    path; no model provider runs during or after this flow.
  - "Catches the user from the get-go." The brain-dump still gates
    onboarding completion; the rewritten UI does multi-parse + auto-
    bind + one-tap binding confirmation block instead of the meta
    "Plan your week" task it produced before.

Authorization: standard user-scoping. Both endpoints require an
authenticated user; the user_scoping middleware sets current_user_id,
TaskManager + DeadlineManager refuse to write without it.
"""
from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Deadline, User
from app.db.scoping import get_current_user_id
from app.schemas.brain_dump import (
    BrainDumpCommitOutcome,
    BrainDumpCommitRequest,
    BrainDumpCommitResponse,
    BrainDumpFailedItem,
    BrainDumpParseRequest,
    BrainDumpParseResponse,
)
from app.services.brain_dump_parser import parse_brain_dump
from app.services.deadline_manager import DeadlineManager
from app.services.task_manager import TaskManager
from app.utils.redis_client import RedisClient
from app.utils.time_utils import now_utc, to_utc

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/brain-dump/parse", response_model=BrainDumpParseResponse)
def brain_dump_parse(
    request: BrainDumpParseRequest,
    db: Session = Depends(get_db),
) -> BrainDumpParseResponse:
    """Heuristic preview. Pure function — no DB writes.

    Returns a list of parsed items + suggested task→deadline bindings
    keyed by `item_id` (uuid generated server-side, opaque to the
    client). The client renders the preview and round-trips the exact
    item_ids to /commit when the user confirms.
    """
    # Authentication still required even though we don't write — keeps
    # the surface behind the same gate as /v1/users/me.
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")

    existing_deadlines = db.query(Deadline).filter(
        Deadline.user_id == uid,
        Deadline.voided_at.is_(None),
        Deadline.state.in_(("planned", "active")),
    ).order_by(Deadline.due_at_utc.asc()).limit(100).all()

    return parse_brain_dump(
        raw_text=request.raw_text,
        now_local_iso=request.current_local_iso,
        existing_deadlines=existing_deadlines,
    )


@router.post("/brain-dump/commit", response_model=BrainDumpCommitResponse)
def brain_dump_commit(
    request: BrainDumpCommitRequest,
    x_idempotency_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> BrainDumpCommitResponse:
    """Persist user-confirmed items + bindings in a single transaction.

    Order:
      1. Deadlines first — task bindings reference deadline_id, so
         deadlines must exist before the bind step writes.
      2. Tasks next — title + when_local + duration. Defaults applied
         when fields are missing (30 min duration, NOW + 30min start).
      3. Bindings last — TaskManager.update_task with deadline_id
         (validates the bind, auto-transitions deadline planned→active).
      4. onboarding_completed_at stamp (idempotent, mirrors the
         TaskManager path so first-task-via-brain-dump still completes
         the onboarding).

    Empty items list is allowed — caller may have parsed nothing usable
    and just wants the onboarding to be marked done. We still stamp the
    onboarding completion timestamp so the UI doesn't loop.
    """
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")

    idempotency_cache: Optional[RedisClient] = None
    idempotency_key = (
        f"brain_dump:commit:{x_idempotency_key.strip()}"
        if x_idempotency_key and x_idempotency_key.strip()
        else None
    )
    if idempotency_key is not None:
        try:
            idempotency_cache = RedisClient()
            cached = idempotency_cache.check_idempotency(
                idempotency_key,
                user_id=uid,
            )
            if cached:
                return BrainDumpCommitResponse(**json.loads(cached))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "brain_dump commit: idempotency lookup unavailable: %s",
                exc,
            )

    task_manager = TaskManager(db)
    deadline_manager = DeadlineManager(db)

    # Map heuristic item_id → real DB id once each row lands. Bindings
    # reference these item_ids (assigned by the parser) and we resolve
    # them to deadline_id / task_id below.
    deadline_id_map: dict[str, str] = {}
    task_id_map: dict[str, str] = {}
    deadline_ids: list[str] = []
    task_ids: list[str] = []
    # LYR-114 fix 2026-04-30: collect per-item failures for the
    # response so the frontend can render a retry-or-edit panel.
    # Pre-fix the endpoint logged + dropped silently.
    failed_items: list[BrainDumpFailedItem] = []
    outcomes: list[BrainDumpCommitOutcome] = []

    def _record_failure(
        item,
        *,
        reason: str,
        detail: str,
        retry_hint: Optional[str],
    ) -> None:
        failed_items.append(BrainDumpFailedItem(
            item_id=item.item_id,
            kind=item.kind,
            title=item.title,
            reason=reason,
            detail=detail,
            retry_hint=retry_hint,
        ))
        outcomes.append(BrainDumpCommitOutcome(
            item_id=item.item_id,
            kind=item.kind,
            title=item.title,
            status="failed" if reason == "internal" else "rejected",
            reason=reason,
            detail=detail,
            retry_hint=retry_hint,
        ))

    def _classify_failure(exc: Exception) -> tuple[str, str, Optional[str]]:
        """Map a TaskManager / DeadlineManager ValueError into a
        machine-readable (reason, detail, retry_hint) triple. Anything
        not recognized falls through to ('internal', repr(exc), None)."""
        msg = str(exc)
        if "start_in_past" in msg:
            return (
                "past_time",
                msg,
                "schedule_tomorrow_same_time",
            )
        if "deadline_terminal_state" in msg:
            return ("deadline_terminal_state", msg, "remove_deadline_binding")
        if "deadline_not_found" in msg or "deadline_user_mismatch" in msg:
            return ("deadline_not_found", msg, "remove_deadline_binding")
        if "deadline_duplicate_title_same_day" in msg:
            return ("duplicate_deadline", msg, "use_existing_deadline")
        if isinstance(exc, ValueError):
            return ("validation", msg, "edit_when_local")
        return ("internal", repr(exc)[:200], None)

    # ── 1. Deadlines ─────────────────────────────────────────────────
    for item in request.items:
        if item.kind != "deadline":
            continue
        if item.when_local is None:
            logger.warning(
                f"brain_dump commit: skipping deadline '{item.title}' — "
                f"no when_local"
            )
            _record_failure(
                item,
                reason="missing_when",
                detail="Deadline needs an explicit due date - none was parsed.",
                retry_hint="edit_when_local",
            )
            continue
        try:
            due_at_utc = to_utc(item.when_local)
            duplicate = deadline_manager.find_duplicate_deadline(
                title=item.title,
                due_at_utc=due_at_utc,
            )
            if duplicate is not None:
                # Reuse the existing deadline for confirmed bindings instead
                # of inflating the pressure map with a second same-day anchor.
                deadline_id_map[item.item_id] = duplicate.deadline_id
                outcomes.append(BrainDumpCommitOutcome(
                    item_id=item.item_id,
                    kind=item.kind,
                    title=item.title,
                    status="reused",
                    canonical_id=duplicate.deadline_id,
                    reason="duplicate_deadline",
                    detail=(
                        "A deadline with this title already exists on the "
                        "same due date; tasks will bind to the existing row."
                    ),
                    retry_hint="use_existing_deadline",
                ))
                continue
            deadline = deadline_manager.create_deadline(
                title=item.title,
                description=item.description,
                due_at_utc=due_at_utc,
            )
            deadline_id_map[item.item_id] = deadline.deadline_id
            deadline_ids.append(deadline.deadline_id)
            outcomes.append(BrainDumpCommitOutcome(
                item_id=item.item_id,
                kind=item.kind,
                title=item.title,
                status="created",
                canonical_id=deadline.deadline_id,
            ))
        except Exception as e:  # noqa: BLE001 — record + continue
            logger.error(
                f"brain_dump commit: deadline create failed for "
                f"'{item.title}': {e}",
                exc_info=True,
            )
            reason, detail, retry_hint = _classify_failure(e)
            _record_failure(
                item,
                reason=reason,
                detail=detail,
                retry_hint=retry_hint,
            )

    # ── 2. Tasks ─────────────────────────────────────────────────────
    # Build a binding lookup so we can pass deadline_id straight to
    # create_task for tasks that already have a confirmed binding —
    # avoids a second update_task round-trip.
    binding_for_task: dict[str, str] = {}
    for b in request.bindings:
        resolved: Optional[str] = None
        if b.target_kind == "existing_deadline" or b.deadline_id:
            resolved = b.deadline_id
        elif b.deadline_item_id:
            resolved = deadline_id_map.get(b.deadline_item_id)
        if resolved is not None:
            # One canonical deadline binding per task. The preview UI enforces
            # this too, but keep the backend deterministic if an old or custom
            # client submits multiple "yes" bindings for the same task.
            binding_for_task.setdefault(b.task_item_id, resolved)

    bindings_applied = 0
    for item in request.items:
        if item.kind != "task":
            continue

        # Defaults — UI should always send these but be resilient.
        when_local = item.when_local
        duration_minutes = item.duration_minutes or 30
        if when_local is None:
            when_local = now_utc() + timedelta(minutes=30)

        end_local = when_local + timedelta(minutes=duration_minutes)
        deadline_id = binding_for_task.get(item.item_id)

        try:
            task, _conflicts, _legacy_external_sync = task_manager.create_task(
                title=item.title,
                start=when_local,
                end=end_local,
                # Brain-dump parse already applies the same deterministic
                # category boundary used by TaskManager. If absent, the
                # manager still falls back to category_mapping inference.
                category=item.category,
                description=item.description,
                deadline_id=deadline_id,
                # force_conflicts=True so a tight brain-dump (multiple
                # items in the same window) doesn't bail out — the
                # operator's intent at this stage is "land everything,
                # I'll triage in /today".
                force_conflicts=True,
            )
            if task is not None:
                task_id_map[item.item_id] = task.task_id
                task_ids.append(task.task_id)
                outcomes.append(BrainDumpCommitOutcome(
                    item_id=item.item_id,
                    kind=item.kind,
                    title=item.title,
                    status="created",
                    canonical_id=task.task_id,
                ))
                if deadline_id is not None:
                    bindings_applied += 1
            else:
                # task is None when create_task returns (None, conflict_result, _)
                # for a soft-conflict rejection — shouldn't happen with
                # force_conflicts=True, but defense in depth.
                _record_failure(
                    item,
                    reason="conflict_blocked",
                    detail="Task creation rejected for conflicts.",
                    retry_hint="edit_when_local",
                )
        except Exception as e:  # noqa: BLE001
            logger.error(
                f"brain_dump commit: task create failed for "
                f"'{item.title}': {e}",
                exc_info=True,
            )
            reason, detail, retry_hint = _classify_failure(e)
            _record_failure(
                item,
                reason=reason,
                detail=detail,
                retry_hint=retry_hint,
            )

    # ── 3. Onboarding stamp ──────────────────────────────────────────
    # TaskManager.create_task already stamps onboarding_completed_at on
    # the FIRST task create — but if the user submitted only deadlines
    # (or nothing usable), that path didn't fire. Defensive idempotent
    # stamp here covers the deadline-only and empty-commit cases.
    user = db.query(User).filter(User.user_id == uid).first()
    if user is not None and user.onboarding_completed_at is None:
        user.onboarding_completed_at = now_utc()
        db.commit()

    response = BrainDumpCommitResponse(
        tasks_created=len(task_ids),
        deadlines_created=len(deadline_ids),
        bindings_applied=bindings_applied,
        task_ids=task_ids,
        deadline_ids=deadline_ids,
        outcomes=outcomes,
        failed_items=failed_items,
    )
    if idempotency_cache is not None and idempotency_key is not None:
        try:
            idempotency_cache.set_idempotency(
                idempotency_key,
                response.model_dump_json(),
                ttl_seconds=60,
                user_id=uid,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "brain_dump commit: idempotency store unavailable: %s",
                exc,
            )

    return response
