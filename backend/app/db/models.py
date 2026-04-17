"""SQLAlchemy models for Lyra Secretary."""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
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

    # Notion sync
    notion_page_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)

    # Multi-user ownership (alembic 014)
    # NO default — writes MUST pass user_id explicitly. The prior default=1
    # silently funneled every cross-tenant write to the operator (LYR-093).
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Relationships
    stopwatch_sessions: Mapped[list["StopwatchSession"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "state IN ('PLANNED', 'EXECUTING', 'PAUSED', 'EXECUTED', 'SKIPPED', 'DELETED')",
            name="check_state"
        ),
        CheckConstraint(
            "source IN ('manual', 'voice', 'web')",
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
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Africa/Cairo")
    is_operator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notion_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archetype_id: Mapped[Optional[str]] = mapped_column(String(40), ForeignKey("archetype.archetype_id"))
    terms_accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    research_consent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class Archetype(Base):
    """Behavioral archetype lookup. Seeded from docs/methodology.md §1."""

    __tablename__ = "archetype"

    archetype_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    prior_bias_factor: Mapped[float] = mapped_column(Float, nullable=False)
    prior_sigma: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)


class ArchetypeAssignment(Base):
    """Per-user archetype assignment + raw instrument scores for re-bucketing."""

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
    # 'micro_mirror' | 'calibration_nudge' — enforced at application layer.
    reflection_type: Mapped[str] = mapped_column(String(30), nullable=False)
    task_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("task.task_id", ondelete="SET NULL")
    )
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    fired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    dwell_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_reflection_view_user_fired_at", "user_id", "fired_at"),
    )
