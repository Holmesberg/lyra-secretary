"""add user_id to task and stopwatch_session

Revision ID: 014
Revises: 013
Create Date: 2026-04-09

Multi-user pivot Phase 1. Adds user_id to owning tables, backfills to
operator (user_id=1), and creates per-user indexes for the hot queries.
SQLite ALTER TABLE can't add a NOT NULL FK in one shot, so we add
nullable, backfill, then leave it nullable=False enforced at the ORM
layer (true NOT NULL would require table recreate; deferred).
"""
from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("task") as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=False, server_default="1"))
    with op.batch_alter_table("stopwatch_session") as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=False, server_default="1"))

    op.create_index("idx_task_user_state", "task", ["user_id", "state"])
    op.create_index("idx_task_user_start", "task", ["user_id", "planned_start_utc"])
    op.create_index("idx_stopwatch_user", "stopwatch_session", ["user_id"])


def downgrade():
    op.drop_index("idx_stopwatch_user", table_name="stopwatch_session")
    op.drop_index("idx_task_user_start", table_name="task")
    op.drop_index("idx_task_user_state", table_name="task")
    with op.batch_alter_table("stopwatch_session") as batch:
        batch.drop_column("user_id")
    with op.batch_alter_table("task") as batch:
        batch.drop_column("user_id")
