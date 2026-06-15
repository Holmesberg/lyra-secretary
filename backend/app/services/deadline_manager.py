"""Deadline Manager — single mutation authority for deadlines.

Mirrors the TaskManager pattern (`backend/app/services/task_manager.py`):
all deadline writes flow through this service. Endpoints never modify
deadline rows directly.

Responsibilities:
- Validate user ownership (read current_user_id from ContextVar)
- Enforce voided_at discipline (every read filters voided_at IS NULL by default)
- Enforce state-transition graph (planned → active/completed/skipped;
  active → completed/skipped; missed → completed/planned; recovery
  from completed/skipped → planned)

State transition graph (user-actionable subset):
    planned ─→ active     (auto on first task bind, OR explicit user action)
    planned ─→ completed  (manual no-bind/offline completion)
    planned ─→ skipped    (user abandons before starting)
    active  ─→ completed  (user marks done)
    active  ─→ skipped    (user abandons mid-flight)
    missed  ─→ completed  (late/offline completion after sweeper marked missed)
    terminal recovery ─→ planned (self-service correction path)
    any     ─→ voided     (soft-delete; via void_deadline, not via update)

Reconciliation-driven (NOT user-actionable here):
    active → missed       (Phase H sweeper, deadline.due_at_utc passed)
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import Deadline, DeadlineCompletionEvent
from app.db.scoping import get_current_user_id
from app.utils.tasks_range_cache import invalidate_user_ranges
from app.utils.time_utils import now_utc, strip_tz


# State transitions a user is allowed to drive directly via update_deadline.
# `missed` itself is reconciliation-driven, but missed -> completed is a
# user-driven late/offline completion affordance. `voided` flows through
# void_deadline (which sets voided_at, not state).
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
    # Reopen paths from terminal states. `missed -> completed` preserves the
    # one-click offline/late completion path after the sweeper runs. Lyra still
    # does NOT distinguish "freshly created" from "reopened" in the schema —
    # analytics that care about completion fidelity should look at completed_at /
    # task_deadline_outcome, not at the current state alone.
    "completed": {"planned"},
    "missed": {"completed", "planned"},
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


def _normalize_deadline_title(title: str) -> str:
    """Canonical title key for same-day duplicate detection."""
    return " ".join(title.casefold().split())


def _invalidate_deadline_user_ranges(user_id: int) -> None:
    try:
        invalidate_user_ranges(int(user_id))
    except Exception:
        pass


class DeadlineDuplicateError(ValueError):
    """Raised when a same-title, same-day, non-voided deadline exists."""

    def __init__(self, existing: Deadline):
        self.existing = existing
        super().__init__(
            "deadline_duplicate_title_same_day: "
            f"existing_deadline_id={existing.deadline_id}"
        )


def record_deadline_completion_event(
    db: Session,
    deadline: Deadline,
    *,
    completion_source: str,
    completed_at_utc: datetime,
    time_provenance: str,
    recorded_at_utc: Optional[datetime] = None,
    task_id: Optional[str] = None,
) -> DeadlineCompletionEvent:
    """Append one deadline completion/submission trace without committing.

    This is intentionally not canonicalizing. One deadline can have multiple
    valid completion events from different sources; analytics must choose
    whether it is counting behaviors or distinct completed deadlines.
    """
    completed_at = strip_tz(completed_at_utc)
    recorded_at = strip_tz(recorded_at_utc) or now_utc()
    due_at = strip_tz(deadline.due_at_utc)
    if completed_at is None or due_at is None:
        raise ValueError("deadline_completion_event requires completed_at and due_at")

    delay_minutes = int((completed_at - due_at).total_seconds() / 60)
    event = DeadlineCompletionEvent(
        deadline_id=deadline.deadline_id,
        user_id=deadline.user_id,
        task_id=task_id,
        completion_source=completion_source,
        completed_at_utc=completed_at,
        recorded_at_utc=recorded_at,
        due_at_utc_at_event=due_at,
        completed_after_due=completed_at > due_at,
        delay_minutes=delay_minutes,
        time_provenance=time_provenance,
    )
    db.add(event)
    return event


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
        force_duplicate: bool = False,
    ) -> Deadline:
        """Create a new deadline in 'planned' state.

        Auto-transitions to 'active' on first task bind (handled in
        TaskManager.create_task — NOT here).
        """
        uid = _require_current_user("create_deadline")
        due_at = strip_tz(due_at_utc) or due_at_utc
        if not force_duplicate:
            duplicate = self.find_duplicate_deadline(title, due_at)
            if duplicate is not None:
                raise DeadlineDuplicateError(duplicate)
        deadline = Deadline(
            deadline_id=str(uuid4()),
            user_id=uid,
            title=title,
            description=description,
            due_at_utc=due_at,
            category_hint=category_hint,
            state="planned",
            created_at=datetime.utcnow(),
        )
        self.db.add(deadline)
        self.db.commit()
        self.db.refresh(deadline)
        _invalidate_deadline_user_ranges(uid)
        return deadline

    def find_duplicate_deadline(
        self,
        title: str,
        due_at_utc: datetime,
        exclude_deadline_id: Optional[str] = None,
    ) -> Optional[Deadline]:
        """Find a same-title, same-UTC-day deadline for the current user.

        This is the deadline sibling of task duplicate-title detection. Any
        non-voided state counts because the row still represents the same
        real-world obligation and should not be duplicated into pressure.
        """
        uid = _require_current_user("find_duplicate_deadline")
        due_at = strip_tz(due_at_utc) or due_at_utc
        day_start = datetime(due_at.year, due_at.month, due_at.day)
        day_end = day_start + timedelta(days=1)
        target = _normalize_deadline_title(title)

        q = self.db.query(Deadline).filter(
            Deadline.user_id == uid,
            Deadline.voided_at.is_(None),
            Deadline.due_at_utc >= day_start,
            Deadline.due_at_utc < day_end,
        )
        if exclude_deadline_id:
            q = q.filter(Deadline.deadline_id != exclude_deadline_id)

        candidates = q.order_by(Deadline.due_at_utc.asc()).all()
        return next(
            (
                deadline
                for deadline in candidates
                if _normalize_deadline_title(deadline.title) == target
            ),
            None,
        )

    def upsert_external_deadline(
        self,
        external_source: str,
        external_id: str,
        title: str,
        due_at_utc: datetime,
        description: Optional[str] = None,
        category_hint: Optional[str] = None,
    ) -> str:
        """Create-or-update a deadline imported from a third-party source.

        Used by the LMS sync job (alembic 041, 2026-04-29) to ingest
        Moodle iCal events as Lyra deadlines. Keyed on
        (user_id, external_source, external_id) — the partial unique
        index `uq_deadline_external` is the DB-level guarantee.

        Returns one of: 'created', 'updated', 'unchanged', 'skipped_voided',
        'duplicate_existing'.

        Voided rows are NOT resurrected — if a user explicitly voided an
        imported deadline, a subsequent sync sees it and skips. The user
        can manually disconnect + reconnect Moodle to reset.
        """
        uid = _require_current_user("upsert_external_deadline")

        # Deliberately INCLUDE voided rows in this lookup so we don't
        # double-create what the user already explicitly voided. The
        # state/voided_at check below decides what to do.
        existing = (
            self.db.query(Deadline)
            .filter(
                Deadline.user_id == uid,
                Deadline.external_source == external_source,
                Deadline.external_id == external_id,
            )
            .first()
        )

        if existing is None:
            duplicate = self.find_duplicate_deadline(title, due_at_utc)
            if duplicate is not None:
                return "duplicate_existing"
            now = datetime.utcnow()
            deadline = Deadline(
                deadline_id=str(uuid4()),
                user_id=uid,
                title=title,
                description=description,
                due_at_utc=due_at_utc,
                category_hint=category_hint,
                state="planned",
                created_at=now,
                external_source=external_source,
                external_id=external_id,
                imported_at=now,
            )
            self.db.add(deadline)
            self.db.commit()
            _invalidate_deadline_user_ranges(uid)
            return "created"

        if existing.voided_at is not None:
            # User explicitly voided this imported row. Don't resurrect.
            return "skipped_voided"

        # Compare canonical fields. due_at_utc is the most likely to
        # change (Moodle deadline extension); title less so but possible.
        # description + category_hint we update silently if they drift.
        changed = (
            existing.title != title
            or existing.due_at_utc != due_at_utc
            or (existing.description or "") != (description or "")
            or (existing.category_hint or "") != (category_hint or "")
        )
        if not changed:
            return "unchanged"

        existing.title = title
        existing.due_at_utc = due_at_utc
        existing.description = description
        existing.category_hint = category_hint
        # imported_at is the FIRST-import timestamp; don't overwrite.
        self.db.commit()
        _invalidate_deadline_user_ranges(uid)
        return "updated"

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

        previous_state = deadline.state
        completion_event_needed = False
        completion_ts: Optional[datetime] = None

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
            if state == "completed" and previous_state != "completed":
                completion_ts = now_utc()
                deadline.completed_at = completion_ts
                completion_event_needed = True

        if title is not None:
            deadline.title = title
        if description is not None:
            deadline.description = description
        if due_at_utc is not None:
            deadline.due_at_utc = due_at_utc
        if category_hint is not None:
            deadline.category_hint = category_hint

        if completion_event_needed and completion_ts is not None:
            record_deadline_completion_event(
                self.db,
                deadline,
                completion_source="user_deadline_done",
                completed_at_utc=completion_ts,
                recorded_at_utc=completion_ts,
                time_provenance="observed_user_action",
            )

        self.db.commit()
        self.db.refresh(deadline)
        _invalidate_deadline_user_ranges(deadline.user_id)
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
        now = now_utc()
        deadline.voided_at = now
        for event in deadline.completion_events:
            if event.voided_at is None:
                event.voided_at = now
        self.db.commit()
        self.db.refresh(deadline)
        _invalidate_deadline_user_ranges(deadline.user_id)
        return deadline
