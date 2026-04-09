"""drop server_default on owning-table user_id + widen total_paused_minutes

Revision ID: 017
Revises: 016
Create Date: 2026-04-09

Phase 3.2 B.1: LYR-093 cross-tenant write leak. Drops the SQL
`DEFAULT '1'` that alembic 014 set on task.user_id and
stopwatch_session.user_id. Combined with the services layer now
passing user_id explicitly (fail-closed via _require_current_user),
any future INSERT that forgets user_id will raise IntegrityError
instead of silently attributing the row to operator (user_id=1).

Also converts stopwatch_session.total_paused_minutes from Integer to
Float so the pause accumulator stores sub-minute durations without
truncation (LYR-094 pause integrity). Timer math in
stopwatch_manager now uses float division.
"""
from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("task") as batch:
        batch.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default=None,
        )
    with op.batch_alter_table("stopwatch_session") as batch:
        batch.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default=None,
        )
        batch.alter_column(
            "total_paused_minutes",
            existing_type=sa.Integer(),
            type_=sa.Float(),
            existing_nullable=False,
            existing_server_default="0",
            server_default="0",
        )


def downgrade():
    with op.batch_alter_table("stopwatch_session") as batch:
        batch.alter_column(
            "total_paused_minutes",
            existing_type=sa.Float(),
            type_=sa.Integer(),
            existing_nullable=False,
            existing_server_default="0",
            server_default="0",
        )
        batch.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default="1",
        )
    with op.batch_alter_table("task") as batch:
        batch.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default="1",
        )
