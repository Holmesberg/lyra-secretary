"""Deadline Manager — single mutation authority for deadlines.

Mirrors the TaskManager pattern (`backend/app/services/task_manager.py`):
all deadline writes flow through this service. Endpoints never modify
deadline rows directly.

Responsibilities:
- Validate user ownership (read current_user_id from ContextVar)
- Enforce voided_at discipline (every read filters voided_at IS NULL by default)
- Enforce state-transition graph (planned → active/skipped/voided;
  active → completed/missed/skipped/voided; terminal states reject
  user-driven transitions)

State transition graph (user-actionable subset):
    planned ─→ active     (auto on first task bind, OR explicit user action)
    planned ─→ skipped    (user abandons before starting)
    active  ─→ completed  (user marks done)
    active  ─→ skipped    (user abandons mid-flight)
    any     ─→ voided     (soft-delete; via void_deadline, not via update)

Reconciliation-driven (NOT user-actionable here):
    active → missed       (Phase H sweeper, deadline.due_at_utc passed)
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import Deadline
from app.db.scoping import get_current_user_id


# State transitions a user is allowed to drive directly via update_deadline.
# `missed` is reconciliation-only; `voided` flows through void_deadline
# (which sets voided_at, not state).
#
# Apr 27 dogfood: operator accidentally tapped "Mark skipped" in the
# DeadlineModal and the change auto-persisted with no recovery path.
# The DeadlineModal now stages state changes until Save, AND the
# state graph permits returning skipped/completed/missed → planned so
# self-service correction works without DB intervention. Going to
# `planned` (NOT `active`) is deliberate — `active` carries the
# "user has bound a task to this deadline" semantic; reopening should
# reset the user back to the editable starting state. Re-binding a
# task auto-transitions planned → active per the existing path.
USER_TRANSITIONS_FROM: dict[str, set[str]] = {
    # `planned → completed` allowed for the no-bind path (operator
    # finished a deadline manually without ever binding a Lyra task).
    # Apr 27 dogfood: operator caught this on first try after the
    # auto-save fix. Without it, the user has to click "Reopen → Save"
    # → reopen modal → "Active" wait, you can't even set active
    # explicitly without binding... so the only path was
    # planned → active(auto via bind) → completed. UX dead-end.
    "planned": {"active", "completed", "skipped"},
    "active": {"completed", "skipped"},
    # Reopen paths from terminal states. Lyra still does NOT distinguish
    # "freshly created" from "reopened" in the schema — analytics that
    # care about completion fidelity should look at completed_at /
    # task_deadline_outcome, not at the current state alone.
    "completed": {"planned"},
    "missed": {"planned"},
    "skipped": {"planned"},
    "voided": set(),
}


def _require_current_user(op: str) -> int:
    """Resolve current_user_id from ContextVar; fail closed if absent.

    Mirrors `_require_current_user` in task_manager.py — the LYR-093
    cross-tenant write leak hardening pattern.
    """
    uid = get_current_user_id()
    if uid is None:
        raise RuntimeError(
            f"{op}: no current_user_id in ContextVar — refusing to write."
        )
    return uid


class DeadlineManager:
    """Single authority for all deadline mutations."""

    def __init__(self, db: Session):
        self.db = db

    # ── Reads ─────────────────────────────────────────────────────────

    def get_deadline(
        self, deadline_id: str, include_voided: bool = False
    ) -> Optional[Deadline]:
        """Get a deadline by id, scoped to current user.

        Returns None if not found OR if the deadline belongs to a
        different user (deliberate — don't leak cross-user existence
        signal).
        """
        uid = _require_current_user("get_deadline")
        q = self.db.query(Deadline).filter(
            Deadline.deadline_id == deadline_id,
            Deadline.user_id == uid,
        )
        if not include_voided:
            q = q.filter(Deadline.voided_at.is_(None))
        return q.first()

    def list_deadlines(
        self, state: Optional[str] = None, include_voided: bool = False
    ) -> list[Deadline]:
        """List the current user's deadlines.

        Default: voided rows excluded (per voided_at_guard memory).
        Optional `state` filter: passes through verbatim (validation
        happens at the schema layer if needed).
        """
        uid = _require_current_user("list_deadlines")
        q = self.db.query(Deadline).filter(Deadline.user_id == uid)
        if not include_voided:
            q = q.filter(Deadline.voided_at.is_(None))
        if state is not None:
            q = q.filter(Deadline.state == state)
        return q.order_by(Deadline.due_at_utc.asc()).all()

    # ── Writes ────────────────────────────────────────────────────────

    def create_deadline(
        self,
        title: str,
        due_at_utc: datetime,
        description: Optional[str] = None,
        category_hint: Optional[str] = None,
    ) -> Deadline:
        """Create a new deadline in 'planned' state.

        Auto-transitions to 'active' on first task bind (handled in
        TaskManager.create_task — NOT here).
        """
        uid = _require_current_user("create_deadline")
        deadline = Deadline(
            deadline_id=str(uuid4()),
            user_id=uid,
            title=title,
            description=description,
            due_at_utc=due_at_utc,
            category_hint=category_hint,
            state="planned",
            created_at=datetime.utcnow(),
        )
        self.db.add(deadline)
        self.db.commit()
        self.db.refresh(deadline)
        return deadline

    def update_deadline(
        self,
        deadline_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        due_at_utc: Optional[datetime] = None,
        category_hint: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Deadline:
        """Update editable fields and/or trigger a state transition.

        Raises ValueError on:
          - deadline_not_found (not found OR cross-user attempt)
          - deadline_voided (cannot edit a voided deadline)
          - deadline_invalid_transition (state change not in
            USER_TRANSITIONS_FROM map)
          - deadline_unknown_state (state value not in enum)
        """
        deadline = self.get_deadline(deadline_id)
        if deadline is None:
            raise ValueError(f"deadline_not_found: {deadline_id}")
        # get_deadline already excludes voided rows by default. If the
        # caller somehow has a voided row in hand, defensive check:
        if deadline.voided_at is not None:
            raise ValueError(f"deadline_voided: {deadline_id}")

        if state is not None:
            allowed = USER_TRANSITIONS_FROM.get(deadline.state)
            if allowed is None:
                raise ValueError(
                    f"deadline_unknown_state: current state '{deadline.state}'"
                )
            if state == deadline.state:
                # No-op transition; allow silently for idempotency.
                pass
            elif state not in allowed:
                raise ValueError(
                    f"deadline_invalid_transition: {deadline.state} → {state}"
                )
            deadline.state = state
            # Stamp completed_at when transitioning to 'completed'.
            if state == "completed" and deadline.completed_at is None:
                deadline.completed_at = datetime.utcnow()

        if title is not None:
            deadline.title = title
        if description is not None:
            deadline.description = description
        if due_at_utc is not None:
            deadline.due_at_utc = due_at_utc
        if category_hint is not None:
            deadline.category_hint = category_hint

        self.db.commit()
        self.db.refresh(deadline)
        return deadline

    def void_deadline(self, deadline_id: str) -> Deadline:
        """Soft-delete a deadline by setting voided_at.

        Bound tasks keep their deadline_id (FK is nullable; no cascade).
        Future analytics queries MUST filter
        `deadline.voided_at IS NULL` per the voided_at_guard memory.

        Voiding is allowed from any state (including terminal states).
        """
        deadline = self.get_deadline(deadline_id, include_voided=True)
        if deadline is None:
            raise ValueError(f"deadline_not_found: {deadline_id}")
        if deadline.voided_at is not None:
            # Idempotent: already voided.
            return deadline
        deadline.voided_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(deadline)
        return deadline
