"""Add unplanned_reason to task

Revision ID: 008
Revises: 007
Create Date: 2026-04-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('task', sa.Column('unplanned_reason', sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column('task', 'unplanned_reason')
