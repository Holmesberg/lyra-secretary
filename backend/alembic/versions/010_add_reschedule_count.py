"""add reschedule_count to task

Revision ID: 010
Revises: 009
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "task",
        sa.Column(
            "reschedule_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade():
    op.drop_column("task", "reschedule_count")
