"""Append-only deadline completion events.

Revision ID: 049
Revises: 048
Create Date: 2026-05-12

Adds a completion/submission trace layer for overdue deadline behavior.
These rows are not stopwatch execution traces and are not VT-17 eligible.
Multiple valid events per deadline are allowed; analytics must distinguish
event count from distinct completed deadlines.
"""
from alembic import op
import sqlalchemy as sa


revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("deadline", sa.Column("missed_at", sa.DateTime(), nullable=True))
    op.create_table(
        "deadline_completion_event",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column(
            "deadline_id",
            sa.String(36),
            sa.ForeignKey("deadline.deadline_id"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "task_id",
            sa.String(36),
            sa.ForeignKey("task.task_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("completion_source", sa.String(40), nullable=False),
        sa.Column("completed_at_utc", sa.DateTime(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(), nullable=False),
        sa.Column("due_at_utc_at_event", sa.DateTime(), nullable=False),
        sa.Column("completed_after_due", sa.Boolean(), nullable=False),
        sa.Column("delay_minutes", sa.Integer(), nullable=False),
        sa.Column("time_provenance", sa.String(40), nullable=False),
        sa.Column("voided_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "completion_source IN ("
            "'user_deadline_done', "
            "'moodle_submission', "
            "'moodle_backfill_submission', "
            "'task_retroactive_done'"
            ")",
            name="check_deadline_completion_source",
        ),
        sa.CheckConstraint(
            "time_provenance IN ("
            "'observed_user_action', "
            "'external_import', "
            "'external_import_sync_time', "
            "'user_reported_retroactive'"
            ")",
            name="check_deadline_completion_time_provenance",
        ),
    )
    op.create_index(
        "idx_deadline_completion_user_recorded",
        "deadline_completion_event",
        ["user_id", "recorded_at_utc"],
    )
    op.create_index(
        "idx_deadline_completion_deadline_completed",
        "deadline_completion_event",
        ["deadline_id", "completed_at_utc"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_deadline_completion_deadline_completed",
        table_name="deadline_completion_event",
    )
    op.drop_index(
        "idx_deadline_completion_user_recorded",
        table_name="deadline_completion_event",
    )
    op.drop_table("deadline_completion_event")
    op.drop_column("deadline", "missed_at")
