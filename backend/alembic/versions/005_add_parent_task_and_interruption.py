"""Add parent_task_id and interruption_type to task

Revision ID: 005
Revises: 004
Create Date: 2026-04-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('task', sa.Column('parent_task_id', sa.String(36), nullable=True))
    op.add_column('task', sa.Column('interruption_type', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('task', 'parent_task_id')
    op.drop_column('task', 'interruption_type')
