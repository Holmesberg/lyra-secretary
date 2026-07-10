"""SQLAlchemy models for LyraOS."""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# Enums
class TaskState(str, Enum):
    """Task state machine states."""
    PLANNED = "PLANNED"
    EXECUTING = "EXECUTING"
    PAUSED = "PAUSED"
    EXECUTED = "EXECUTED"
    SKIPPED = "SKIPPED"
    DELETED = "DELETED"


class TaskSource(str, Enum):
    """How the task was created."""
    MANUAL = "manual"
    VOICE = "voice"
    WEB = "web"
    # JARVIS-mediated creation (operator-only, 2026-04-30). Marks tasks
    # whose origin was a JARVIS tool call (create_task) so the audit
    # trail can distinguish them from human typing/voice. Future
    # research-integrity stratifications may want to filter these out
    # the same way external_source='moodle_ics' deadlines are filtered.
    JARVIS = "jarvis"


# Models
class Task(Base):
    """
    Core task entity. One row = one task through entire lifecycle.
    
    This is the heart of the adaptive scheduler.
    Key fields:
        planned_duration_minutes - What user planned
        executed_duration_minutes - What actually happened
        
    The delta between these drives future AI scheduling.
    """
    
    __tablename__ = "task"
    
    # Primary key
    task_id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid4())
    )
    
    # Core fields
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Planned time (always populated)
    planned_start_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    planned_end_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    planned_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Executed time (nullable until execution)
    executed_start_utc: Mapped[Optional[datetime]] = mapped_column(DateTime)
    executed_end_utc: Mapped[Optional[datetime]] = mapped_column(DateTime)
    executed_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    
    # State machine
    state: Mapped[TaskState] = mapped_column(
        String(20),
        nullable=False,
        default=TaskState.PLANNED
    )
    
    # Metadata
    source: Mapped[TaskSource] = mapped_column(
        String(20),
        nullable=False,
        default=TaskSource.MANUAL
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    scope_outcome: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False,
        default=datetime.utcnow
    )
    last_modified_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Discrepancy measurement (research instrument — do not remove)
    pre_task_readiness: Mapped[Optional[int]] = mapped_column(Integer)
    post_task_reflection: Mapped[Optional[int]] = mapped_column(Integer)
    initiation_status: Mapped[str] = mapped_column(String(20), default="not_started")
    initiation_delay_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    pause_count: Mapped[int] = mapped_column(Integer, default=0)

    # Void tracking (system_error sessions excluded from analytics)
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Enum string (test_contamination|duplicate|system_error|data_quality|other)
    voided_reason: Mapped[Optional[str]] = mapped_column(String(200))
    # Free text — required only when voided_reason='other'.
    void_reason_detail: Mapped[Optional[str]] = mapped_column(String(500))

    # Interruption tracking
    parent_task_id: Mapped[Optional[str]] = mapped_column(String(36))
    interruption_type: Mapped[Optional[str]] = mapped_column(String(20))

    # Substitution tracking
    replaced_by_task_id: Mapped[Optional[str]] = mapped_column(String(36))
    replaces_task_id: Mapped[Optional[str]] = mapped_column(String(36))

    # Reschedule tracking
    reschedule_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Anonymized retention (alembic 019) — set when user deletes account with
    # retain_for_research=true. Rows with post_deletion_retained_at != NULL are
    # the logical "cohort=deleted_anonymized" in research queries.
    post_deletion_retained_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    original_user_id_hash: Mapped[Optional[str]] = mapped_column(String(64))

    # Cascade chain position — immutable, set at creation time only.
    # Resets per local-tz date. Voided (system_error) rows excluded from chain.
    # See alembic 012, MANIFESTO.md cascade section.
    session_index_in_day: Mapped[Optional[int]] = mapped_column(Integer)

    # Unplanned execution tracking
    unplanned_reason: Mapped[Optional[str]] = mapped_column(String(30))

    # Legacy external-sync columns retained until an approved schema migration.
    notion_page_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)

    # Multi-user ownership (alembic 014)
    # NO default — writes MUST pass user_id explicitly. The prior default=1
    # silently funneled every cross-tenant write to the operator (LYR-093).
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Measurement validity gates (alembic 053, 2026-05-19).
    # is_anchor marks fixed routine blocks such as prayers and sleep. These
    # are valid descriptive schedule rows, but they must not enter clean
    # bias_factor calibration as evidence of planning/execution skill.
    is_anchor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Rule 16 soft-warning cohort assignment. Deterministic by user_id mod 2
    # and stamped at creation so later analyses do not infer exposure arm.
    rct_arm: Mapped[Optional[str]] = mapped_column(String(40))

    # Loop 11 — deadline mechanism foundation (alembic 033, 2026-04-26).
    # Pre-registered MANIFESTO Rules 14, 15, 16 + Rule 12 amendment.
    # See `docs/archive/legacy/planning/feedback_loops_closure_plan.md §Loop 11` and
    # `docs/archive/legacy/provider_academic/deadline_mechanism_design.md`.
    deadline_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("deadline.deadline_id"),
    )
    # 0.0–1.0 from binding source (1.0 for explicit, 0.5–0.99 for parser).
    deadline_match_confidence: Mapped[Optional[float]] = mapped_column(Float)
    # Enum string: 'user_explicit' | 'parser_auto' | 'user_corrected'.
    deadline_match_source: Mapped[Optional[str]] = mapped_column(String(20))
    # Auto-counted at PLANNED-state creation by extract_scope_bullets().
    scope_bullet_count_at_plan: Mapped[Optional[int]] = mapped_column(Integer)
    # Re-sampled at complete_task time (before EXECUTED transition).
    scope_bullet_count_at_execute: Mapped[Optional[int]] = mapped_column(Integer)

    # ── LLM enrichment fields (alembic 036, magic-for-alpha 2026-04-28) ──
    # Populated by the async background `llm_enrichment` worker, NOT by
    # the fast-path POST /v1/create. Critical guardrails:
    #   - Regex output (`scope_bullet_count_at_plan`) and parser-based
    #     `deadline_id` remain canonical. These llm_* fields are a parallel
    #     signal the user can confirm into canonical via a one-tap chip.
    #   - `llm_parse_status` flips: pending → enriched | unavailable | failed.
    #     UI degrades to regex output when status != 'enriched'.
    #   - `llm_inferred_deadline_id` does NOT replace `deadline_id`;
    #     `POST /v1/tasks/{id}/llm-confirm` copies it across on user accept.
    llm_parse_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    llm_priority: Mapped[Optional[int]] = mapped_column(Integer)
    llm_inferred_deadline_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("deadline.deadline_id", ondelete="SET NULL"),
    )
    llm_deadline_match_confidence: Mapped[Optional[float]] = mapped_column(Float)
    # Tier system (operator-locked UX 2026-04-28):
    #   Tier 1 — top confidence > 0.85: silent auto-chip with confirm
    #   Tier 2 — top confidence 0.45-0.85: "Related to one of these?"
    #             rendering top 2-3 candidates from this list
    #   Tier 3 — top confidence < 0.45: no chip
    #   Tier 4 — manual override always via DeadlinePickerSlot
    # Shape: [{"deadline_id": "...", "title": "...", "confidence": 0..1}, ...]
    llm_deadline_candidates: Mapped[Optional[list]] = mapped_column(JSON)
    llm_sub_items: Mapped[Optional[list]] = mapped_column(JSON)
    llm_parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Set by POST /v1/tasks/{id}/reject-llm-binding (Workstream 4) when
    # the user explicitly rejects the LLM-suggested deadline binding.
    llm_binding_rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Trust-not-rewrite contract (alembic 039, 2026-04-28). When a
    # heuristic-bound or user-bound task gets a different deadline
    # suggestion from the async LLM enrichment, we DO NOT silently
    # rewrite task.deadline_id — that breaks user trust ("the chip
    # changed under me"). Instead, the alternative is stored here as a
    # JSONB suggestion the chip can render as "Possible better match
    # — [keep current] [switch]". User decides.
    # Shape: {"deadline_id": "...", "title": "...", "confidence": 0..1,
    #         "from_source": "llm_auto" | "heuristic_substring" | ...}
    llm_alternative_suggestion: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    stopwatch_sessions: Mapped[list["StopwatchSession"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan"
    )
    execution_corrections: Mapped[list["TaskExecutionCorrection"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    deadline: Mapped[Optional["Deadline"]] = relationship(
        back_populates="tasks",
        # Explicit FK selection — alembic 036 added a second FK
        # (llm_inferred_deadline_id) which made the join condition
        # ambiguous. The canonical user-facing binding stays on
        # Task.deadline_id; the LLM suggestion lives in
        # llm_inferred_deadline_id with no ORM relationship traversal.
        foreign_keys="Task.deadline_id",
    )
    deadline_outcome: Mapped[Optional["TaskDeadlineOutcome"]] = relationship(
        back_populates="task",
        uselist=False,
        cascade="all, delete-orphan",
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "state IN ('PLANNED', 'EXECUTING', 'PAUSED', 'EXECUTED', 'SKIPPED', 'DELETED')",
            name="check_state"
        ),
        CheckConstraint(
            "source IN ('manual', 'voice', 'web', 'jarvis')",
            name="check_source"
        ),
        CheckConstraint(
            "planned_duration_minutes > 0",
            name="check_planned_duration"
        ),
        Index("idx_task_state", "state"),
        Index("idx_task_start", "planned_start_utc"),
        Index("idx_task_category", "category"),
        Index("idx_task_created", "created_at"),
        Index("idx_task_user_anchor", "user_id", "is_anchor"),
        Index("idx_task_rct_arm", "rct_arm"),
    )
    
    # Helper properties
    @property
    def is_mutable(self) -> bool:
        """Can this task be modified?"""
        return self.state not in (TaskState.EXECUTED, TaskState.DELETED)
    
    @property
    def duration_delta_minutes(self) -> Optional[int]:
        """
        Planned - Executed duration.

        Positive = finished early
        Negative = took longer than planned

        This is the core data for adaptive scheduling.
        """
        if self.executed_duration_minutes is None:
            return None
        return self.planned_duration_minutes - self.executed_duration_minutes

    @property
    def latest_execution_correction(self) -> Optional["TaskExecutionCorrection"]:
        """Most recent retroactive timer correction, if one exists."""
        if not self.execution_corrections:
            return None
        return max(self.execution_corrections, key=lambda c: c.created_at)

    @property
    def effective_executed_duration_minutes(self) -> Optional[int]:
        """User-facing duration after append-only retroactive correction."""
        correction = self.latest_execution_correction
        if correction is not None:
            return correction.corrected_executed_duration_minutes
        return self.executed_duration_minutes

    @property
    def effective_executed_end_utc(self) -> Optional[datetime]:
        """User-facing end time after append-only retroactive correction."""
        correction = self.latest_execution_correction
        if correction is not None:
            return correction.corrected_executed_end_utc
        return self.executed_end_utc

    @property
    def effective_duration_delta_minutes(self) -> Optional[int]:
        """Planned - effective executed duration."""
        effective = self.effective_executed_duration_minutes
        if effective is None:
            return None
        return self.planned_duration_minutes - effective

    @property
    def execution_duration_provenance(self) -> str:
        """observed for raw stopwatch rows, retroactive after correction."""
        return (
            "retroactive"
            if self.latest_execution_correction or self.initiation_status == "retroactive"
            else "observed"
        )

    @property
    def discrepancy_score(self) -> Optional[int]:
        """Absolute cognitive shift between pre and post task ratings.
        Formula: abs(pre_task_readiness - post_task_reflection)
        NOT abs(planned_duration - actual_duration) — that is duration_delta_minutes.
        """
        if self.pre_task_readiness is None or self.post_task_reflection is None:
            return None
        return abs(self.pre_task_readiness - self.post_task_reflection)  # cognitive shift magnitude

    @property
    def signed_discrepancy(self) -> Optional[int]:
        """Signed cognitive shift: post_task_reflection - pre_task_readiness.
        Positive = task was restorative (ended sharper than started)
        Negative = task was depleting (ended duller than started)
        Zero = neutral cognitive impact
        """
        if self.pre_task_readiness is None or self.post_task_reflection is None:
            return None
        return self.post_task_reflection - self.pre_task_readiness


class Deadline(Base):
    """First-class deadline entity (alembic 033, 2026-04-26).

    Many tasks → one deadline. Created in `state='planned'` (dormant);
    auto-transitions to 'active' on first task bind via TaskManager.

    State enum: planned | active | completed | missed | skipped | voided.
    Per operator decision 2026-04-26 — mirrors task lifecycle semantics.
    `skipped` is intentional abandonment (distinct from `missed` which is
    passive — `due_at_utc` passed unhandled).

    Pre-registration: MANIFESTO Rules 14 (deadline-distance kill criterion),
    15 (per-deadline bias_factor analysis), 16 (soft-warning RCT design).

    Voided_at discipline (per `feedback_voided_at_guard` memory): every
    query of this table MUST filter `voided_at IS NULL`. State-only filters
    leak voided rows.
    """

    __tablename__ = "deadline"

    deadline_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.user_id"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    due_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    category_hint: Mapped[Optional[str]] = mapped_column(String(100))

    # See class docstring for state enum semantics.
    state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="planned",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Set only by the active->missed sweeper. Planned overdue rows stay
    # planned by design, so "overdue" analytics must compare completion time
    # against due_at_utc instead of treating missed_at as universal.
    missed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    # External-source flagging (alembic 041, 2026-04-29). NULL on
    # native deadlines (operator/user-typed). Non-NULL means the row
    # was imported from a third-party source (Moodle iCal, future:
    # Canvas/Blackboard/etc). H2 research queries (Rules 14-16) MUST
    # filter `WHERE external_source IS NULL` to keep native-only.
    # Mirrors `external_event_outcome` template (line 654).
    external_source: Mapped[Optional[str]] = mapped_column(String(32))
    external_id: Mapped[Optional[str]] = mapped_column(String(256))
    imported_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="deadline",
        # Symmetric to Task.deadline — only follow the canonical FK,
        # not the new llm_inferred_deadline_id FK from alembic 036.
        foreign_keys="Task.deadline_id",
    )
    completion_events: Mapped[list["DeadlineCompletionEvent"]] = relationship(
        back_populates="deadline",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "state IN ('planned', 'active', 'completed', 'missed', 'skipped', 'voided')",
            name="check_deadline_state",
        ),
        Index("idx_deadline_user_state", "user_id", "state", "voided_at"),
        # Partial unique index for upsert keying — only enforced for
        # imported rows. Native deadlines have NULL external_*, so they
        # don't participate in uniqueness. See alembic 041 for the
        # postgresql_where/sqlite_where partial-index spec.
        Index(
            "uq_deadline_external",
            "user_id",
            "external_source",
            "external_id",
            unique=True,
            postgresql_where=text("external_source IS NOT NULL"),
            sqlite_where=text("external_source IS NOT NULL"),
        ),
    )

    @property
    def is_bindable(self) -> bool:
        """Can a new task be bound to this deadline?

        Bindable iff state ∈ {planned, active} AND not voided. Terminal
        states (completed/missed/skipped) reject new bindings; voided is
        a soft-delete that supersedes any state.
        """
        if self.voided_at is not None:
            return False
        return self.state in ("planned", "active")


class DeadlineCompletionEvent(Base):
    """Append-only deadline resolution trace (alembic 049).

    One deadline may have multiple valid completion events: a manual "done",
    a later Moodle submission confirmation, and a retroactive task-done action
    are distinct behaviors. Analytics must distinguish event count from
    distinct completed deadlines. These rows are completion/submission traces,
    not stopwatch execution traces, and are never VT-17 eligible.
    """

    __tablename__ = "deadline_completion_event"

    event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    deadline_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("deadline.deadline_id"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    task_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("task.task_id", ondelete="SET NULL"),
    )
    completion_source: Mapped[str] = mapped_column(String(40), nullable=False)
    completed_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    due_at_utc_at_event: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_after_due: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Signed: positive = completed after due_at_utc_at_event.
    delay_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    time_provenance: Mapped[str] = mapped_column(String(40), nullable=False)
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    deadline: Mapped["Deadline"] = relationship(back_populates="completion_events")

    __table_args__ = (
        CheckConstraint(
            "completion_source IN ("
            "'user_deadline_done', "
            "'moodle_submission', "
            "'moodle_backfill_submission', "
            "'task_retroactive_done'"
            ")",
            name="check_deadline_completion_source",
        ),
        CheckConstraint(
            "time_provenance IN ("
            "'observed_user_action', "
            "'external_import', "
            "'external_import_sync_time', "
            "'user_reported_retroactive'"
            ")",
            name="check_deadline_completion_time_provenance",
        ),
        Index("idx_deadline_completion_user_recorded", "user_id", "recorded_at_utc"),
        Index("idx_deadline_completion_deadline_completed", "deadline_id", "completed_at_utc"),
    )


class TaskDeadlineOutcome(Base):
    """Post-execution reconciliation row for deadline-met outcomes (alembic 033).

    Stored in a separate table from `task` to preserve EXECUTED-task
    immutability (state_machine.py:29,61-64). Mirrors the
    `external_event_outcome` template (alembic 027).

    Frozen-at-compute-time semantics: `deadline_utc_at_compute` and
    `executed_end_utc_at_compute` snapshot the values used in the
    `deadline_met` decision. If the rule changes later (e.g., grace
    period for clock skew), historical answers remain reproducible
    against the snapshotted inputs.

    Voided_at: if the underlying task is voided post-EXECUTED (LYR-095
    scenario), this row is invalidated (NOT deleted) by setting voided_at.
    Future reconciliation queries MUST filter `voided_at IS NULL` per
    `feedback_voided_at_guard` discipline.

    Written by the Phase H reconciliation job (deferred from today's
    foundation commit). Read by `GET /v1/analytics/deadline-shape`
    (Phase I, also deferred).
    """

    __tablename__ = "task_deadline_outcome"

    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("task.task_id"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    deadline_utc_at_compute: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    executed_end_utc_at_compute: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    deadline_met: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Signed: positive = overran (missed by N min), negative = under (met
    # by N min). delay_minutes == 0 is treated as met (boundary case).
    delay_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    task: Mapped["Task"] = relationship(back_populates="deadline_outcome")

    __table_args__ = (
        Index("idx_tdo_user_computed", "user_id", "computed_at"),
    )


class StopwatchSession(Base):
    """Tracks stopwatch timing sessions."""
    
    __tablename__ = "stopwatch_session"
    
    session_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("task.task_id", ondelete="CASCADE"),
        nullable=False
    )
    start_time_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time_utc: Mapped[Optional[datetime]] = mapped_column(DateTime)
    auto_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    paused_at_utc: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Float so sub-minute pauses don't truncate to zero (LYR-094).
    total_paused_minutes: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    pause_reason: Mapped[Optional[str]] = mapped_column(String(50))
    pause_initiator: Mapped[Optional[str]] = mapped_column(String(20))
    original_pre_task_readiness: Mapped[Optional[int]] = mapped_column(Integer)
    task_completion_percentage: Mapped[Optional[int]] = mapped_column(Integer)

    # Multi-user ownership (alembic 014)
    # NO default — writes MUST pass user_id explicitly. The prior default=1
    # silently funneled every cross-tenant write to the operator (LYR-093).
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Anonymized retention (alembic 019)
    post_deletion_retained_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    original_user_id_hash: Mapped[Optional[str]] = mapped_column(String(64))

    # Data-quality retrofit flag (alembic 020). NULL = clean.
    # 'possibly_default_pause_metadata' = pre-April-15 rows where pause_reason
    # + pause_initiator may have been silently defaulted by the removed defaults
    # at stopwatch_manager.py:330-331.
    # 'pause_reason_lost_to_overwrite' = sessions whose task has pause_count > 1
    # and the earlier pause's metadata was overwritten before pause_event existed.
    # Analytics MUST exclude non-NULL rows when analyzing pause metadata.
    data_quality_flag: Mapped[Optional[str]] = mapped_column(String(50))

    # Relationship
    task: Mapped["Task"] = relationship(back_populates="stopwatch_sessions")

    # Indexes
    __table_args__ = (
        Index("idx_stopwatch_task", "task_id"),
    )
    
    @property
    def is_active(self) -> bool:
        """Is this session currently running?"""
        return self.end_time_utc is None
    
    @property
    def wall_clock_minutes(self) -> Optional[int]:
        """Wall clock duration in minutes (if stopped). Includes paused time."""
        if self.end_time_utc is None:
            return None
        delta = self.end_time_utc - self.start_time_utc
        return int(delta.total_seconds() / 60)

    @property
    def active_duration_minutes(self) -> Optional[int]:
        """Active work duration in minutes (wall clock minus paused time)."""
        if self.end_time_utc is None:
            return None
        wall = int((self.end_time_utc - self.start_time_utc).total_seconds() / 60)
        return max(0, wall - self.total_paused_minutes)


class TaskExecutionCorrection(Base):
    """Append-only retroactive correction for forgotten timer stops.

    This is Layer D user narrative / repair data. It never overwrites the
    Layer A task or stopwatch timestamps. VT-17 eligibility is explicitly
    false: this row is not a PauseEvent-like object and must not enter
    PausePredictionLog or ResumePredictionLog training data.
    """

    __tablename__ = "task_execution_correction"

    correction_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("task.task_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    provenance: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="retroactive",
    )
    reason: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="forgot_to_stop_timer",
    )
    note: Mapped[Optional[str]] = mapped_column(String(500))

    original_executed_start_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    original_executed_end_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    original_executed_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    corrected_executed_end_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    corrected_executed_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_paused_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Explicit schema marker: timer corrections are never VT-17 training rows.
    vt17_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    task: Mapped["Task"] = relationship(back_populates="execution_corrections")

    __table_args__ = (
        CheckConstraint(
            "provenance = 'retroactive'",
            name="check_task_execution_correction_provenance",
        ),
        CheckConstraint(
            "reason IN ('forgot_to_stop_timer', 'accidental_left_running')",
            name="check_task_execution_correction_reason",
        ),
        CheckConstraint(
            "corrected_executed_duration_minutes > 0",
            name="check_task_execution_correction_duration_positive",
        ),
        CheckConstraint(
            "vt17_eligible = false",
            name="check_task_execution_correction_vt17_ineligible",
        ),
        Index("idx_task_execution_correction_task_created", "task_id", "created_at"),
        Index("idx_task_execution_correction_user_created", "user_id", "created_at"),
    )


class CategoryMapping(Base):
    """
    Static category mappings from keywords.
    
    Seeded once, not learned dynamically in v1.
    """
    
    __tablename__ = "category_mapping"
    
    keyword: Mapped[str] = mapped_column(String(100), primary_key=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.9)
    last_used: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    __table_args__ = (
        Index("idx_category_confidence", "category", "confidence"),
    )


class User(Base):
    """Multi-user pivot — one row per account. Operator is user_id=1."""

    __tablename__ = "user"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    google_display_name: Mapped[Optional[str]] = mapped_column(String(120))
    google_first_name: Mapped[Optional[str]] = mapped_column(String(80))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Africa/Cairo")
    is_operator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notion_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archetype_id: Mapped[Optional[str]] = mapped_column(String(40), ForeignKey("archetype.archetype_id"))
    terms_accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    research_consent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Path B (2026-04-21): stamped on first task creation OR explicit
    # skip. Null = user has not yet completed the onboarding planning
    # ritual. Used by the frontend (app)/layout.tsx to gate the
    # onboarding surface and by the 2026-05-21 kill-criterion query.
    onboarding_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Guided tour stamps (alembic 029, 2026-04-22). Both NULL = user has
    # not seen the tour yet; either non-null = tour won't re-fire. See
    # frontend/components/tutorial-overlay.tsx and
    # docs/parked_ideas.md §Guided product tour.
    tutorial_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    tutorial_skipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Archetype survey retrofit banner dismissal (alembic 032, 2026-04-22).
    # Set when a pre-launch user clicks Dismiss on the Settings
    # "Get predictions that fit you" banner. Null = banner still visible
    # if user has no ArchetypeAssignment. Taking the survey makes the
    # banner disappear independently of this stamp (via the
    # has_assignment check in /users/me).
    archetype_retrofit_dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Google Calendar read-only integration (2026-04-21, migration 026).
    # Long-lived refresh token for offline calendar.readonly access.
    # Stored plaintext in v1 — Fernet encryption deferred to Phase 6+
    # (security debt). NEVER returned in any API response, never logged.
    # Null = user has not completed calendar OAuth consent yet OR
    # revoked access.
    google_refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    # Moodle LMS read-only integration (alembic 041, 2026-04-29).
    # moodle_ics_url is the user's private Moodle calendar subscription
    # URL (contains a per-user authtoken — credential-equivalent). Same
    # trust class as google_refresh_token: plaintext in v1, Fernet
    # encryption deferred to Phase 6+. NEVER returned in any API
    # response, NEVER logged in full. NULL = user has not connected
    # Moodle yet OR explicitly disconnected.
    moodle_ics_url: Mapped[Optional[str]] = mapped_column(Text)
    moodle_last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Set when sync fails permanently (4xx, malformed feed, etc.).
    # Frontend reads this to surface "Reconnect needed" instead of
    # silently failing. Cleared when user reconnects.
    moodle_disconnect_reason: Mapped[Optional[str]] = mapped_column(String(64))
    # Moodle Web Services token (alembic 043, 2026-05-01). Powers
    # automatic submission detection - when set, the
    # moodle_submissions_sync job queries WS for each task-bound
    # imported deadline and records completion candidate evidence when
    # Moodle confirms submission/grading. Encrypted-at-rest via Fernet from alembic 044
    # — see utils/encryption.py. Stored format: `"fernet:" + base64`
    # for new connections; legacy operator row may be raw plaintext
    # (the prefix-sniffing decryptor handles both transparently).
    # NEVER returned in any API response (only "is set: bool" via
    # /v1/integrations).
    moodle_ws_token: Mapped[Optional[str]] = mapped_column(Text)
    moodle_ws_last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Set on permanent WS failure (e.g., 'invalidtoken' — operator
    # rotated the token in Moodle). Frontend surfaces "Reconnect Web
    # Services" prompt; cleared on successful reconnect.
    moodle_ws_disconnect_reason: Mapped[Optional[str]] = mapped_column(String(64))
    # Per-user Moodle userid + base URL (alembic 044, 2026-05-01).
    # Captured at WS connect from core_webservice_get_site_info; the
    # WS token is bound to its user and Moodle rejects cross-user
    # queries with accessexception. Pre-044 operator row may have NULL
    # values; sync_user falls back to env (MOODLE_WS_USERID,
    # MOODLE_WS_BASE_URL) for that case.
    moodle_userid: Mapped[Optional[int]] = mapped_column(Integer)
    moodle_base_url: Mapped[Optional[str]] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    # Alpha funnel instrumentation (alembic 037, 2026-04-28). Tracks the
    # operator's North Star metric: task_created + timer_started within
    # the user's first 3 minutes. All three columns are lazily stamped
    # — written once on first occurrence, never updated. NULL = event
    # not yet occurred.
    #   first_task_at — set in TaskManager.create_task on first call per user
    #   first_timer_started_at — set in StopwatchManager.start on first call per user
    #   d1_return_at — set in /users/me when called ≥24h after created_at and
    #     this column is still NULL; approximates "returned next day"
    # Per VT-15/VT-16 (research-integrity audit 2026-04-28): these are
    # Population 2 (product research) signals only, not Population 1 (H1
    # hypothesis research). Cross-population contamination forbidden —
    # do not feed funnel statistics into H1 correlation analyses.
    first_task_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    first_timer_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    d1_return_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Transactional account email state. This is operational identity
    # infrastructure only; it must not feed behavioral inference,
    # Cortex, clean-data profiles, or adaptive scheduling.
    activation_email_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    activation_email_failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    activation_email_last_error: Mapped[Optional[str]] = mapped_column(String(80))


class EmailEngagementEvent(Base):
    """Operational email engagement telemetry.

    These rows measure campaign delivery outcomes such as opens and clicks.
    They are not clean execution evidence and must not feed behavioral
    inference, Cortex, calibration, adaptive scheduling, or user-facing claims.
    Open events are best-effort because email clients often block tracking
    pixels; click events are the stronger re-entry signal.
    """

    __tablename__ = "email_engagement_event"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("user.user_id", ondelete="SET NULL"), nullable=True
    )
    campaign_version: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_key: Mapped[str] = mapped_column(String(32), nullable=False)
    target_url: Mapped[Optional[str]] = mapped_column(String(1024))
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(128))
    request_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index(
            "idx_email_engagement_campaign_event",
            "campaign_version",
            "event_type",
            "occurred_at",
        ),
        Index("idx_email_engagement_user", "user_id", "occurred_at"),
        Index("idx_email_engagement_recipient", "campaign_version", "recipient_key"),
    )


class Archetype(Base):
    """Behavioral archetype lookup. Seeded from docs/methodology.md §1."""

    __tablename__ = "archetype"

    archetype_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    prior_bias_factor: Mapped[float] = mapped_column(Float, nullable=False)
    prior_sigma: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)


class ArchetypeAssignment(Base):
    """Per-user archetype assignment + raw instrument scores for re-bucketing.

    Alembic 031 (2026-04-22) added `completed`, `skipped_at`,
    `raw_responses` — distinguishes genuine survey-answered
    assignments from skip-defaulted Diffuse Average rows. Skipped
    assignments have `completed=False`, `skipped_at` stamped,
    `raw_responses=NULL`. Completed assignments have `completed=True`,
    `skipped_at=NULL`, `raw_responses` = 29-item answer array.
    Retention analyses that want "genuine clustering" exclude
    `completed=False` rows; analyses that want "all assignments
    including defaults" include everything.
    """

    __tablename__ = "archetype_assignment"

    assignment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.user_id"), nullable=False)
    archetype_id: Mapped[str] = mapped_column(String(40), ForeignKey("archetype.archetype_id"), nullable=False)
    meq_score: Mapped[Optional[int]] = mapped_column(Integer)
    bfi_c_score: Mapped[Optional[int]] = mapped_column(Integer)
    bscs_score: Mapped[Optional[int]] = mapped_column(Integer)
    gp_score: Mapped[Optional[int]] = mapped_column(Integer)
    chronotype: Mapped[Optional[str]] = mapped_column(String(20))
    discipline_z: Mapped[Optional[float]] = mapped_column(Float)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    # Alembic 031 additions (2026-04-22).
    completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    skipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Raw 29-item responses: {"meq": [a,b,c,d,e], "bfi_c": [a,b],
    # "bscs": [...13 items...], "gp": [...9 items...]}. Enables
    # re-scoring under future weight tuning without re-surveying
    # (Gate 3/4 remediation). NULL for skip-defaulted assignments.
    raw_responses: Mapped[Optional[dict]] = mapped_column(JSON)


class ExternalEventOutcome(Base):
    """User-marked attendance on imported external calendar events.

    Path B (2026-04-21): the "Did you attend?" yes/no on /today cards
    for Google Calendar-imported events lands here. NOT in the `task`
    table — imported events never enter H1's test set. See
    docs/strategic_decisions_april_21.md §6 (VT-23: external-source
    attendance self-report).
    """

    __tablename__ = "external_event_outcome"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # ON DELETE CASCADE added in alembic 028 (2026-04-22). User deletion
    # purges outcome rows atomically — see LYR-103 note for the
    # retention-consistency follow-up (task/stopwatch_session anonymize
    # on retention; this table currently purges either way).
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_source: Mapped[str] = mapped_column(String(32), nullable=False)  # 'google_calendar'
    external_id: Mapped[str] = mapped_column(String(256), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)  # 'attended' | 'skipped'
    event_title: Mapped[Optional[str]] = mapped_column(Text)
    event_start_utc: Mapped[Optional[datetime]] = mapped_column(DateTime)
    event_end_utc: Mapped[Optional[datetime]] = mapped_column(DateTime)
    marked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class PauseEvent(Base):
    """One row per pause, created on pause() and closed on resume().

    Replaces the silent-overwrite pattern that was losing earlier pause metadata
    when a session had more than one pause (alembic 020). Source of truth for
    pause-prediction clock-anchor and work-rhythm algorithms.

    pause_reason and pause_initiator are NOT NULL — callers must supply both
    explicitly. The silent defaults at stopwatch_manager.py:330-331 were removed
    in the same commit batch that introduced this table; any omission is now a
    400 at the API boundary rather than contaminated research data.
    """

    __tablename__ = "pause_event"

    pause_event_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("stopwatch_session.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    paused_at_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resumed_at_utc: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_minutes: Mapped[Optional[float]] = mapped_column(Float)
    pause_reason: Mapped[str] = mapped_column(String(50), nullable=False)
    pause_initiator: Mapped[str] = mapped_column(String(20), nullable=False)
    active_elapsed_at_pause_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    # Flag for pauses captured via the retroactive-confirmation chip
    # (2026-04-22, alembic 030). False = real-time pause via timer
    # action. True = operator confirmed the pause retroactively after
    # a prediction fired as `no_response`. VT-17d stratified analysis
    # reports acceptance rate with and without retroactive-confirmed
    # rows (MANIFESTO v1.9 §VT-17d).
    self_reported_retroactively: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_pause_event_user_paused_at", "user_id", "paused_at_utc"),
        Index("idx_pause_event_session", "session_id"),
    )


class PausePredictionLog(Base):
    """Pre-registered research artifact for VT-17 analyses (MANIFESTO.md).

    One row per prediction firing. user_response and response_at are NULL at
    fire time and filled by the reconciliation job: 'pause_now' if a pause_event
    landed in the acceptance window, 'dismiss' for explicit dismissal signals,
    'snooze' for snooze-and-refire (with parent_firing_id linking the chain),
    'no_response' if the acceptance window closed with no pause.

    Acceptance-rate formula is pre-registered and frozen at feature launch —
    see MANIFESTO.md §VT-17. Snoozes are excluded from the kill-criterion
    denominator (parent_firing_id IS NOT NULL marks re-fires).
    """

    __tablename__ = "pause_prediction_log"

    firing_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # 'clock_anchor' | 'work_rhythm' — enforced in services/pause_predictor.py
    mechanism: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    lead_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    active_task_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("task.task_id", ondelete="SET NULL")
    )
    # NULL at fire time. 'pause_now' | 'dismiss' | 'snooze' | 'no_response'.
    user_response: Mapped[Optional[str]] = mapped_column(String(20))
    response_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    parent_firing_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("pause_prediction_log.firing_id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_pause_pred_user_fired_at", "user_id", "fired_at"),
    )


class ResumePredictionLog(Base):
    """W2 (alembic 038, 2026-04-28) — magic-for-alpha resume prediction.

    Sibling of PausePredictionLog. One row per resume-banner firing. The
    predictor checks active paused sessions every 2min — if the user's
    paused-for duration approaches their historical p75 for the active
    task's (category, time_of_day) cell, fire a banner: "You usually
    resume by now."

    Cold-start: when fewer than 5 samples exist for the cell OR the
    user has <7 days of pause history, mechanism='cold_start_synthetic'
    and the trigger is a flat 30-min cap with observational copy
    "LyraOS hasn't seen enough yet — picking it up?".

    Pre-registered footprint: VT-17 sibling (instrument-intervention
    threats apply symmetrically — anchor drift + induced-resume risk).
    Per docs/manifesto_alignment_audit_2026_04_28.md item #4: at
    n ≥ 30 firings per user, run VT-17a/b parallel analysis with
    pause→resume substitution. No new MANIFESTO rule yet (sample-size
    threshold not crossed).
    """

    __tablename__ = "resume_prediction_log"

    firing_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stopwatch_session.session_id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("task.task_id", ondelete="CASCADE"), nullable=False
    )
    fired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    paused_for_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    # NULL when cold_start_synthetic (no historical p75 to display).
    p75_pause_minutes: Mapped[Optional[float]] = mapped_column(Float)
    # 'category_tod' | 'cold_start_synthetic'
    mechanism: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    # NULL at fire time. 'resumed_within_window' | 'ignored' | 'snoozed' | 'no_response'.
    user_response: Mapped[Optional[str]] = mapped_column(String(20))
    response_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_resume_pred_user_fired_at", "user_id", "fired_at"),
        Index("idx_resume_pred_session", "session_id"),
    )


class CalibrationNudgeEvent(Base):
    """Per-fire calibration nudge event + decision + outcome (Loop 1).

    Pre-registered in `docs/archive/legacy/planning/feedback_loops_closure_plan.md §Loop 1`. Captures
    every NewTaskModal nudge fire + user decision (accepted | dismissed) +
    the executed_duration_minutes outcome once the bound task transitions
    to EXECUTED. Enables the "did the nudge improve calibration?" research
    question by comparing mean delta on accepted vs dismissed events.

    Lifecycle:
      1. NewTaskModal computes a calibration suggestion via
         `lookupBiasFactor`. User decides "use suggested" (accepted) or
         keeps their typed duration (dismissed).
      2. Task creation (`POST /v1/tasks/create`) accepts optional
         `nudge_decision` + `nudge_*` fields. If present, TaskManager
         writes ONE CalibrationNudgeEvent row in the SAME transaction
         as the Task — ensuring task_id and event_id are both committed
         atomically (or both rolled back).
      3. When the task transitions to EXECUTED via
         `TaskManager.complete_task`, an inline reconciliation block
         queries this table by task_id and stamps
         executed_duration_minutes + resolved_at.
      4. If the task is voided post-creation, the event row's voided_at
         is set (NOT deleted) to keep the audit trail intact.

    Analytics: `GET /v1/analytics/calibration_nudge` aggregates
    user_decision='accepted' vs 'dismissed' delta means over rolling N days.

    voided_at_guard discipline (per `feedback_voided_at_guard` memory):
    every analytics query MUST filter `voided_at IS NULL`.
    """

    __tablename__ = "calibration_nudge_event"

    event_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), nullable=False
    )
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("task.task_id"), nullable=False
    )
    # What LyraOS suggested at nudge-fire time.
    suggested_duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    # What the user actually typed in.
    user_planned_duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    # Snapshot of bias_factor used to compute the suggestion (Rule-13 blend).
    bias_factor: Mapped[float] = mapped_column(Float, nullable=False)
    # n_sessions_in_cell at nudge-fire time. <30 → prior-dominant blend.
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    # 'accepted' (user used suggested_duration) or 'dismissed' (kept typed).
    user_decision: Mapped[str] = mapped_column(String(16), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Filled inline by TaskManager.complete_task on EXECUTED transition.
    executed_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Symmetry with task voiding (LYR-095 + Loop 11 outcome precedent).
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_cne_user_decided", "user_id", "decided_at"),
        Index("idx_cne_task", "task_id"),
    )


class ReflectionViewLog(Base):
    """Per-fired reflection-surface impression record (LYR-098 Commit 2b).

    Every micro_mirror / calibration_nudge / (future) archetype reveal /
    milestone banner writes a row here when the backend renders it. The
    client stamps `viewed_at` on impression and `dismissed_at` on
    dismissal; the server computes `dwell_seconds` on dismiss.

    Used by /insights history (so a dismissed reflection is retrievable
    later — see notification_patterns.md §Saved-to-history) and by
    VT-21 stratified analysis (surface-exposed vs surface-naive
    sessions — see MANIFESTO.md §VT-21 candidate).

    `task_id` is nullable: task-bound reflections link back for context;
    non-task reflections (archetype reveal, milestone banner) use NULL.

    `payload` stores the rendered string verbatim — helper text changes
    between releases (e.g., April 15 neutralization), historical rows
    must not be rewritten by later-version helpers.
    """

    __tablename__ = "reflection_view_log"

    view_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # 'micro_mirror' | 'calibration_nudge' (stop-time toast)
    # | 'creation_nudge' (task-creation modal, alembic 035)
    # | 'pause_prediction' (forward) | 'archetype_proximity' (forward)
    # | 'telemetry_*' (Phase 6 behavioral telemetry — per
    #   docs/calibration_contract.md R7; payload schemas in
    #   docs/reflection_view_log_schemas.md when Phase 6 lands)
    # — enforced at application layer.
    reflection_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Promoted from JSON payload to top-level column in alembic 045
    # (Phase 1.5, 2026-05-02). 'impression' (UI surface viewed by user)
    # vs 'telemetry' (Phase 6 behavioral capture). Btree-indexed for
    # WHERE event_class = 'impression' filters in VT-21 stratified
    # analysis paths post-Phase-6. Application-layer-enforced enum.
    # See docs/calibration_contract.md R7.1.
    event_class: Mapped[str] = mapped_column(
        String(20), nullable=False, default="impression"
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("task.task_id", ondelete="SET NULL")
    )
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    fired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    dwell_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    # Decision outcome on decisional surfaces. Per Phase 6 V3 spec
    # (`docs/archive/legacy/planning/phase_6_architecture_backlog.md:227`): for creation_nudge
    # this carries 'kept' / 'adjusted' / 'dismissed'. NULL on
    # informational surfaces (micro_mirror, banner). Added in alembic 035.
    outcome: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_reflection_view_user_fired_at", "user_id", "fired_at"),
        Index("idx_reflection_view_event_class", "event_class"),
    )


class ExposureDecisionEvent(Base):
    """Exposure Ledger v0 decision atom.

    Append-only record that a system-generated information injection was
    eligible, shown, delayed, suppressed, failed, or left unknown. This is not
    a causal attribution table. It exists so baseline-learning paths can prove
    exposure context was checked before treating downstream behavior as clean.
    """

    __tablename__ = "exposure_decision_event"

    exposure_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), nullable=False
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("task.task_id", ondelete="SET NULL")
    )
    eligible_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    decision_status: Mapped[str] = mapped_column(String(20), nullable=False)
    initiative: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    exposure_category: Mapped[str] = mapped_column(String(40), nullable=False)
    content_template_id: Mapped[Optional[str]] = mapped_column(String(120))
    trigger_source: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown")
    generating_model: Mapped[Optional[str]] = mapped_column(String(120))
    generating_version: Mapped[Optional[str]] = mapped_column(String(120))
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(128))
    data_snapshot_hash: Mapped[Optional[str]] = mapped_column(String(128))
    randomization_arm: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    randomization_policy_version: Mapped[Optional[str]] = mapped_column(String(80))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_exposure_decision_user_eligible", "user_id", "eligible_at"),
        Index("idx_exposure_decision_task", "task_id"),
        Index("idx_exposure_decision_category", "exposure_category"),
    )


class ExposureRenderEvent(Base):
    """Exposure Ledger v0 render atom.

    Captures the exact rendered stimulus that could enter the user's decision
    context. Interruptiveness and salience live here because they are
    properties of the rendering surface, not the decision to generate content.
    """

    __tablename__ = "exposure_render_event"

    render_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    exposure_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("exposure_decision_event.exposure_id", ondelete="CASCADE"),
        nullable=False,
    )
    rendered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    surface: Mapped[str] = mapped_column(String(80), nullable=False)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    content_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    render_policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    interruptiveness: Mapped[str] = mapped_column(String(20), nullable=False)
    salience_level: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_exposure_render_exposure", "exposure_id"),
        Index("idx_exposure_render_rendered", "rendered_at"),
    )


class ExposureAckEvent(Base):
    """Frontend exposure acknowledgement atom (Wave 6).

    Decision rows say the system chose to show something. Render rows preserve
    the exact stimulus snapshot. Ack rows are the authenticated client boundary:
    the browser reports that a renderable exposure reached the rendered UI.

    Idempotency is intentionally narrow: a retried render acknowledgement for
    the same exposure returns the same row through the service layer.
    """

    __tablename__ = "exposure_ack_event"

    ack_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    exposure_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("exposure_decision_event.exposure_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    acked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    client_event_id: Mapped[Optional[str]] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "exposure_id",
            "event_type",
            name="uq_exposure_ack_exposure_event_type",
        ),
        Index("idx_exposure_ack_user_acked", "user_id", "acked_at"),
        Index("idx_exposure_ack_exposure", "exposure_id"),
    )


class NotificationLifecycleEvent(Base):
    """Durable lifecycle row for user-facing notification delivery.

    Redis remains the short-lived delivery queue. This table is the audit
    boundary that distinguishes queued/reserved notifications from stimuli that
    actually reached the browser UI.
    """

    __tablename__ = "notification_lifecycle_event"

    event_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.user_id"),
        nullable=False,
    )
    notification_id: Mapped[str] = mapped_column(String(120), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False, default="web")
    notification_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued")
    dedupe_key: Mapped[Optional[str]] = mapped_column(String(200))
    payload_hash: Mapped[Optional[str]] = mapped_column(String(128))
    content_snapshot: Mapped[Optional[str]] = mapped_column(Text)
    surface_id: Mapped[Optional[str]] = mapped_column(String(120))
    exposure_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("exposure_decision_event.exposure_id", ondelete="SET NULL"),
    )
    task_id: Mapped[Optional[str]] = mapped_column(String(36))
    session_id: Mapped[Optional[str]] = mapped_column(String(36))
    firing_id: Mapped[Optional[str]] = mapped_column(String(36))
    queued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reserved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rendered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    acted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    expired_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    lost_unrendered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_transition_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "notification_id",
            "channel",
            name="uq_notification_lifecycle_user_notification_channel",
        ),
        Index("idx_notification_lifecycle_user_created", "user_id", "created_at"),
        Index("idx_notification_lifecycle_status", "status"),
        Index("idx_notification_lifecycle_dedupe", "user_id", "dedupe_key"),
        Index("idx_notification_lifecycle_exposure", "exposure_id"),
    )


class SuppressionEvent(Base):
    """Exposure Ledger v0 suppression atom.

    Records an eligible exposure that was withheld. Suppression is not user
    exposure, but it is required to distinguish "nothing eligible" from
    "eligible but intentionally not shown".
    """

    __tablename__ = "suppression_event"

    suppression_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    exposure_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("exposure_decision_event.exposure_id", ondelete="CASCADE"),
        nullable=False,
    )
    suppressed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    suppression_reason: Mapped[str] = mapped_column(String(40), nullable=False)
    would_have_rendered_template_id: Mapped[Optional[str]] = mapped_column(String(120))
    generating_confidence: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_suppression_exposure", "exposure_id"),
        Index("idx_suppression_suppressed", "suppressed_at"),
    )


class ExposurePolicyEffectLog(Base):
    """Diagnostic snapshot of how a horizon policy affects baseline gates.

    This is not behavioral telemetry. It is meta-instrumentation for detecting
    whether the exposure gate itself drifts into invisible authority: too many
    false-clean rows, too many unknowns, or widespread ledger incompleteness.
    """

    __tablename__ = "exposure_policy_effect_log"

    log_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.user_id"), nullable=False
    )
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    exposure_category: Mapped[str] = mapped_column(String(40), nullable=False)
    signal_target: Mapped[str] = mapped_column(String(40), nullable=False)
    state_distribution_counts: Mapped[dict] = mapped_column(JSON, nullable=False)
    unknown_rate: Mapped[float] = mapped_column(Float, nullable=False)
    ledger_incomplete_rate: Mapped[float] = mapped_column(Float, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_exposure_policy_effect_user_created", "user_id", "created_at"),
        Index("idx_exposure_policy_effect_policy_target", "policy_version", "signal_target"),
    )


class Feedback(Base):
    """Alpha-cohort feedback channel (alembic 040, 2026-04-28).

    Operator-facing triage queue. Users submit via the in-app feedback
    widget; rows here flow to operator email + Telegram (best-effort
    notifiers). Operator triages via GET /v1/admin/feedback +
    POST /v1/admin/feedback/{id}/resolve.

    `kind` enum: 'bug' | 'suggestion' | 'confused' | 'other'
    `status` enum: 'unread' | 'read' | 'acted_on' | 'dismissed'

    Optional context fields (page_url, user_agent, error_context) help
    operator reproduce; user opts in via a checkbox at submit time.
    """

    __tablename__ = "feedback"

    feedback_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("user.user_id", ondelete="SET NULL")
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    page_url: Mapped[Optional[str]] = mapped_column(String(500))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    error_context: Mapped[Optional[list]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unread"
    )
    operator_note: Mapped[Optional[str]] = mapped_column(Text)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_feedback_status_submitted", "status", "submitted_at"),
    )


class JarvisInvocation(Base):
    """JARVIS tool-call audit trail (alembic 042, 2026-04-30).

    One row per JARVIS tool call. Read tools insert with status='executed'
    immediately; write tools insert with status='pending_confirmation'
    and flip to 'executed' (with confirmed_at stamped) when the user
    clicks the confirmation chip in the chat UI, or 'rejected' on cancel.

    Defense-in-depth on multi-tenancy: every JARVIS read/write tool
    already runs under the auto-scoping ContextVar (current_user_id);
    the user_id column here is a redundant audit field that lets us
    reconstruct who-did-what after the fact even if the scoping layer
    were ever bypassed.

    Truncation rule: tool_result_summary is capped at 500 chars by the
    write path. Storing full results (think: 50-task list responses)
    would balloon this table. The summary is for human/operator review;
    the actual tool result lives in the chat session message thread.
    """

    __tablename__ = "jarvis_invocation"

    invocation_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # OpenAI-style tool args dict. Bounded by the tool schema declared in
    # services/jarvis_tools.py — most args are scalars or short strings.
    tool_args: Mapped[Optional[dict]] = mapped_column(JSON)
    tool_result_summary: Mapped[Optional[str]] = mapped_column(String(500))
    # 'executed' | 'pending_confirmation' | 'rejected' | 'failed'
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="executed"
    )
    invoked_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    # Stamped only when the user explicitly confirms a pending write.
    # confirmed_at − invoked_at = how long the user took to greenlight
    # JARVIS to act (a reasoning-time signal we may surface later).
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("ix_jarvis_invocation_user_invoked_at", "user_id", "invoked_at"),
    )


class SecurityAuditEvent(Base):
    """Append-only security/governance audit event.

    This table is deliberately not behavioral telemetry. Rows here exist for
    authentication, access-control, provider-connection, account-governance,
    and topology/secret incident review only. They must never be consumed by
    Cortex, clean-data profiles, adaptive scheduling, productivity inference,
    or user behavior analysis.
    """

    __tablename__ = "security_audit_event"

    event_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    actor_user_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    surface: Mapped[str] = mapped_column(String(160), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(80))
    target_id: Mapped[Optional[str]] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64))
    user_agent_hash: Mapped[Optional[str]] = mapped_column(String(64))
    redacted_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    __table_args__ = (
        Index("idx_security_audit_event_created", "created_at"),
        Index("idx_security_audit_event_type_created", "event_type", "created_at"),
        Index("idx_security_audit_actor_created", "actor_user_id", "created_at"),
        Index("idx_security_audit_user_created", "user_id", "created_at"),
    )
