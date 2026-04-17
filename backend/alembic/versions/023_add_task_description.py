"""Add description column to task table.

Revision ID: 023
Revises: 022
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("task", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("task", "description")
