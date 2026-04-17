"""Add active_elapsed_at_pause_seconds to pause_event.

Captures the active work time (in seconds) at the exact moment
of each pause — raw data for future fragmentation-index computation
(Rule 10 candidate). Nullable for backfill compatibility with
existing rows.
"""
from alembic import op
import sqlalchemy as sa

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pause_event",
        sa.Column("active_elapsed_at_pause_seconds", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pause_event", "active_elapsed_at_pause_seconds")
