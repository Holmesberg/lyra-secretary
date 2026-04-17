"""Add scope_outcome column to task table.

Revision ID: 024
Revises: 023
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("task", sa.Column("scope_outcome", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("task", "scope_outcome")
