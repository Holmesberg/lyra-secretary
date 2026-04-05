"""Add pause_reason, pause_initiator, original_pre_task_readiness to stopwatch_session

Revision ID: 004
Revises: 003
Create Date: 2026-04-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('stopwatch_session', sa.Column('pause_reason', sa.String(50), nullable=True))
    op.add_column('stopwatch_session', sa.Column('pause_initiator', sa.String(20), nullable=True))
    op.add_column('stopwatch_session', sa.Column('original_pre_task_readiness', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('stopwatch_session', 'pause_reason')
    op.drop_column('stopwatch_session', 'pause_initiator')
    op.drop_column('stopwatch_session', 'original_pre_task_readiness')
