"""add task_completion_percentage to stopwatch_session

Revision ID: 011
Revises: 010
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "stopwatch_session",
        sa.Column("task_completion_percentage", sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column("stopwatch_session", "task_completion_percentage")
