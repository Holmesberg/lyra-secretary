"""Feedback table — alpha-cohort feedback channel.

Revision ID: 040
Revises: 039
Create Date: 2026-04-28

Single-table addition for the in-app feedback widget. Users submit via
Settings page or user-dropdown link; rows here flow to operator email +
Telegram (best-effort) and surface in GET /v1/admin/feedback.

Companion: archive/migration_040_for_supabase_sql_editor.sql for the
operator's pre-pull Supabase paste (per feedback_migration_first.md).
"""
from alembic import op
import sqlalchemy as sa


revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("feedback_id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("user.user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("page_url", sa.String(500), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("error_context", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("operator_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "idx_feedback_status_submitted",
        "feedback",
        ["status", "submitted_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_feedback_status_submitted", table_name="feedback")
    op.drop_table("feedback")
