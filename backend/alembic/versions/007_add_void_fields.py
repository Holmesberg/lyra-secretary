"""Add voided_at and voided_reason to task

Revision ID: 007
Revises: 006
Create Date: 2026-04-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('task', sa.Column('voided_at', sa.DateTime(), nullable=True))
    op.add_column('task', sa.Column('voided_reason', sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column('task', 'voided_at')
    op.drop_column('task', 'voided_reason')
