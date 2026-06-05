"""Store Google profile display and first name.

Revision ID: 055
Revises: 054
Create Date: 2026-06-05

These columns support operator-only analytics identity labels without exposing
raw email addresses. They are not behavioral evidence.
"""
from alembic import op
import sqlalchemy as sa


revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("google_display_name", sa.String(length=120), nullable=True))
    op.add_column("user", sa.Column("google_first_name", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "google_first_name")
    op.drop_column("user", "google_display_name")
