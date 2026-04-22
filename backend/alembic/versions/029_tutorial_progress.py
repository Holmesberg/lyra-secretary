"""Add tutorial_completed_at + tutorial_skipped_at to user table.

Revision ID: 029
Revises: 028
Create Date: 2026-04-22

Backs the Apr 22 guided-tour feature (see docs/parked_ideas.md §Guided
product tour). Fresh sign-ins whose onboarding is already completed
(onboarding_completed_at IS NOT NULL) but who have neither stamp yet
see the 8-step overlay on next /today mount. Completing or skipping
stamps the respective field so the overlay doesn't re-fire.

Both fields are nullable so existing users carry a NULL/NULL state and
get the tour on their next sign-in too (u3, u7 never onboarded so the
tour won't fire for them yet; u5, u6 already completed onboarding so
they'll see it once).
"""
from alembic import op
import sqlalchemy as sa

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("tutorial_completed_at", sa.DateTime, nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("tutorial_skipped_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "tutorial_skipped_at")
    op.drop_column("user", "tutorial_completed_at")
