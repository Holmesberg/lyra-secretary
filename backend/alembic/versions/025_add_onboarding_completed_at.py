"""Add onboarding_completed_at to user table.

Revision ID: 025
Revises: 024
Create Date: 2026-04-21

Part of the Path B commitment (see docs/strategic_decisions_april_21.md
§1). Tracks whether the user has passed through the first-session
planning ritual — either by creating their first task or by opting
out. Stamped atomically by the task_manager on first task creation,
or by the /users/me/skip-onboarding endpoint when the user declines
the ritual but still proceeds into the app.

Kill criterion pre-registered 2026-05-21 reads this column to compute
"% of first-session planning task completers that logged a second
planning task before session 10."
"""
from alembic import op
import sqlalchemy as sa

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("onboarding_completed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "onboarding_completed_at")
