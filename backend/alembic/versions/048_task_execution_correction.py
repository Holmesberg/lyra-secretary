"""Append-only task execution correction.

Revision ID: 048
Revises: 047
Create Date: 2026-05-10

Adds a Layer D repair table for forgotten timer stops. The raw task and
stopwatch rows remain observed truth; this table carries retroactive
provenance and is explicitly ineligible for VT-17 training.
"""
from alembic import op
import sqlalchemy as sa


revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_execution_correction",
        sa.Column("correction_id", sa.String(36), primary_key=True),
        sa.Column(
            "task_id",
            sa.String(36),
            sa.ForeignKey("task.task_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="retroactive"),
        sa.Column("reason", sa.String(40), nullable=False, server_default="forgot_to_stop_timer"),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("original_executed_start_utc", sa.DateTime, nullable=False),
        sa.Column("original_executed_end_utc", sa.DateTime, nullable=False),
        sa.Column("original_executed_duration_minutes", sa.Integer, nullable=False),
        sa.Column("corrected_executed_end_utc", sa.DateTime, nullable=False),
        sa.Column("corrected_executed_duration_minutes", sa.Integer, nullable=False),
        sa.Column("observed_paused_minutes", sa.Float, nullable=False, server_default="0"),
        sa.Column("vt17_eligible", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "provenance = 'retroactive'",
            name="check_task_execution_correction_provenance",
        ),
        sa.CheckConstraint(
            "reason IN ('forgot_to_stop_timer', 'accidental_left_running')",
            name="check_task_execution_correction_reason",
        ),
        sa.CheckConstraint(
            "corrected_executed_duration_minutes > 0",
            name="check_task_execution_correction_duration_positive",
        ),
        sa.CheckConstraint(
            "vt17_eligible = false",
            name="check_task_execution_correction_vt17_ineligible",
        ),
    )
    op.create_index(
        "idx_task_execution_correction_task_created",
        "task_execution_correction",
        ["task_id", "created_at"],
    )
    op.create_index(
        "idx_task_execution_correction_user_created",
        "task_execution_correction",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_task_execution_correction_user_created",
        table_name="task_execution_correction",
    )
    op.drop_index(
        "idx_task_execution_correction_task_created",
        table_name="task_execution_correction",
    )
    op.drop_table("task_execution_correction")
