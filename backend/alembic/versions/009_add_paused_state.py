"""Add PAUSED to task state CHECK constraint

Revision ID: 009
Revises: 008
Create Date: 2026-04-07 00:00:00.000000

The `state` column is String(20), not a native enum, but the initial schema
baked a CHECK constraint naming the 5 original states. Adding PAUSED as a
valid state requires rewriting that constraint. On SQLite this means a
table recreation via batch_alter_table (Alembic handles this transparently).
"""
from alembic import op
import sqlalchemy as sa


revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('task') as batch_op:
        batch_op.drop_constraint('check_state', type_='check')
        batch_op.create_check_constraint(
            'check_state',
            "state IN ('PLANNED', 'EXECUTING', 'PAUSED', 'EXECUTED', 'SKIPPED', 'DELETED')",
        )


def downgrade() -> None:
    with op.batch_alter_table('task') as batch_op:
        batch_op.drop_constraint('check_state', type_='check')
        batch_op.create_check_constraint(
            'check_state',
            "state IN ('PLANNED', 'EXECUTING', 'EXECUTED', 'SKIPPED', 'DELETED')",
        )
