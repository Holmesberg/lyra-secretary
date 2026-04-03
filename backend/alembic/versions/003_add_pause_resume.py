"""Add pause/resume fields to stopwatch_session and task

Revision ID: 003
Revises: 002
Create Date: 2026-04-03 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('stopwatch_session', sa.Column('paused_at_utc', sa.DateTime(), nullable=True))
    op.add_column('stopwatch_session', sa.Column(
        'total_paused_minutes', sa.Integer(), nullable=False, server_default='0'
    ))
    op.add_column('task', sa.Column(
        'pause_count', sa.Integer(), nullable=False, server_default='0'
    ))


def downgrade() -> None:
    op.drop_column('stopwatch_session', 'paused_at_utc')
    op.drop_column('stopwatch_session', 'total_paused_minutes')
    op.drop_column('task', 'pause_count')
