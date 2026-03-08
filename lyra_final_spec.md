# Lyra Secretary v1.1
## Complete Implementation Specification
**Master Technical Specification + Implementation Guide**

---

**Version:** v1.1 Final  
**Status:** Implementation Ready  
**Philosophy:** Learning-First, Production-Quality  
**Target Deployment:** 14 Days  
**Project Path:** `d:\Projects\Adaptive scheduler 2`

---

## Table of Contents

1. [Vision & Philosophy](#1-vision--philosophy)
2. [System Architecture](#2-system-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Database Schema](#5-database-schema)
6. [Pydantic Schemas](#6-pydantic-schemas)
7. [Core Services](#7-core-services)
8. [API Endpoints](#8-api-endpoints)
9. [Redis Patterns](#9-redis-patterns)
10. [External Integrations](#10-external-integrations)
11. [Workers & Scheduler](#11-workers--scheduler)
12. [OpenClaw Configuration](#12-openclaw-configuration)
13. [Architectural Principles](#13-architectural-principles)
14. [Critical Requirements](#14-critical-requirements)
15. [Testing Strategy](#15-testing-strategy)
16. [Deployment](#16-deployment)
17. [Implementation Timeline](#17-implementation-timeline)
18. [Vibe-Code Prompts](#18-vibe-code-prompts)

---

## 1. Vision & Philosophy

### 1.1 What Lyra Secretary Actually Is

Lyra Secretary is **not a todo app**. It is the first organ of a personal cognitive operating system where the adaptive scheduler functions as the nervous system.

**The Core Innovation:**
```python
delta = planned_duration_minutes - executed_duration_minutes
```

**Example:**
```
Planned: Gym 120 min
Actual:  Gym 90 min
Delta: +30 min (finished early)

Over time:
gym_avg_delta = +5 min   (you're efficient at gym)
study_avg_delta = -25 min (studying takes longer than planned)
```

**This data enables future AI to adaptively schedule tasks based on your actual behavior patterns.**

Everything else (Telegram, Notion, parsing) is interface decoration.

### 1.2 Design Philosophy

**Learning-First Implementation:**
- Every component teaches a valuable backend skill
- Architecture over features
- Clarity over cleverness
- Production-quality code that's educational

**Core Principles:**
1. **Cognition ≠ Execution** - OpenClaw reasons, FastAPI executes
2. **Immutable History** - Executed tasks are truth, never modified
3. **Single Source of Truth** - SQLite is authoritative, Notion is presentation
4. **User Authority** - User has final decision power on all actions
5. **Deterministic Core** - FastAPI is predictable, no hidden state

### 1.3 Scope Definition

**✅ In Scope (v1.1):**
- Text input via Telegram (natural language parsing)
- Voice input via Telegram (Whisper transcription)
- Task creation, rescheduling, deletion
- Stopwatch-based execution tracking
- Manual logging (without stopwatch)
- Conflict detection (warn, don't block)
- Search and query
- 30-second undo window
- Notion calendar sync (one-way push)
- Pre-task reminders
- Redis-based stopwatch persistence

**❌ Out of Scope (Removed for v1.1):**
- ~~OCR/Image parsing~~ (unnecessary ML complexity)
- ~~Insights engine~~ (no data for 2-3 months)
- ~~Category learning~~ (use static seed data)
- ~~Notion external edit detection~~ (premature complexity)
- ~~Grace period auto-skip~~ (behavior will change frequently)
- ~~Audit event table~~ (SQLite history sufficient)
- ~~Input flood protection~~ (single user, unnecessary)

**🔴 Critical Additions (Were Missing):**
- ✅ Timezone handling (UTC storage, Cairo display)
- ✅ Idempotency keys (Telegram webhook duplicates)
- ✅ Transaction safety (atomic mutations)
- ✅ Failure recovery (orphaned stopwatches)

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER (Telegram Bot)                  │
│                                                         │
│  Input: Text, Voice                                     │
│  Output: Formatted responses, notifications             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Webhook
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  OPENCLAW (Cognitive Layer)             │
│                         🧠                               │
│                                                         │
│  Responsibilities:                                      │
│  • Understand natural language intent                   │
│  • Ask clarifying questions                             │
│  • Orchestrate multi-step workflows                     │
│  • Format responses naturally                           │
│  • Call external APIs (Whisper)                         │
│  • Invoke FastAPI tools via Skills                      │
│                                                         │
│  ❌ DOES NOT:                                           │
│  • Store task data                                      │
│  • Enforce business rules                               │
│  • Manage database state                                │
│                                                         │
│  Skills (HTTP Tools):                                   │
│  ├─ transcribe_voice (Whisper API)                      │
│  ├─ parse_input → POST /v1/parse                        │
│  ├─ create_task → POST /v1/tasks/create                 │
│  ├─ start_stopwatch → POST /v1/stopwatch/start          │
│  ├─ stop_stopwatch → POST /v1/stopwatch/stop            │
│  ├─ query_tasks → GET /v1/tasks/query                   │
│  ├─ reschedule_task → POST /v1/tasks/reschedule         │
│  ├─ delete_task → POST /v1/tasks/delete                 │
│  └─ undo → POST /v1/undo                                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ HTTP Skills
                       ▼
┌─────────────────────────────────────────────────────────┐
│            FASTAPI (Execution Layer / Brain)            │
│                        ⚙️                                │
│                                                         │
│  Responsibilities:                                      │
│  • Parse natural language → structured tasks            │
│  • Enforce state machine transitions                    │
│  • Validate all mutations                               │
│  • Detect time conflicts                                │
│  • Manage stopwatch lifecycle                           │
│  • Calculate durations and deltas                       │
│  • Sync to Notion (authoritative push)                  │
│  • Send scheduled notifications                         │
│  • Maintain transaction safety                          │
│  • Enforce immutability rules                           │
│                                                         │
│  ❌ DOES NOT:                                           │
│  • Interpret user intent                                │
│  • Format conversational responses                      │
│  • Maintain conversation context                        │
│                                                         │
│  Core Pattern: Single Mutation Authority                │
│  ┌─────────────────────────────────────┐               │
│  │      TaskManager (ONLY writer)      │               │
│  │  • create_task()                    │               │
│  │  • start_task()                     │               │
│  │  • complete_task()                  │               │
│  │  • skip_task()                      │               │
│  │  • delete_task()                    │               │
│  └─────────────────────────────────────┘               │
│           ▲                                             │
│           │ All writes flow through here                │
│           │                                             │
│  ┌────────┴──────────────────────────┐                 │
│  │  Parser  │  State    │  Conflict  │                 │
│  │          │  Machine  │  Detector  │                 │
│  └───────────────────────────────────┘                 │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ├────────────┬──────────────┬──────┐
                       ▼            ▼              ▼      ▼
              ┌─────────────┐  ┌────────┐  ┌──────────┐ ┌────────┐
              │   SQLite    │  │ Redis  │  │ Notion   │ │APSched │
              │             │  │        │  │  API     │ │        │
              │ • Tasks     │  │ • Stop │  │          │ │• Remind│
              │ • Sessions  │  │   watch│  │ Present- │ │• Retry │
              │ • Category  │  │ • Undo │  │  ation   │ │        │
              │             │  │ • Idem │  │  Layer   │ │        │
              └─────────────┘  └────────┘  └──────────┘ └────────┘
                  💾              🧠            🎨           ⏰
              Source of       Ephemeral     Read-Only    Background
                Truth           State        Calendar       Jobs
```

### 2.2 Data Flow (Unidirectional)

```
User Input (Text/Voice)
        ↓
OpenClaw (Understands Intent)
        ↓
FastAPI (Executes Logic)
        ↓
TaskManager (Single Mutation Authority)
        ↓
Database (UTC Storage)
        ↓
Notion (Sync/Display)
        ↓
OpenClaw (Format Response)
        ↓
User (Telegram Message)
```

**Critical Rule:** Data flows ONE direction. Notion/Telegram never modify database directly.

### 2.3 Layer Responsibilities

| Layer | Owns | Never Touches |
|-------|------|---------------|
| **OpenClaw** | Intent, reasoning, orchestration, conversation | Task state, business rules, database |
| **FastAPI** | Execution, validation, state, persistence | User intent interpretation, conversation |
| **TaskManager** | ALL task mutations | — |
| **Storage** | Truth, history, ephemeral state | Logic, decisions, formatting |

---

## 3. Tech Stack

### 3.1 Exact Versions (Critical)

**Backend (Python 3.11.7):**
```txt
# requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0
sqlalchemy==2.0.25
alembic==1.13.1
redis==5.0.1
httpx==0.26.0
python-telegram-bot==20.7
notion-client==2.2.1
dateparser==1.2.0
apscheduler==3.10.4
python-jose[cryptography]==3.3.0
python-multipart==0.0.6

# Dev dependencies
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
black==24.1.1
ruff==0.1.14
mypy==1.8.0
```

**Removed Dependencies:**
```txt
# ❌ NOT INCLUDED (removed features)
pytesseract  # No OCR
pillow       # No image processing
parsedatetime # Using dateparser only
```

**Infrastructure:**
```yaml
python: 3.11.7
redis: 7.2-alpine
```

### 3.2 Environment Variables

**`.env.example`:**
```bash
# Core
ENVIRONMENT=development  # development | staging | production
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key-min-32-chars

# Database
DATABASE_URL=sqlite:///./data/lyra.db

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=

# Telegram
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_URL=https://your-domain.com/telegram/webhook
TELEGRAM_WEBHOOK_SECRET=random-32-char-secret

# Notion
NOTION_API_KEY=secret_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
NOTION_DATABASE_ID=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

# OpenAI (for Whisper)
OPENAI_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Anthropic (for OpenClaw)
ANTHROPIC_API_KEY=sk-ant-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# User Context (CRITICAL)
USER_TIMEZONE=Africa/Cairo  # All times stored UTC, displayed in this timezone
USER_ID=user_primary

# Monitoring (Optional)
SENTRY_DSN=
```

---

## 4. Project Structure

```
lyra_secretary/
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
├── pyproject.toml
├── alembic.ini
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   │
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── endpoints/
│   │   │       │   ├── health.py
│   │   │       │   ├── parse.py
│   │   │       │   ├── tasks.py
│   │   │       │   ├── stopwatch.py
│   │   │       │   └── undo.py
│   │   │       └── router.py
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── exceptions.py
│   │   │   └── logging.py
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── models.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── task.py
│   │   │   ├── stopwatch.py
│   │   │   └── parse.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── parser.py
│   │   │   ├── task_manager.py        # ⭐ SINGLE MUTATION AUTHORITY
│   │   │   ├── state_machine.py
│   │   │   ├── conflict_detector.py
│   │   │   ├── stopwatch_manager.py
│   │   │   ├── notion_client.py
│   │   │   └── telegram_notifier.py
│   │   │
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   ├── scheduler.py
│   │   │   └── jobs/
│   │   │       ├── reminders.py
│   │   │       └── notion_sync.py
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── redis_client.py
│   │       ├── time_utils.py
│   │       └── retry.py
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       └── unit/
│           ├── test_parser.py
│           ├── test_state_machine.py
│           └── test_conflict_detector.py
│
├── openclaw/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config/
│   │   ├── agent.yml
│   │   └── prompts/
│   │       └── system_prompt.txt
│   ├── skills/
│   │   ├── transcribe_voice.py
│   │   └── telegram_handler.py
│   └── main.py
│
├── scripts/
│   ├── seed_categories.py
│   └── backup.sh
│
└── data/
    ├── lyra.db  # SQLite (gitignored)
    └── backups/
```

**Removed from Structure:**
```
❌ services/insights_generator.py
❌ services/category_learner.py (replaced with static seed)
❌ workers/jobs/grace_period.py
❌ api/v1/endpoints/insights.py
❌ openclaw/skills/extract_image_text.py
❌ db/models.py → AuditEvent table
```

---

## 5. Database Schema

### 5.1 SQLAlchemy Models

**`backend/app/db/models.py`:**

```python
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
```

### 5.2 Alembic Migration

**`backend/alembic/versions/001_initial_schema.py`:**

```python
"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-12-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Task table
    op.create_table(
        'task',
        sa.Column('task_id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        
        sa.Column('planned_start_utc', sa.DateTime(), nullable=False),
        sa.Column('planned_end_utc', sa.DateTime(), nullable=False),
        sa.Column('planned_duration_minutes', sa.Integer(), nullable=False),
        
        sa.Column('executed_start_utc', sa.DateTime(), nullable=True),
        sa.Column('executed_end_utc', sa.DateTime(), nullable=True),
        sa.Column('executed_duration_minutes', sa.Integer(), nullable=True),
        
        sa.Column('state', sa.String(20), nullable=False),
        sa.Column('source', sa.String(20), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_modified_at', sa.DateTime(), nullable=False),
        sa.Column('notion_page_id', sa.String(100), unique=True, nullable=True),
        
        sa.CheckConstraint(
            "state IN ('PLANNED', 'EXECUTING', 'EXECUTED', 'SKIPPED', 'DELETED')",
            name='check_state'
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'voice')",
            name='check_source'
        ),
        sa.CheckConstraint(
            'planned_duration_minutes > 0',
            name='check_planned_duration'
        ),
    )
    
    op.create_index('idx_task_state', 'task', ['state'])
    op.create_index('idx_task_start', 'task', ['planned_start_utc'])
    op.create_index('idx_task_category', 'task', ['category'])
    op.create_index('idx_task_created', 'task', ['created_at'])
    
    # StopwatchSession table
    op.create_table(
        'stopwatch_session',
        sa.Column('session_id', sa.String(36), primary_key=True),
        sa.Column('task_id', sa.String(36), nullable=False),
        sa.Column('start_time_utc', sa.DateTime(), nullable=False),
        sa.Column('end_time_utc', sa.DateTime(), nullable=True),
        sa.Column('auto_closed', sa.Boolean(), default=False),
        
        sa.ForeignKeyConstraint(['task_id'], ['task.task_id'], ondelete='CASCADE'),
    )
    
    op.create_index('idx_stopwatch_task', 'stopwatch_session', ['task_id'])
    
    # CategoryMapping table
    op.create_table(
        'category_mapping',
        sa.Column('keyword', sa.String(100), primary_key=True),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('confidence', sa.Float(), default=0.9),
        sa.Column('last_used', sa.DateTime(), nullable=False),
    )
    
    op.create_index(
        'idx_category_confidence',
        'category_mapping',
        ['category', 'confidence']
    )


def downgrade() -> None:
    op.drop_table('category_mapping')
    op.drop_table('stopwatch_session')
    op.drop_table('task')
```

### 5.3 Seed Data

**`scripts/seed_categories.py`:**

```python
"""Seed initial category mappings (STATIC - not learned)."""
from app.db.session import SessionLocal
from app.db.models import CategoryMapping
from datetime import datetime


INITIAL_MAPPINGS = {
    # Health
    "gym": "Health",
    "workout": "Health",
    "exercise": "Health",
    "cardio": "Health",
    "run": "Health",
    "yoga": "Health",
    
    # Study
    "study": "Study",
    "lecture": "Study",
    "class": "Study",
    "assignment": "Study",
    "homework": "Study",
    "exam": "Study",
    "quiz": "Study",
    "reading": "Study",
    
    # Work
    "meeting": "Work",
    "call": "Work",
    "project": "Work",
    "deadline": "Work",
    "presentation": "Work",
    
    # Personal
    "groceries": "Personal",
    "shopping": "Personal",
    "errands": "Personal",
    "appointment": "Personal",
    
    # Social
    "coffee": "Social",
    "lunch": "Social",
    "dinner": "Social",
}


def seed_categories():
    db = SessionLocal()
    try:
        for keyword, category in INITIAL_MAPPINGS.items():
            mapping = CategoryMapping(
                keyword=keyword.lower(),
                category=category,
                confidence=0.9,
                last_used=datetime.utcnow()
            )
            db.merge(mapping)
        
        db.commit()
        print(f"✅ Seeded {len(INITIAL_MAPPINGS)} category mappings")
    finally:
        db.close()


if __name__ == "__main__":
    seed_categories()
```

---

## 6. Pydantic Schemas

### 6.1 Task Schemas

**`backend/app/schemas/task.py`:**

```python
"""Pydantic schemas for task operations."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator
from app.db.models import TaskState, TaskSource


# Request schemas
class TaskParseRequest(BaseModel):
    """Request to parse natural language into task."""
    text: str = Field(..., min_length=1, max_length=500)


class TaskCreateRequest(BaseModel):
    """Request to create a new task."""
    title: str = Field(..., min_length=1, max_length=255)
    start: datetime
    end: datetime
    category: Optional[str] = Field(None, max_length=100)
    state: TaskState = TaskState.PLANNED
    source: TaskSource = TaskSource.MANUAL
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    force: bool = Field(False, description="Ignore conflicts if true")
    
    @validator('end')
    def end_after_start(cls, v, values):
        if 'start' in values and v <= values['start']:
            raise ValueError('end must be after start')
        return v


class TaskRescheduleRequest(BaseModel):
    """Request to reschedule a task."""
    task_id: str = Field(..., min_length=36, max_length=36)
    new_start: datetime
    new_end: Optional[datetime] = None  # If None, preserves duration
    
    @validator('new_end')
    def end_after_start(cls, v, values):
        if v is not None and 'new_start' in values and v <= values['new_start']:
            raise ValueError('new_end must be after new_start')
        return v


class TaskDeleteRequest(BaseModel):
    """Request to delete a task."""
    task_id: str = Field(..., min_length=36, max_length=36)


class TaskQueryRequest(BaseModel):
    """Request to query tasks."""
    q: Optional[str] = Field(None, description="Search keyword")
    state: Optional[TaskState] = None
    category: Optional[str] = None
    timeframe: Optional[str] = Field(
        None,
        description="today|this_week|last_week|this_month|last_month"
    )
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(1, ge=1)
    limit: int = Field(50, ge=1, le=100)


# Response schemas
class ConflictInfo(BaseModel):
    """Information about a conflicting task."""
    task_id: str
    title: str
    start: datetime
    end: datetime
    state: TaskState


class TaskParseResponse(BaseModel):
    """Response from parsing natural language."""
    title: str
    start: datetime
    end: Optional[datetime]
    duration_minutes: Optional[int]
    category: Optional[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
    ambiguities: list[str] = Field(default_factory=list)


class TaskCreateResponse(BaseModel):
    """Response from creating a task."""
    task_id: Optional[str]
    created: bool
    conflicts: list[ConflictInfo] = Field(default_factory=list)
    can_proceed: bool = True


class TaskDetail(BaseModel):
    """Detailed task information."""
    task_id: str
    title: str
    category: Optional[str]
    
    planned_start: datetime
    planned_end: datetime
    planned_duration_minutes: int
    
    executed_start: Optional[datetime]
    executed_end: Optional[datetime]
    executed_duration_minutes: Optional[int]
    
    state: TaskState
    source: TaskSource
    confidence_score: Optional[float]
    notes: Optional[str]
    
    created_at: datetime
    last_modified_at: datetime
    
    # Computed fields
    duration_delta_minutes: Optional[int]
    is_mutable: bool
    
    class Config:
        from_attributes = True


class TaskQueryResponse(BaseModel):
    """Response from querying tasks."""
    tasks: list[TaskDetail]
    total: int
    page: int
    has_more: bool


class TaskRescheduleResponse(BaseModel):
    """Response from rescheduling a task."""
    task_id: str
    rescheduled: bool
    new_start: datetime
    new_end: datetime
    conflicts: list[ConflictInfo] = Field(default_factory=list)


class TaskDeleteResponse(BaseModel):
    """Response from deleting a task."""
    task_id: str
    deleted: bool
```

### 6.2 Stopwatch Schemas

**`backend/app/schemas/stopwatch.py`:**

```python
"""Pydantic schemas for stopwatch operations."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class StopwatchStartRequest(BaseModel):
    """Request to start stopwatch."""
    task_id: Optional[str] = Field(
        None,
        description="If None, creates new unplanned task"
    )
    title: Optional[str] = Field(
        None,
        description="Required if task_id is None"
    )


class StopwatchStartResponse(BaseModel):
    """Response from starting stopwatch."""
    session_id: str
    task_id: str
    start_time: datetime


class StopwatchStopResponse(BaseModel):
    """Response from stopping stopwatch."""
    task_id: str
    session_id: str
    duration_minutes: int
    planned_duration_minutes: Optional[int]
    delta_minutes: Optional[int]
    executed_at: datetime


class StopwatchStatusResponse(BaseModel):
    """Current stopwatch status."""
    active: bool
    session_id: Optional[str]
    task_id: Optional[str]
    task_title: Optional[str]
    start_time: Optional[datetime]
    elapsed_minutes: Optional[int]
```

### 6.3 Parse Schema

**`backend/app/schemas/parse.py`:**

```python
"""Pydantic schemas for parsing."""
from pydantic import BaseModel, Field

# Already defined in task.py
# Included here for clarity

class ParseRequest(BaseModel):
    """Request to parse natural language."""
    text: str = Field(..., min_length=1, max_length=500)


class ParseResponse(BaseModel):
    """Response from parsing."""
    # Same as TaskParseResponse
    pass
```

---

## 7. Core Services

### 7.1 Config

**`backend/app/config.py`:**

```python
"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Core
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/lyra.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_URL: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    
    # Notion
    NOTION_API_KEY: str
    NOTION_DATABASE_ID: str
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    
    # User Context (CRITICAL)
    USER_TIMEZONE: str = "Africa/Cairo"
    USER_ID: str = "user_primary"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
```

### 7.2 Time Utils (CRITICAL)

**`backend/app/utils/time_utils.py`:**

```python
"""Timezone conversion utilities.

CRITICAL RULE: All times stored in UTC, displayed in user's local time.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from app.config import settings


def to_utc(local_dt: datetime) -> datetime:
    """
    Convert local datetime to UTC.
    
    Args:
        local_dt: Datetime in user's timezone (Africa/Cairo)
        
    Returns:
        Datetime in UTC
    """
    if local_dt.tzinfo is None:
        # Assume user's timezone
        tz = ZoneInfo(settings.USER_TIMEZONE)
        local_dt = local_dt.replace(tzinfo=tz)
    
    return local_dt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def to_local(utc_dt: datetime) -> datetime:
    """
    Convert UTC datetime to user's local time.
    
    Args:
        utc_dt: Datetime in UTC
        
    Returns:
        Datetime in user's timezone (Africa/Cairo)
    """
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=ZoneInfo("UTC"))
    
    tz = ZoneInfo(settings.USER_TIMEZONE)
    return utc_dt.astimezone(tz).replace(tzinfo=None)


def now_utc() -> datetime:
    """Get current time in UTC."""
    return datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)


def now_local() -> datetime:
    """Get current time in user's timezone."""
    tz = ZoneInfo(settings.USER_TIMEZONE)
    return datetime.now(tz).replace(tzinfo=None)
```

### 7.3 Parser (Core NLP)

**`backend/app/services/parser.py`:**

```python
"""Natural language task parser."""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
import dateparser

from app.schemas.task import TaskParseResponse
from app.db.session import SessionLocal
from app.db.models import CategoryMapping
from app.config import settings
from app.utils.time_utils import to_utc, now_local


class TaskParser:
    """Parse natural language into structured task data."""
    
    def __init__(self):
        self.user_tz = settings.USER_TIMEZONE
        self.db = SessionLocal()
    
    def parse(self, text: str) -> TaskParseResponse:
        """
        Parse natural language text into task components.
        
        Args:
            text: Natural language task description
            
        Returns:
            TaskParseResponse with extracted data and confidence score
        """
        text = text.strip()
        ambiguities = []
        
        # Extract title (everything before time indicators)
        title, remaining = self._extract_title(text)
        
        # Extract time components
        start, end, duration_minutes, time_confidence = self._extract_time(
            remaining or text
        )
        
        # If no time found, try full text
        if start is None:
            start, end, duration_minutes, time_confidence = self._extract_time(text)
            if start is not None:
                title, _ = self._extract_title(
                    re.sub(r'\b(at|from|@)\b.*', '', text, flags=re.IGNORECASE)
                )
        
        # Handle missing end time
        if start and end is None and duration_minutes is None:
            ambiguities.append("duration_missing")
        
        # Infer category (from static mappings)
        category = self._infer_category(title)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(
            title, start, end, duration_minutes, time_confidence
        )
        
        # If end is missing but duration exists, calculate end
        if start and end is None and duration_minutes:
            end = start + timedelta(minutes=duration_minutes)
        
        # Convert to UTC for storage
        start_utc = to_utc(start) if start else now_local()
        end_utc = to_utc(end) if end else None
        
        return TaskParseResponse(
            title=title or "Untitled Task",
            start=start_utc,
            end=end_utc,
            duration_minutes=duration_minutes,
            category=category,
            confidence=confidence,
            ambiguities=ambiguities
        )
    
    def _extract_title(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract task title from text.
        
        Returns:
            (title, remaining_text)
        """
        time_indicators = r'\b(at|from|@|tomorrow|today|tonight|in|next|this)\b'
        
        match = re.search(time_indicators, text, re.IGNORECASE)
        if match:
            title = text[:match.start()].strip()
            remaining = text[match.start():].strip()
            return title, remaining
        
        return text, None
    
    def _extract_time(
        self, text: str
    ) -> Tuple[Optional[datetime], Optional[datetime], Optional[int], float]:
        """
        Extract time components from text.
        
        Returns:
            (start, end, duration_minutes, confidence)
        """
        if not text:
            return None, None, None, 0.0
        
        # Use dateparser with user's timezone
        settings_dict = {
            'TIMEZONE': self.user_tz,
            'RETURN_AS_TIMEZONE_AWARE': False,
            'PREFER_DATES_FROM': 'future',
        }
        
        parsed = dateparser.parse(text, settings=settings_dict)
        if parsed:
            # If time is in past (same day), adjust to tomorrow
            now = now_local()
            if parsed.date() == now.date() and parsed.time() < now.time():
                parsed = parsed + timedelta(days=1)
            
            duration_minutes = self._extract_duration(text)
            end = self._extract_end_time(text, parsed)
            
            return parsed, end, duration_minutes, 0.85
        
        return None, None, None, 0.0
    
    def _extract_duration(self, text: str) -> Optional[int]:
        """Extract duration in minutes from text."""
        # Range pattern (e.g., "2-3 hours") → use MAX
        range_pattern = r'(\d+)\s*[-–]\s*(\d+)\s*(hours?|hrs?|h|minutes?|mins?|m)'
        match = re.search(range_pattern, text, re.IGNORECASE)
        if match:
            max_val = int(match.group(2))
            unit = match.group(3).lower()
            
            if 'h' in unit:
                return max_val * 60
            else:
                return max_val
        
        # Single duration
        single_pattern = r'(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)'
        match = re.search(single_pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            
            if 'h' in unit:
                return int(value * 60)
            else:
                return int(value)
        
        return None
    
    def _extract_end_time(
        self, text: str, start: datetime
    ) -> Optional[datetime]:
        """Try to extract explicit end time."""
        patterns = [
            r'(?:to|until|till|-|–)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
            r'(?:ends?\s+at)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                end_str = match.group(1)
                end = dateparser.parse(
                    end_str,
                    settings={'TIMEZONE': self.user_tz, 'RELATIVE_BASE': start}
                )
                if end and end > start:
                    return end
        
        return None
    
    def _infer_category(self, title: str) -> Optional[str]:
        """Infer category from static keyword mappings."""
        title_lower = title.lower()
        
        # Query database for matching keywords
        for word in title_lower.split():
            mapping = self.db.query(CategoryMapping).filter(
                CategoryMapping.keyword == word
            ).first()
            
            if mapping:
                return mapping.category
        
        return None
    
    def _calculate_confidence(
        self,
        title: Optional[str],
        start: Optional[datetime],
        end: Optional[datetime],
        duration: Optional[int],
        time_confidence: float
    ) -> float:
        """Calculate overall parsing confidence."""
        confidence = 0.0
        
        if title and len(title) > 1:
            confidence += 0.3
        
        if start:
            confidence += 0.3
        
        if end or duration:
            confidence += 0.2
        
        confidence += time_confidence * 0.2
        
        return min(confidence, 1.0)
```

### 7.4 State Machine

**`backend/app/services/state_machine.py`:**

```python
"""Task state machine enforcement."""
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import Task, TaskState
from app.core.exceptions import (
    ImmutableTaskError,
    InvalidStateTransitionError
)


class StateMachine:
    """Enforce task state transition rules."""
    
    # Valid transitions
    TRANSITIONS = {
        TaskState.PLANNED: {
            TaskState.EXECUTING,
            TaskState.EXECUTED,
            TaskState.SKIPPED,
            TaskState.DELETED
        },
        TaskState.EXECUTING: {
            TaskState.EXECUTED
        },
        TaskState.EXECUTED: set(),  # Immutable
        TaskState.SKIPPED: set(),   # Immutable
        TaskState.DELETED: set(),   # Immutable
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def transition(
        self,
        task: Task,
        new_state: TaskState,
        notes: Optional[str] = None
    ) -> Task:
        """
        Transition task to new state if valid.
        
        Args:
            task: Task to transition
            new_state: Target state
            notes: Optional notes
            
        Returns:
            Updated task
            
        Raises:
            ImmutableTaskError: If task is immutable
            InvalidStateTransitionError: If transition invalid
        """
        # Check if task is immutable
        if not task.is_mutable:
            raise ImmutableTaskError(
                f"Task {task.task_id} is {task.state.value} and cannot be modified"
            )
        
        # Check if transition is valid
        if new_state not in self.TRANSITIONS.get(task.state, set()):
            raise InvalidStateTransitionError(
                f"Cannot transition from {task.state.value} to {new_state.value}"
            )
        
        # Perform transition
        task.state = new_state
        task.last_modified_at = datetime.utcnow()
        
        if notes:
            task.notes = f"{task.notes or ''}\n{notes}".strip()
        
        self.db.commit()
        self.db.refresh(task)
        
        return task
    
    def can_transition(self, task: Task, new_state: TaskState) -> bool:
        """Check if transition is valid without raising exception."""
        if not task.is_mutable:
            return False
        return new_state in self.TRANSITIONS.get(task.state, set())
```

### 7.5 Task Manager (SINGLE MUTATION AUTHORITY)

**`backend/app/services/task_manager.py`:**

```python
"""
Task Manager - SINGLE MUTATION AUTHORITY.

ALL task modifications MUST go through this service.
No other service should modify Task objects directly.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import Task, TaskState, TaskSource
from app.services.parser import TaskParser
from app.services.state_machine import StateMachine
from app.services.conflict_detector import ConflictDetector
from app.services.notion_client import NotionClient
from app.utils.redis_client import RedisClient
from app.utils.time_utils import to_utc, now_utc
from app.core.exceptions import ImmutableTaskError


class TaskManager:
    """
    Single authority for all task mutations.
    
    Architecture principle: All writes flow through here.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.parser = TaskParser()
        self.state_machine = StateMachine(db)
        self.conflict_detector = ConflictDetector(db)
        self.notion = NotionClient()
        self.redis = RedisClient()
    
    def create_task(
        self,
        title: str,
        start: datetime,
        end: datetime,
        category: Optional[str] = None,
        state: TaskState = TaskState.PLANNED,
        source: TaskSource = TaskSource.MANUAL,
        confidence_score: Optional[float] = None,
        force_conflicts: bool = False
    ) -> tuple[Optional[Task], list[Task]]:
        """
        Create a new task.
        
        Args:
            title: Task title
            start: Start time (UTC)
            end: End time (UTC)
            category: Optional category
            state: Initial state (default PLANNED)
            source: How task was created
            confidence_score: Parser confidence
            force_conflicts: Ignore conflicts if True
            
        Returns:
            (created_task, conflicts)
            If conflicts exist and not forced: (None, conflicts)
        """
        # Detect conflicts
        conflicts = self.conflict_detector.detect(start, end)
        
        if conflicts and not force_conflicts:
            return None, conflicts
        
        # Calculate duration
        duration_minutes = int((end - start).total_seconds() / 60)
        
        # Create task (transaction safety)
        with self.db.begin():
            task = Task(
                title=title,
                planned_start_utc=start,
                planned_end_utc=end,
                planned_duration_minutes=duration_minutes,
                category=category,
                state=state,
                source=source,
                confidence_score=confidence_score,
                created_at=now_utc(),
                last_modified_at=now_utc()
            )
            
            self.db.add(task)
            self.db.flush()  # Get task_id
        
        # Sync to Notion (async, non-blocking)
        try:
            self.notion.sync_task(task)
        except Exception as e:
            # Don't fail task creation if Notion fails
            pass
        
        # Cache for undo
        self.redis.cache_undo_action("create_task", task.task_id, {
            "task_id": task.task_id,
            "title": task.title
        })
        
        return task, []
    
    def start_task(self, task_id: str) -> Task:
        """
        Start a task (transition PLANNED → EXECUTING).
        
        Args:
            task_id: Task to start
            
        Returns:
            Updated task
        """
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        
        with self.db.begin():
            task = self.state_machine.transition(task, TaskState.EXECUTING)
        
        # Sync to Notion
        try:
            self.notion.sync_task(task)
        except Exception:
            pass
        
        return task
    
    def complete_task(
        self,
        task_id: str,
        executed_start: datetime,
        executed_end: datetime
    ) -> Task:
        """
        Mark task as completed.
        
        Args:
            task_id: Task to complete
            executed_start: Actual start time (UTC)
            executed_end: Actual end time (UTC)
            
        Returns:
            Updated task
        """
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        
        executed_duration = int((executed_end - executed_start).total_seconds() / 60)
        
        with self.db.begin():
            task.executed_start_utc = executed_start
            task.executed_end_utc = executed_end
            task.executed_duration_minutes = executed_duration
            task = self.state_machine.transition(task, TaskState.EXECUTED)
        
        # Sync to Notion
        try:
            self.notion.sync_task(task)
        except Exception:
            pass
        
        return task
    
    def skip_task(self, task_id: str, reason: Optional[str] = None) -> Task:
        """
        Mark task as skipped.
        
        Args:
            task_id: Task to skip
            reason: Optional reason
            
        Returns:
            Updated task
        """
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        
        with self.db.begin():
            task = self.state_machine.transition(task, TaskState.SKIPPED, notes=reason)
        
        # Sync to Notion
        try:
            self.notion.sync_task(task)
        except Exception:
            pass
        
        return task
    
    def delete_task(self, task_id: str) -> Task:
        """
        Delete a task (soft delete - mark as DELETED).
        
        Args:
            task_id: Task to delete
            
        Returns:
            Updated task
        """
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        
        if not task.is_mutable:
            raise ImmutableTaskError("Cannot delete immutable task")
        
        with self.db.begin():
            task = self.state_machine.transition(task, TaskState.DELETED)
        
        # Remove from Notion
        try:
            if task.notion_page_id:
                self.notion.archive_page(task.notion_page_id)
        except Exception:
            pass
        
        # Cache for undo
        self.redis.cache_undo_action("delete_task", task.task_id, {
            "task_id": task.task_id,
            "title": task.title,
            "previous_state": task.state.value
        })
        
        return task
    
    def reschedule_task(
        self,
        task_id: str,
        new_start: datetime,
        new_end: Optional[datetime] = None
    ) -> tuple[Task, list[Task]]:
        """
        Reschedule a task (preserves TaskID).
        
        Args:
            task_id: Task to reschedule
            new_start: New start time (UTC)
            new_end: New end time (UTC), or None to preserve duration
            
        Returns:
            (updated_task, conflicts)
        """
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        
        if not task.is_mutable:
            raise ImmutableTaskError("Cannot reschedule immutable task")
        
        # Calculate new end if not provided
        if new_end is None:
            duration = task.planned_end_utc - task.planned_start_utc
            new_end = new_start + duration
        
        # Check for conflicts (excluding current task)
        conflicts = self.conflict_detector.detect(
            new_start,
            new_end,
            exclude_task_id=task.task_id
        )
        
        # Update task
        with self.db.begin():
            task.planned_start_utc = new_start
            task.planned_end_utc = new_end
            task.planned_duration_minutes = int((new_end - new_start).total_seconds() / 60)
            task.last_modified_at = now_utc()
        
        # Sync to Notion
        try:
            self.notion.sync_task(task)
        except Exception:
            pass
        
        return task, conflicts
```

### 7.6 Conflict Detector

**`backend/app/services/conflict_detector.py`:**

```python
"""Time conflict detection."""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import Task, TaskState


class ConflictDetector:
    """Detect overlapping tasks."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def detect(
        self,
        start: datetime,
        end: datetime,
        exclude_task_id: Optional[str] = None
    ) -> list[Task]:
        """
        Detect tasks that overlap with given time range.
        
        Overlap logic:
            Task A: [start_A, end_A)
            Task B: [start_B, end_B)
            Overlap if: start_A < end_B AND start_B < end_A
        
        Args:
            start: Range start (UTC)
            end: Range end (UTC)
            exclude_task_id: Optional task to exclude from check
            
        Returns:
            List of conflicting tasks
        """
        query = self.db.query(Task).filter(
            Task.state.in_([TaskState.PLANNED, TaskState.EXECUTING, TaskState.EXECUTED]),
            Task.planned_start_utc < end,
            Task.planned_end_utc > start
        )
        
        if exclude_task_id:
            query = query.filter(Task.task_id != exclude_task_id)
        
        return query.all()
```

### 7.7 Stopwatch Manager

**`backend/app/services/stopwatch_manager.py`:**

```python
"""Stopwatch lifecycle management with Redis."""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import StopwatchSession, Task, TaskState
from app.services.task_manager import TaskManager
from app.utils.redis_client import RedisClient
from app.utils.time_utils import now_utc
from app.core.exceptions import (
    StopwatchAlreadyRunningError,
    NoActiveStopwatchError
)


class StopwatchManager:
    """Manage stopwatch sessions with Redis persistence."""
    
    def __init__(self, db: Session):
        self.db = db
        self.redis = RedisClient()
        self.task_manager = TaskManager(db)
    
    def start(
        self,
        task_id: Optional[str] = None,
        title: Optional[str] = None,
        user_id: str = "user_primary"
    ) -> tuple[StopwatchSession, Task]:
        """
        Start stopwatch.
        
        Args:
            task_id: Existing task to time (optional)
            title: Title for new task if task_id is None
            user_id: User ID (single user in v1)
            
        Returns:
            (session, task)
            
        Raises:
            StopwatchAlreadyRunningError: If stopwatch already active
        """
        # Check for active stopwatch
        active = self.redis.get_active_stopwatch(user_id)
        if active:
            raise StopwatchAlreadyRunningError(
                f"Stopwatch already running for task {active['task_id']}"
            )
        
        # Get or create task
        if task_id:
            task = self.db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                raise ValueError("Task not found")
            
            # Transition to EXECUTING
            task = self.task_manager.start_task(task_id)
        else:
            # Create new unplanned task
            if not title:
                raise ValueError("Title required for unplanned task")
            
            # Create task with current time as start
            now = now_utc()
            task, _ = self.task_manager.create_task(
                title=title,
                start=now,
                end=now + timedelta(hours=1),  # Default 1h duration
                state=TaskState.EXECUTING
            )
        
        # Create stopwatch session (transaction safety)
        with self.db.begin():
            session = StopwatchSession(
                task_id=task.task_id,
                start_time_utc=now_utc(),
                auto_closed=False
            )
            self.db.add(session)
            self.db.flush()
        
        # Store in Redis
        self.redis.set_active_stopwatch(
            user_id=user_id,
            session_id=session.session_id,
            task_id=task.task_id,
            title=task.title,
            start_time=session.start_time_utc.isoformat()
        )
        
        return session, task
    
    def stop(
        self,
        user_id: str = "user_primary"
    ) -> tuple[StopwatchSession, Task]:
        """
        Stop active stopwatch.
        
        Args:
            user_id: User ID
            
        Returns:
            (session, task)
            
        Raises:
            NoActiveStopwatchError: If no stopwatch running
        """
        # Get active stopwatch from Redis
        active = self.redis.get_active_stopwatch(user_id)
        if not active:
            raise NoActiveStopwatchError("No active stopwatch")
        
        # Get session from DB
        session = self.db.query(StopwatchSession).filter(
            StopwatchSession.session_id == active['session_id']
        ).first()
        
        if not session:
            # Redis/DB desync - clear Redis
            self.redis.clear_active_stopwatch(user_id)
            raise NoActiveStopwatchError("Stopwatch session not found")
        
        # Get task
        task = self.db.query(Task).filter(Task.task_id == session.task_id).first()
        if not task:
            raise ValueError("Task not found")
        
        # Stop stopwatch (transaction safety)
        stop_time = now_utc()
        
        with self.db.begin():
            # Close session
            session.end_time_utc = stop_time
            
            # Mark task as completed
            task = self.task_manager.complete_task(
                task_id=task.task_id,
                executed_start=session.start_time_utc,
                executed_end=stop_time
            )
        
        # Clear Redis
        self.redis.clear_active_stopwatch(user_id)
        
        return session, task
    
    def get_status(
        self,
        user_id: str = "user_primary"
    ) -> Optional[dict]:
        """
        Get current stopwatch status.
        
        Args:
            user_id: User ID
            
        Returns:
            Status dict or None if no active stopwatch
        """
        active = self.redis.get_active_stopwatch(user_id)
        if not active:
            return None
        
        # Calculate elapsed time
        start_time = datetime.fromisoformat(active['start_time'])
        elapsed = now_utc() - start_time
        elapsed_minutes = int(elapsed.total_seconds() / 60)
        
        return {
            "active": True,
            "session_id": active['session_id'],
            "task_id": active['task_id'],
            "task_title": active['title'],
            "start_time": start_time,
            "elapsed_minutes": elapsed_minutes
        }
```

---

## 8. API Endpoints

### 8.1 Dependencies

**`backend/app/api/deps.py`:**

```python
"""FastAPI dependency injection."""
from typing import Generator
from app.db.session import SessionLocal


def get_db() -> Generator:
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 8.2 Parse Endpoint

**`backend/app/api/v1/endpoints/parse.py`:**

```python
"""Parse endpoint."""
from fastapi import APIRouter, HTTPException
import logging

from app.schemas.task import TaskParseRequest, TaskParseResponse
from app.services.parser import TaskParser

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/parse", response_model=TaskParseResponse)
async def parse_input(request: TaskParseRequest) -> TaskParseResponse:
    """
    Parse natural language text into structured task data.
    
    This is stateless - nothing is persisted.
    OpenClaw calls this to understand intent,
    then calls /tasks/create to commit.
    
    Examples:
        - "Gym at 9am"
        - "Study AI 2-3 hours tonight"
        - "Meeting tomorrow at 2pm"
    """
    try:
        parser = TaskParser()
        result = parser.parse(request.text)
        
        logger.info(
            f"Parsed '{request.text}' -> {result.title} "
            f"(confidence: {result.confidence:.2f})"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Parse error: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "parse_failed",
                "message": str(e),
                "confidence": 0.0
            }
        )
```

### 8.3 Tasks Endpoint (Simplified)

**`backend/app/api/v1/endpoints/tasks.py`:**

```python
"""Task management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.api.deps import get_db
from app.schemas.task import (
    TaskCreateRequest,
    TaskCreateResponse,
    TaskRescheduleRequest,
    TaskRescheduleResponse,
    TaskDeleteRequest,
    TaskDeleteResponse,
    ConflictInfo,
)
from app.services.task_manager import TaskManager
from app.core.exceptions import ImmutableTaskError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/tasks/create", response_model=TaskCreateResponse)
async def create_task(
    request: TaskCreateRequest,
    db: Session = Depends(get_db)
) -> TaskCreateResponse:
    """
    Create a new task.
    
    If conflicts detected and force=False, returns conflicts without creating.
    If force=True or no conflicts, creates task and syncs to Notion.
    """
    try:
        manager = TaskManager(db)
        
        task, conflicts = manager.create_task(
            title=request.title,
            start=request.start,
            end=request.end,
            category=request.category,
            state=request.state,
            source=request.source,
            confidence_score=request.confidence_score,
            force_conflicts=request.force
        )
        
        if task is None:
            # Conflicts exist, not forced
            conflict_info = [
                ConflictInfo(
                    task_id=c.task_id,
                    title=c.title,
                    start=c.planned_start_utc,
                    end=c.planned_end_utc,
                    state=c.state
                )
                for c in conflicts
            ]
            
            return TaskCreateResponse(
                task_id=None,
                created=False,
                conflicts=conflict_info,
                can_proceed=True
            )
        
        return TaskCreateResponse(
            task_id=task.task_id,
            created=True,
            conflicts=[],
            can_proceed=True
        )
        
    except Exception as e:
        logger.error(f"Task creation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/reschedule", response_model=TaskRescheduleResponse)
async def reschedule_task(
    request: TaskRescheduleRequest,
    db: Session = Depends(get_db)
) -> TaskRescheduleResponse:
    """Reschedule task (preserves TaskID)."""
    try:
        manager = TaskManager(db)
        
        task, conflicts = manager.reschedule_task(
            task_id=request.task_id,
            new_start=request.new_start,
            new_end=request.new_end
        )
        
        conflict_info = [
            ConflictInfo(
                task_id=c.task_id,
                title=c.title,
                start=c.planned_start_utc,
                end=c.planned_end_utc,
                state=c.state
            )
            for c in conflicts
        ]
        
        return TaskRescheduleResponse(
            task_id=task.task_id,
            rescheduled=True,
            new_start=task.planned_start_utc,
            new_end=task.planned_end_utc,
            conflicts=conflict_info
        )
        
    except ImmutableTaskError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Reschedule error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/delete", response_model=TaskDeleteResponse)
async def delete_task(
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
        raise HTTPException(status_code=500, detail=str(e))
```

### 8.4 Stopwatch Endpoint

**`backend/app/api/v1/endpoints/stopwatch.py`:**

```python
"""Stopwatch endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.api.deps import get_db
from app.schemas.stopwatch import (
    StopwatchStartRequest,
    StopwatchStartResponse,
    StopwatchStopResponse,
    StopwatchStatusResponse,
)
from app.services.stopwatch_manager import StopwatchManager
from app.core.exceptions import (
    StopwatchAlreadyRunningError,
    NoActiveStopwatchError
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stopwatch/start", response_model=StopwatchStartResponse)
async def start_stopwatch(
    request: StopwatchStartRequest,
    db: Session = Depends(get_db)
) -> StopwatchStartResponse:
    """Start stopwatch."""
    try:
        manager = StopwatchManager(db)
        
        session, task = manager.start(
            task_id=request.task_id,
            title=request.title
        )
        
        return StopwatchStartResponse(
            session_id=session.session_id,
            task_id=task.task_id,
            start_time=session.start_time_utc
        )
        
    except StopwatchAlreadyRunningError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stopwatch start error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stopwatch/stop", response_model=StopwatchStopResponse)
async def stop_stopwatch(
    db: Session = Depends(get_db)
) -> StopwatchStopResponse:
    """Stop active stopwatch."""
    try:
        manager = StopwatchManager(db)
        
        session, task = manager.stop()
        
        return StopwatchStopResponse(
            task_id=task.task_id,
            session_id=session.session_id,
            duration_minutes=task.executed_duration_minutes,
            planned_duration_minutes=task.planned_duration_minutes,
            delta_minutes=task.duration_delta_minutes,
            executed_at=task.executed_end_utc
        )
        
    except NoActiveStopwatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stopwatch stop error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stopwatch/status", response_model=StopwatchStatusResponse)
async def stopwatch_status(
    db: Session = Depends(get_db)
) -> StopwatchStatusResponse:
    """Get stopwatch status."""
    try:
        manager = StopwatchManager(db)
        status = manager.get_status()
        
        if status:
            return StopwatchStatusResponse(**status)
        else:
            return StopwatchStatusResponse(active=False)
            
    except Exception as e:
        logger.error(f"Stopwatch status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 9. Redis Patterns

**`backend/app/utils/redis_client.py`:**

```python
"""Redis client with Lyra-specific patterns."""
import json
import redis
from typing import Optional, Dict, Any
from datetime import timedelta
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client with application-specific patterns."""
    
    def __init__(self):
        self.client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
    
    # Stopwatch patterns
    def set_active_stopwatch(
        self,
        user_id: str,
        session_id: str,
        task_id: str,
        title: str,
        start_time: str
    ):
        """Store active stopwatch session (no TTL - persists until stopped)."""
        key = f"stopwatch:active:{user_id}"
        data = {
            "session_id": session_id,
            "task_id": task_id,
            "title": title,
            "start_time": start_time
        }
        self.client.set(key, json.dumps(data))
        logger.info(f"Stopwatch started: {task_id}")
    
    def get_active_stopwatch(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get active stopwatch session."""
        key = f"stopwatch:active:{user_id}"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def clear_active_stopwatch(self, user_id: str):
        """Clear active stopwatch."""
        key = f"stopwatch:active:{user_id}"
        self.client.delete(key)
        logger.info(f"Stopwatch cleared for user {user_id}")
    
    # Undo pattern (30 second TTL)
    def cache_undo_action(
        self,
        action_type: str,
        entity_id: str,
        data: Dict[str, Any],
        ttl_seconds: int = 30
    ):
        """Cache action for undo."""
        key = f"undo:{entity_id}"
        undo_data = {
            "action": action_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.client.setex(key, ttl_seconds, json.dumps(undo_data))
    
    def get_undo_data(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get undo data if within TTL."""
        key = f"undo:{entity_id}"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def clear_undo_data(self, entity_id: str):
        """Clear undo data."""
        key = f"undo:{entity_id}"
        self.client.delete(key)
    
    # Idempotency pattern (Telegram webhooks)
    def check_telegram_update(self, update_id: int) -> bool:
        """
        Check if Telegram update already processed.
        
        Returns:
            True if duplicate (already processed)
            False if new
        """
        key = f"telegram:update:{update_id}"
        
        if self.client.exists(key):
            return True  # Duplicate
        
        # Mark as processed (60 second TTL)
        self.client.setex(key, 60, "1")
        return False  # New
    
    # Notion sync queue
    def queue_notion_sync(self, task_id: str, task_data: Dict[str, Any]):
        """Queue task for Notion sync (if API down)."""
        key = "notion:sync_queue"
        self.client.rpush(key, json.dumps({"task_id": task_id, "data": task_data}))
    
    def get_notion_sync_queue(self, limit: int = 10) -> list:
        """Get pending Notion sync items."""
        key = "notion:sync_queue"
        items = self.client.lrange(key, 0, limit - 1)
        return [json.loads(item) for item in items]
    
    def remove_from_notion_queue(self, count: int):
        """Remove synced items from queue."""
        key = "notion:sync_queue"
        self.client.ltrim(key, count, -1)
```

---

## 10. External Integrations

### 10.1 Notion Client

**`backend/app/services/notion_client.py`:**

```python
"""Notion API client for calendar sync."""
import logging
from typing import Optional, Dict, Any

from notion_client import Client
from notion_client.errors import APIResponseError

from app.config import settings
from app.db.models import Task, TaskState
from app.utils.retry import retry_with_backoff
from app.utils.time_utils import to_local

logger = logging.getLogger(__name__)


class NotionClient:
    """Client for syncing tasks to Notion calendar database."""
    
    def __init__(self):
        self.client = Client(auth=settings.NOTION_API_KEY)
        self.database_id = settings.NOTION_DATABASE_ID
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def sync_task(self, task: Task) -> Optional[str]:
        """
        Sync task to Notion database.
        
        Creates page if notion_page_id is None, updates if exists.
        
        Returns:
            Notion page ID
        """
        try:
            properties = self._build_properties(task)
            
            if task.notion_page_id:
                # Update existing page
                response = self.client.pages.update(
                    page_id=task.notion_page_id,
                    properties=properties
                )
                logger.info(f"Updated Notion page for task {task.task_id}")
            else:
                # Create new page
                response = self.client.pages.create(
                    parent={"database_id": self.database_id},
                    properties=properties
                )
                task.notion_page_id = response["id"]
                logger.info(f"Created Notion page for task {task.task_id}")
            
            return response["id"]
            
        except APIResponseError as e:
            logger.error(f"Notion API error: {e}", exc_info=True)
            raise
    
    def _build_properties(self, task: Task) -> Dict[str, Any]:
        """Build Notion page properties from task."""
        # Use executed time if available, else planned
        start = task.executed_start_utc or task.planned_start_utc
        end = task.executed_end_utc or task.planned_end_utc
        
        # Convert UTC to local time for display
        start_local = to_local(start)
        end_local = to_local(end)
        
        # State icon
        state_icons = {
            TaskState.PLANNED: "☐",
            TaskState.EXECUTING: "▶️",
            TaskState.EXECUTED: "✓",
            TaskState.SKIPPED: "⊘",
            TaskState.DELETED: "🗑️"
        }
        icon = state_icons.get(task.state, "")
        
        properties = {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": f"{icon} {task.title}"
                        }
                    }
                ]
            },
            "Start": {
                "date": {
                    "start": start_local.isoformat(),
                    "end": end_local.isoformat()
                }
            },
            "State": {
                "status": {
                    "name": task.state.value
                }
            },
        }
        
        # Optional fields
        if task.category:
            properties["Category"] = {
                "multi_select": [{"name": task.category}]
            }
        
        if task.notes:
            properties["Notes"] = {
                "rich_text": [
                    {
                        "text": {"content": task.notes[:2000]}
                    }
                ]
            }
        
        # Duration info (THE CORE VALUE)
        if task.executed_duration_minutes:
            duration_text = f"Planned: {task.planned_duration_minutes}min, "
            duration_text += f"Actual: {task.executed_duration_minutes}min"
            if task.duration_delta_minutes:
                duration_text += f" (Δ {task.duration_delta_minutes:+d}min)"
            
            properties["Duration"] = {
                "rich_text": [
                    {"text": {"content": duration_text}}
                ]
            }
        
        return properties
    
    def archive_page(self, page_id: str):
        """Archive a Notion page (for deleted tasks)."""
        try:
            self.client.pages.update(
                page_id=page_id,
                archived=True
            )
            logger.info(f"Archived Notion page {page_id}")
        except APIResponseError as e:
            logger.error(f"Failed to archive page: {e}")
```

---

## 11. Workers & Scheduler

**`backend/app/workers/scheduler.py`:**

```python
"""APScheduler setup for background jobs."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

from app.workers.jobs.reminders import check_upcoming_tasks
from app.workers.jobs.notion_sync import retry_failed_syncs

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def start_scheduler():
    """Start background scheduler."""
    # Reminders (check every 1 minute)
    scheduler.add_job(
        check_upcoming_tasks,
        trigger=IntervalTrigger(minutes=1),
        id="reminders",
        name="Check upcoming task reminders",
        replace_existing=True
    )
    
    # Notion sync retry (check every 5 minutes)
    scheduler.add_job(
        retry_failed_syncs,
        trigger=IntervalTrigger(minutes=5),
        id="notion_sync",
        name="Retry failed Notion syncs",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("APScheduler started")


def shutdown_scheduler():
    """Shutdown scheduler gracefully."""
    scheduler.shutdown()
    logger.info("APScheduler shutdown")
```

**`backend/app/workers/jobs/reminders.py`:**

```python
"""Pre-task reminder job."""
from datetime import timedelta
import logging

from app.db.session import SessionLocal
from app.db.models import Task, TaskState
from app.services.telegram_notifier import TelegramNotifier
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)


def check_upcoming_tasks():
    """Check for tasks starting in 15 minutes."""
    db = SessionLocal()
    try:
        now = now_utc()
        reminder_time = now + timedelta(minutes=15)
        
        # Query tasks starting in next 15 minutes
        tasks = db.query(Task).filter(
            Task.state == TaskState.PLANNED,
            Task.planned_start_utc >= now,
            Task.planned_start_utc <= reminder_time
        ).all()
        
        notifier = TelegramNotifier()
        for task in tasks:
            try:
                notifier.send_reminder(task)
                logger.info(f"Sent reminder for task {task.task_id}")
            except Exception as e:
                logger.error(f"Failed to send reminder: {e}")
                
    finally:
        db.close()
```

---

## 12. OpenClaw Configuration

**`openclaw/config/agent.yml`:**

```yaml
agent:
  name: "Lyra"
  model: "claude-sonnet-4"
  temperature: 0.7
  
  system_prompt: |
    You are Lyra, a personal time management assistant.
    
    Your role is to help the user plan and track their time with minimal friction.
    
    Core principles:
    1. User has final authority on all decisions
    2. Executed tasks are immutable historical records  
    3. Always disambiguate before taking action
    4. Present conflicts clearly with options
    5. Be concise and natural in conversation
    
    You have access to tools that interact with the Secretary Core (FastAPI backend).
    The backend handles all task state, validation, and persistence.
    Your job is to understand intent, orchestrate workflows, and format responses.

memory:
  type: conversation
  retention_days: 7
  max_messages: 100
  
telegram:
  webhook_url: "https://your-openclaw-instance.com/telegram/webhook"
  bot_token: ${TELEGRAM_BOT_TOKEN}
  
external_apis:
  whisper:
    endpoint: "https://api.openai.com/v1/audio/transcriptions"
    api_key: ${OPENAI_API_KEY}
    model: "whisper-1"

skills:
  - name: parse_input
    type: http
    endpoint: "http://backend:8000/v1/parse"
    method: POST
    
  - name: create_task
    type: http
    endpoint: "http://backend:8000/v1/tasks/create"
    method: POST
    
  - name: start_stopwatch
    type: http
    endpoint: "http://backend:8000/v1/stopwatch/start"
    method: POST
    
  - name: stop_stopwatch
    type: http
    endpoint: "http://backend:8000/v1/stopwatch/stop"
    method: POST
```

---

## 13. Architectural Principles

### 13.1 The 7 Commandments

1. **Single Mutation Authority** - Only TaskManager writes to database
2. **Thin Controllers** - API endpoints orchestrate, services execute
3. **Unidirectional Flow** - Data flows one direction: User → OpenClaw → FastAPI → DB → Notion
4. **Sync Over Async** - Use sync functions (SQLAlchemy/Redis are blocking)
5. **Core Independence** - System works without Notion/Telegram/OpenClaw
6. **No God Services** - Services stay <400 lines, single responsibility
7. **UTC Everywhere** - Store UTC, display local time

### 13.2 What NOT to Do

❌ **Don't mix cognition with execution**
```python
# BAD - Logic in API route
@router.post("/tasks")
def create_task(request):
    parsed = parser.parse(request.text)  # Logic here
    task = Task(...)
    db.add(task)  # State management here
    notion.sync(task)  # Integration here
```

✅ **DO delegate to services**
```python
# GOOD - Thin controller
@router.post("/tasks")
def create_task(request):
    task = task_manager.create_task(request.text)
    return task
```

❌ **Don't let multiple services modify tasks**
```python
# BAD - Hidden mutations
parser.modify_task(task)
stopwatch.modify_task(task)
state_machine.modify_task(task)
```

✅ **DO use single authority**
```python
# GOOD - All writes through manager
task_manager.create_task(...)
task_manager.start_task(...)
task_manager.complete_task(...)
```

---

## 14. Critical Requirements

### 14.1 Timezone Handling (NON-NEGOTIABLE)

**Storage Rule:** All datetime fields in UTC (no timezone info)

**Display Rule:** Convert to user's local time (Africa/Cairo)

**Implementation:**
```python
# When parsing user input
from app.utils.time_utils import to_utc

local_time = parser.parse_time("9am tomorrow")
utc_time = to_utc(local_time)
task.planned_start_utc = utc_time  # Store UTC

# When displaying to user
from app.utils.time_utils import to_local

utc_time = task.planned_start_utc
local_time = to_local(utc_time)  # Display local
```

### 14.2 Idempotency Keys (REQUIRED)

**Problem:** Telegram sends duplicate webhooks

**Solution:** Redis-based deduplication

```python
from app.utils.redis_client import RedisClient

redis = RedisClient()

# In Telegram webhook handler
if redis.check_telegram_update(update.update_id):
    return {"status": "duplicate, ignored"}

# Process normally (already marked as processed)
```

### 14.3 Transaction Safety (CRITICAL)

**Rule:** All task mutations MUST be atomic

```python
# Use context manager for transactions
with db.begin():
    # All database writes here
    session.end_time_utc = stop_time
    task.executed_duration_minutes = duration
    task.state = TaskState.EXECUTED
    # Either all commit or all rollback
```

### 14.4 Failure Recovery

**On FastAPI Startup:**
```python
def recover_orphaned_stopwatches():
    """Recover stopwatches if FastAPI crashed."""
    redis = RedisClient()
    keys = redis.client.keys("stopwatch:active:*")
    
    for key in keys:
        data = redis.client.get(key)
        logger.warning(f"Recovered active stopwatch: {data}")
        # DO NOT auto-close
        # User will stop manually
```

---

## 15. Testing Strategy

### 15.1 Unit Tests (REQUIRED)

**`backend/tests/conftest.py`:**
```python
"""Pytest configuration."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.main import app
from app.api.deps import get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="function")
def db():
    """Fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
```

**`backend/tests/unit/test_parser.py`:**
```python
"""Test natural language parsing."""
import pytest
from datetime import datetime

from app.services.parser import TaskParser


def test_simple_task():
    """Test 'task at time' pattern."""
    parser = TaskParser()
    result = parser.parse("Gym at 9am")
    
    assert result.title == "Gym"
    assert result.start.hour == 9
    assert result.confidence > 0.7


def test_duration_range_uses_max():
    """Test '2-3 hours' uses maximum."""
    parser = TaskParser()
    result = parser.parse("Study 2-3 hours")
    
    assert result.duration_minutes == 180  # Max of range
```

**`backend/tests/unit/test_state_machine.py`:**
```python
"""Test state machine transitions."""
import pytest

from app.db.models import Task, TaskState
from app.services.state_machine import StateMachine
from app.core.exceptions import (
    ImmutableTaskError,
    InvalidStateTransitionError
)


def test_planned_to_executing(db):
    """Test PLANNED → EXECUTING transition."""
    task = Task(
        title="Test",
        state=TaskState.PLANNED,
        planned_start_utc=datetime.utcnow(),
        planned_end_utc=datetime.utcnow(),
        planned_duration_minutes=60
    )
    db.add(task)
    db.commit()
    
    sm = StateMachine(db)
    task = sm.transition(task, TaskState.EXECUTING)
    
    assert task.state == TaskState.EXECUTING


def test_executed_immutable(db):
    """Test EXECUTED tasks cannot be modified."""
    task = Task(
        title="Test",
        state=TaskState.EXECUTED,
        planned_start_utc=datetime.utcnow(),
        planned_end_utc=datetime.utcnow(),
        planned_duration_minutes=60
    )
    db.add(task)
    db.commit()
    
    sm = StateMachine(db)
    
    with pytest.raises(ImmutableTaskError):
        sm.transition(task, TaskState.PLANNED)
```

---

## 16. Deployment

**`docker-compose.yml`:**
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: lyra-backend
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=sqlite:///data/lyra.db
      - REDIS_URL=redis://redis:6379/0
      - NOTION_API_KEY=${NOTION_API_KEY}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - USER_TIMEZONE=Africa/Cairo
    volumes:
      - ./data:/app/data
    depends_on:
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  openclaw:
    build: ./openclaw
    container_name: lyra-openclaw
    ports:
      - "8080:8080"
    environment:
      - BACKEND_URL=http://backend:8000
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - backend

  redis:
    image: redis:7.2-alpine
    container_name: lyra-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  redis_data:
```

---

## 17. Implementation Timeline

### Week 1: Core Backend

**Day 1-2: Foundation**
- Project structure
- Database models
- Alembic migrations
- Config setup

**Day 3-4: Services**
- Parser
- State machine
- Task manager
- Conflict detector

**Day 5-6: API**
- Parse endpoint
- Task endpoints
- Health checks
- Error handling

**Day 7: Stopwatch**
- Stopwatch manager
- Redis integration
- Session persistence

### Week 2: Integration & Polish

**Day 8-9: External Services**
- Notion client
- Telegram notifier
- APScheduler jobs

**Day 10-11: OpenClaw**
- Agent config
- Skills setup
- Telegram webhook

**Day 12-13: Testing**
- Unit tests
- Integration tests
- Manual testing

**Day 14: Deployment**
- Docker setup
- Production config
- Documentation

---

## 18. Vibe-Code Prompts

### Prompt 1: Database Models
```
Generate complete SQLAlchemy models for Lyra Secretary:

Tables:
1. Task (task_id PK, title, category, planned_start_utc, planned_end_utc, 
   planned_duration_minutes, executed_start_utc, executed_end_utc, 
   executed_duration_minutes, state ENUM, source ENUM, confidence_score, 
   notes, created_at, last_modified_at, notion_page_id)

2. StopwatchSession (session_id PK, task_id FK, start_time_utc, 
   end_time_utc, auto_closed)

3. CategoryMapping (keyword PK, category, confidence, last_used)

Requirements:
- Python 3.11 type hints (Mapped[])
- Indexes on: task.state, task.planned_start_utc, task.category
- Check constraints for state/source enums
- Helper properties: is_mutable, duration_delta_minutes
- All PKs are UUIDv4 strings
- Relationships with cascade delete

File: backend/app/db/models.py
```

### Prompt 2: Task Parser
```
Generate natural language task parser:

Class: TaskParser
Methods:
- parse(text: str) -> TaskParseResponse
- _extract_title(text)
- _extract_time(text)
- _extract_duration(text)
- _infer_category(title) - lookup in CategoryMapping table
- _calculate_confidence(...)

Libraries:
- dateparser for time parsing
- regex for duration extraction

Rules:
- "X-Y hours" → use max (Y)
- Times in past (same day) → adjust to tomorrow
- Missing duration → add "duration_missing" to ambiguities
- Convert to UTC using to_utc() from time_utils

User timezone: Africa/Cairo

File: backend/app/services/parser.py
```

### Prompt 3: Task Manager (Single Mutation Authority)
```
Generate TaskManager service (ONLY class that modifies tasks):

Class: TaskManager(db: Session)

Methods:
- create_task(...) → (task, conflicts)
- start_task(task_id) → task
- complete_task(task_id, executed_start, executed_end) → task
- skip_task(task_id, reason) → task
- delete_task(task_id) → task
- reschedule_task(task_id, new_start, new_end) → (task, conflicts)

Each method:
1. Uses transaction safety (with db.begin())
2. Calls NotionClient.sync_task() after mutation
3. Caches undo data in Redis
4. Returns updated task

Dependencies:
- StateMAchine for transitions
- ConflictDetector for overlaps
- NotionClient for sync
- RedisClient for undo cache

File: backend/app/services/task_manager.py
```

---

**END OF SPECIFICATION**

This document is complete, implementation-ready, and focuses on the core value: adaptive scheduling through delta tracking.

**Ready to build.**
