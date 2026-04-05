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
    EXECUTED = "EXECUTED"
    SKIPPED = "SKIPPED"
    DELETED = "DELETED"


class TaskSource(str, Enum):
    """How the task was created."""
    MANUAL = "manual"
    VOICE = "voice"


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

    # Notion sync
    notion_page_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    
    # Relationships
    stopwatch_sessions: Mapped[list["StopwatchSession"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "state IN ('PLANNED', 'EXECUTING', 'EXECUTED', 'SKIPPED', 'DELETED')",
            name="check_state"
        ),
        CheckConstraint(
            "source IN ('manual', 'voice')",
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
        return self.state not in (TaskState.EXECUTED, TaskState.SKIPPED, TaskState.DELETED)
    
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
    total_paused_minutes: Mapped[int] = mapped_column(Integer, default=0)
    
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
    def duration_minutes(self) -> Optional[int]:
        """Duration in minutes (if stopped)."""
        if self.end_time_utc is None:
            return None
        delta = self.end_time_utc - self.start_time_utc
        return int(delta.total_seconds() / 60)


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
