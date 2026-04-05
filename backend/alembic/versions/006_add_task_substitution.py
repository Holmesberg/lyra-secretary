"""Add replaced_by_task_id and replaces_task_id to task

Revision ID: 006
Revises: 005
Create Date: 2026-04-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('task', sa.Column('replaced_by_task_id', sa.String(36), nullable=True))
    op.add_column('task', sa.Column('replaces_task_id', sa.String(36), nullable=True))


def downgrade() -> None:
    op.drop_column('task', 'replaced_by_task_id')
    op.drop_column('task', 'replaces_task_id')
