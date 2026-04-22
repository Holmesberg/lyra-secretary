"""Add pause_event.self_reported_retroactively bool.

Revision ID: 030
Revises: 029
Create Date: 2026-04-22

Supports the Apr 22 retroactive pause-confirmation chip: when the
operator returns to /today and sees "Pause predicted around 13:37 —
did it happen?", tapping Yes creates a pause_event stamped with this
flag = true so VT-17d stratified analysis can distinguish real-time-
captured pauses from retroactive self-reports (see MANIFESTO v1.9
Rule 13 / VT-17d amendment).

Default false — all pre-existing rows are real-time captures.
Inference via active_elapsed_at_pause_seconds IS NULL would also work
but explicit flag is cleaner + prevents future code from treating
those two distinctions as equivalent when they may diverge.
"""
from alembic import op
import sqlalchemy as sa

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pause_event",
        sa.Column(
            "self_reported_retroactively",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("pause_event", "self_reported_retroactively")
