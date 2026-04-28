"""User alpha-funnel columns — North Star instrumentation for magic-for-alpha.

Revision ID: 037
Revises: 036
Create Date: 2026-04-28

Adds three lazy-stamped timestamp columns to the user table for tracking
the alpha North Star: `task_created + timer_started within first 3 min`.

  - first_task_at — stamped in TaskManager.create_task on first per-user call
  - first_timer_started_at — stamped in StopwatchManager.start on first call
  - d1_return_at — stamped in /users/me when called ≥24h after created_at

All three are nullable, default NULL, written once. None of them are mutated
after their first stamp.

Research-integrity caveat (per docs/manifesto_alignment_audit_2026_04_28.md
audit item #7): these are Population 2 (product research) signals only, NOT
Population 1 (H1 hypothesis research). Cross-population contamination is
forbidden — funnel statistics must not feed into H1 correlation analyses.

Companion: archive/migration_037_for_supabase_sql_editor.sql for the
operator to apply BEFORE pushing this commit to prod (per
feedback_migration_first.md — model column additions to live Postgres
must run the SQL migration FIRST in Supabase, otherwise every SELECT 500s
and sign-in breaks).
"""
from alembic import op
import sqlalchemy as sa


revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("first_task_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("first_timer_started_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("d1_return_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "d1_return_at")
    op.drop_column("user", "first_timer_started_at")
    op.drop_column("user", "first_task_at")
