"""Resume prediction log (W2 magic-for-alpha 2026-04-28).

Revision ID: 038
Revises: 037
Create Date: 2026-04-28

Adds the ResumePredictionLog table for W2 resume-prediction firings.
Mirrors PausePredictionLog with two additional fields specific to the
resume mechanism:
  - paused_for_minutes — how long the user was paused at fire time
  - p75_pause_minutes — historical p75 for (category, time_of_day) or
    NULL when cold_start_synthetic

Cold-start fallback: when the user has <5 samples for the (category,
time_of_day) cell OR <7d pause history, mechanism='cold_start_synthetic'
and p75_pause_minutes IS NULL.

Companion: archive/migration_038_for_supabase_sql_editor.sql for the
operator-on-wake Supabase paste-first workflow (per
feedback_migration_first.md — running model on prod schema without
this column = sign-in breaks).
"""
from alembic import op
import sqlalchemy as sa


revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_prediction_log",
        sa.Column("firing_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("stopwatch_session.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            sa.String(36),
            sa.ForeignKey("task.task_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fired_at", sa.DateTime(), nullable=False),
        sa.Column("paused_for_minutes", sa.Float(), nullable=False),
        sa.Column("p75_pause_minutes", sa.Float(), nullable=True),
        sa.Column("mechanism", sa.String(40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("user_response", sa.String(20), nullable=True),
        sa.Column("response_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "idx_resume_pred_user_fired_at",
        "resume_prediction_log",
        ["user_id", "fired_at"],
    )
    op.create_index(
        "idx_resume_pred_session",
        "resume_prediction_log",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_resume_pred_session", table_name="resume_prediction_log")
    op.drop_index("idx_resume_pred_user_fired_at", table_name="resume_prediction_log")
    op.drop_table("resume_prediction_log")
