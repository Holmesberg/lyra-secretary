"""Time conflict detection — classified severity model (Path A, Apr 16 2026).

Severity rules (per dogfood `Conflict detection too strict for planned tasks`,
April 15 2026; revised Apr 17 — EXECUTING overlap downgraded to SOFT per
rules_vs_agency.md §planning during execution is permitted):

  SOFT — `executing_overlap`: overlap with state=EXECUTING. Planning during
         execution is a legitimate workflow (schedule the next task while the
         current one is running). User can force-override.

  SOFT — `planned_overlap`: overlap with state=PLANNED or PAUSED. Legitimate
         use cases: context-switching, contingent tasks, multi-task scenarios
         (see `parked_ideas.md §Multi-task logging`). User can force-override.

  SOFT — `duplicate_title`: same title (case-insensitive) on the same UTC date.
         User can force-override. Note: same-UTC-date is a v1 simplification —
         Cairo (UTC+2) shifts the boundary by 2h, so an edge-case task at
         Cairo 01:30 vs another at Cairo 03:00 would be on different UTC days.
         Multi-tz refactor lives on its own backlog item.

  No HARD conflicts exist in the current model — all overlaps are
  force-overridable. The `hard` bucket is kept in ConflictResult for
  future use (e.g., if immutable-slot constraints are added).
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Task, TaskState


@dataclass
class ConflictResult:
    """Classified conflict-detection output. See module docstring for severity rules."""

    hard: list[Task] = field(default_factory=list)
    soft_overlap: list[Task] = field(default_factory=list)
    soft_duplicate: list[Task] = field(default_factory=list)

    def all_conflicts(self) -> list[Task]:
        """Flat list, deduped by task_id (a single task can hit multiple gates)."""
        seen: set[str] = set()
        out: list[Task] = []
        for t in self.hard + self.soft_overlap + self.soft_duplicate:
            if t.task_id not in seen:
                seen.add(t.task_id)
                out.append(t)
        return out

    def has_hard(self) -> bool:
        return bool(self.hard)

    def has_soft(self) -> bool:
        return bool(self.soft_overlap) or bool(self.soft_duplicate)

    def severity(self) -> Optional[str]:
        """`"hard"` (always rejects) | `"soft"` (force-overridable) | `None` (no conflict)."""
        if self.has_hard():
            return "hard"
        if self.has_soft():
            return "soft"
        return None

    def soft_reasons(self) -> list[str]:
        """Stable-ordered list naming the soft-warning gates that fired."""
        out: list[str] = []
        if self.soft_overlap:
            out.append("overlap")
        if self.soft_duplicate:
            out.append("duplicate_title")
        return out


class ConflictDetector:
    """Detect overlapping + duplicate-title tasks with severity classification."""

    def __init__(self, db: Session):
        self.db = db

    def detect(
        self,
        start: datetime,
        end: datetime,
        exclude_task_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> ConflictResult:
        """Classified detection.

        Overlap rule: half-open interval [start, end) — task A and task B
        overlap iff `A.start < B.end AND B.start < A.end`.

        Args:
            start: New/rescheduled task's planned_start_utc.
            end: New/rescheduled task's planned_end_utc.
            exclude_task_id: Skip this task_id (used by reschedule so the task
                being moved doesn't conflict with itself).
            title: If provided, also runs the duplicate-title same-day gate.
                Skipped when None (back-compat for callers that don't have title).

        Returns:
            ConflictResult with three buckets.
        """
        # Time-overlap query — applies to all three pause-machine states that
        # reserve calendar time. EXECUTED / SKIPPED / DELETED are excluded
        # (their slot is no longer reserved).
        overlap_q = self.db.query(Task).filter(
            Task.state.in_([TaskState.PLANNED, TaskState.EXECUTING, TaskState.PAUSED]),
            Task.voided_at.is_(None),
            Task.planned_start_utc < end,
            Task.planned_end_utc > start,
        )
        if exclude_task_id:
            overlap_q = overlap_q.filter(Task.task_id != exclude_task_id)
        overlapping = overlap_q.all()

        hard: list[Task] = []
        soft_overlap = list(overlapping)

        # Duplicate-title same-UTC-day gate.
        soft_duplicate: list[Task] = []
        if title:
            day_start = datetime(start.year, start.month, start.day)
            day_end = day_start + timedelta(days=1)
            dup_q = self.db.query(Task).filter(
                func.lower(Task.title) == title.lower(),
                Task.state != TaskState.DELETED,
                Task.voided_at.is_(None),
                Task.planned_start_utc >= day_start,
                Task.planned_start_utc < day_end,
            )
            if exclude_task_id:
                dup_q = dup_q.filter(Task.task_id != exclude_task_id)
            soft_duplicate = dup_q.all()

        return ConflictResult(
            hard=hard,
            soft_overlap=soft_overlap,
            soft_duplicate=soft_duplicate,
        )
