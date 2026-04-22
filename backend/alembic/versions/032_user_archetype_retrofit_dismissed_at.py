"""Add user.archetype_retrofit_dismissed_at.

Revision ID: 032
Revises: 031
Create Date: 2026-04-22

Supports the Settings retrofit banner for pre-launch users (u2, u5, u6,
u7 — anyone created before 2026-04-22 clustering launch). The banner
shows iff user has no ArchetypeAssignment AND retrofit_dismissed_at is
NULL. Clicking Dismiss stamps this column; clicking Take-survey writes
an ArchetypeAssignment (at which point the banner's "no assignment"
precondition fails and the banner disappears regardless of this stamp).
"""
from alembic import op
import sqlalchemy as sa

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("archetype_retrofit_dismissed_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "archetype_retrofit_dismissed_at")
