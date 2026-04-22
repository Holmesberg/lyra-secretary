"""Add completed + skipped_at + raw_responses to archetype_assignment.

Revision ID: 031
Revises: 030
Create Date: 2026-04-22

Supports the 2026-04-22 clustering acceleration (see
docs/strategic_decisions_april_22.md §5). The original ArchetypeAssignment
schema (alembic 015) stored per-instrument scores but had no way to
distinguish "user answered the survey" from "user skipped and was
defaulted to Diffuse Average." Three new columns:

  * `completed` — True when the user answered all 4 instruments. False
    when the user skipped the survey entirely or abandoned mid-flow.
    Retention analysis separates bounce from genuine assignment via
    this flag.
  * `skipped_at` — timestamp of explicit skip action. Distinguishes
    "skipped on day 1 at onboarding" from "never reached the survey
    surface."
  * `raw_responses` — JSON blob of the 29-item answer array. Stored so
    future scoring-weight tuning (Gate 3/4 remediation per
    methodology.md:107-137) can re-score without forcing users to
    re-take the survey. NULL for skipped assignments.

Index on (user_id, completed) supports the Settings-page retrofit
banner gate — "show banner iff user has no completed assignment."
"""
from alembic import op
import sqlalchemy as sa

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "archetype_assignment",
        sa.Column(
            "completed",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "archetype_assignment",
        sa.Column("skipped_at", sa.DateTime, nullable=True),
    )
    op.add_column(
        "archetype_assignment",
        sa.Column("raw_responses", sa.JSON, nullable=True),
    )
    op.create_index(
        "idx_archetype_assignment_user_completed",
        "archetype_assignment",
        ["user_id", "completed"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_archetype_assignment_user_completed",
        table_name="archetype_assignment",
    )
    op.drop_column("archetype_assignment", "raw_responses")
    op.drop_column("archetype_assignment", "skipped_at")
    op.drop_column("archetype_assignment", "completed")
