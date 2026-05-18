"""Add transactional activation email state to users.

Revision ID: 052
Revises: 051
Create Date: 2026-05-18

Activation email state is operational account infrastructure only. It must not
be consumed by behavioral analytics, Cortex, clean-data profiles, or adaptive
scheduling.
"""
from alembic import op
import sqlalchemy as sa


revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("activation_email_sent_at", sa.DateTime(), nullable=True))
    op.add_column("user", sa.Column("activation_email_failed_at", sa.DateTime(), nullable=True))
    op.add_column("user", sa.Column("activation_email_last_error", sa.String(80), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "activation_email_last_error")
    op.drop_column("user", "activation_email_failed_at")
    op.drop_column("user", "activation_email_sent_at")
