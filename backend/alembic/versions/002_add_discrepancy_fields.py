"""Add discrepancy measurement fields

Revision ID: 002
Revises: 001
Create Date: 2026-04-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('task', sa.Column('pre_task_readiness', sa.Integer(), nullable=True))
    op.add_column('task', sa.Column('post_task_reflection', sa.Integer(), nullable=True))
    op.add_column('task', sa.Column(
        'initiation_status',
        sa.String(20),
        nullable=False,
        server_default='not_started'
    ))
    op.add_column('task', sa.Column('initiation_delay_minutes', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('task', 'initiation_delay_minutes')
    op.drop_column('task', 'initiation_status')
    op.drop_column('task', 'post_task_reflection')
    op.drop_column('task', 'pre_task_readiness')
