"""Loop 11 — deadline mechanism foundation + scope-bullet instruments.

Revision ID: 033
Revises: 032
Create Date: 2026-04-26

Lands the schema for the thesis-testable instrument per `docs/feedback_loops_closure_plan.md
§Loop 11` + `docs/deadline_mechanism_design.md` (Option B, locked 2026-04-25). Pre-registration
committed in MANIFESTO.md v1.12 (Rules 14, 15, 16 + Rule 12 amendment).

Adds three things:

1. New `deadline` table — first-class entity per `deadline_mechanism_design.md:132-145`.
   State enum extended per operator decision 2026-04-26 to mirror task lifecycle:
   `planned | active | completed | missed | skipped | voided`. Default state = 'planned'
   (deadlines start dormant; auto-transition to 'active' on first task bind).

2. New `task_deadline_outcome` table — preserves EXECUTED-task immutability
   (state_machine.py:29,61-64) by storing post-execution reconciliation outputs
   in a separate table rather than mutating the task row. Mirrors the
   `external_event_outcome` template (Alembic 027). Frozen-at-compute-time
   semantics → research-reproducible. Includes voided_at column for symmetry
   with task voiding (LYR-095 pattern).

3. Five new columns on `task`:
   - deadline_id (FK to deadline) — nullable, populated by parser Pass 1
   - deadline_match_confidence (Float) — 0.0-1.0 from binding source
   - deadline_match_source (String) — 'user_explicit' | 'parser_auto' | 'user_corrected'
   - scope_bullet_count_at_plan (Int) — auto-counted on PLANNED-state creation
   - scope_bullet_count_at_execute (Int) — re-sampled at complete_task time

Ordering invariant: `deadline` table created BEFORE the FK column on task is added.
Downgrade reverses: indexes → columns → tables.
"""
from alembic import op
import sqlalchemy as sa


revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. New table: deadline (first-class entity).
    op.create_table(
        "deadline",
        sa.Column("deadline_id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("user.user_id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("due_at_utc", sa.DateTime, nullable=False),
        sa.Column("category_hint", sa.String(100), nullable=True),
        # State enum: planned | active | completed | missed | skipped | voided.
        # Default 'planned' (not 'active') — see module docstring.
        sa.Column(
            "state",
            sa.String(20),
            nullable=False,
            server_default="planned",
        ),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("voided_at", sa.DateTime, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_deadline_user_state",
        "deadline",
        ["user_id", "state", "voided_at"],
    )

    # 2. New table: task_deadline_outcome (immutability-preserving).
    op.create_table(
        "task_deadline_outcome",
        sa.Column(
            "task_id",
            sa.String(36),
            sa.ForeignKey("task.task_id"),
            primary_key=True,
        ),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("computed_at", sa.DateTime, nullable=False),
        sa.Column("deadline_utc_at_compute", sa.DateTime, nullable=False),
        sa.Column("executed_end_utc_at_compute", sa.DateTime, nullable=False),
        sa.Column("deadline_met", sa.Boolean, nullable=False),
        # Signed: positive = overran (missed), negative = under (met early).
        sa.Column("delay_minutes", sa.Integer, nullable=False),
        # Symmetry with task voiding: if task voided post-EXECUTED (LYR-095),
        # outcome row is invalidated by setting voided_at, NOT deleted.
        sa.Column("voided_at", sa.DateTime, nullable=True),
    )
    op.create_index(
        "idx_tdo_user_computed",
        "task_deadline_outcome",
        ["user_id", "computed_at"],
    )

    # 3. New columns on task.
    op.add_column(
        "task",
        sa.Column(
            "deadline_id",
            sa.String(36),
            sa.ForeignKey("deadline.deadline_id"),
            nullable=True,
        ),
    )
    op.add_column(
        "task",
        sa.Column("deadline_match_confidence", sa.Float, nullable=True),
    )
    op.add_column(
        "task",
        sa.Column("deadline_match_source", sa.String(20), nullable=True),
    )
    op.add_column(
        "task",
        sa.Column("scope_bullet_count_at_plan", sa.Integer, nullable=True),
    )
    op.add_column(
        "task",
        sa.Column("scope_bullet_count_at_execute", sa.Integer, nullable=True),
    )
    op.create_index("idx_task_deadline_id", "task", ["deadline_id"])


def downgrade() -> None:
    # Reverse order: indexes → columns → tables.
    op.drop_index("idx_task_deadline_id", table_name="task")
    op.drop_column("task", "scope_bullet_count_at_execute")
    op.drop_column("task", "scope_bullet_count_at_plan")
    op.drop_column("task", "deadline_match_source")
    op.drop_column("task", "deadline_match_confidence")
    op.drop_column("task", "deadline_id")
    op.drop_index("idx_tdo_user_computed", table_name="task_deadline_outcome")
    op.drop_table("task_deadline_outcome")
    op.drop_index("idx_deadline_user_state", table_name="deadline")
    op.drop_table("deadline")
