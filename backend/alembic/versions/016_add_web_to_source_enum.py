"""add 'web' to task.source check constraint

Revision ID: 016
Revises: 015
Create Date: 2026-04-09

Phase 3.1 BUG-1: frontend task creation posts source='web' for retention
analytics (distinguish web/openclaw/voice/api). Relax the CHECK constraint
to allow it. SQLite requires batch mode to rewrite table-level constraints.
"""
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("task") as batch_op:
        batch_op.drop_constraint("check_source", type_="check")
        batch_op.create_check_constraint(
            "check_source",
            "source IN ('manual', 'voice', 'web')",
        )


def downgrade():
    with op.batch_alter_table("task") as batch_op:
        batch_op.drop_constraint("check_source", type_="check")
        batch_op.create_check_constraint(
            "check_source",
            "source IN ('manual', 'voice')",
        )
