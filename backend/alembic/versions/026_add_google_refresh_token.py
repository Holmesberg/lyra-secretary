"""Add google_refresh_token to user table.

Revision ID: 026
Revises: 025
Create Date: 2026-04-21

Path B read-only Google Calendar integration (see
docs/strategic_decisions_april_21.md §6). Stores the user's Google
OAuth refresh token so the backend can obtain short-lived access
tokens for `calendar.readonly` API calls without requiring the user
to re-authenticate every hour.

Security debt (tracked in docs/do_not_add.md equivalent / LYRA_BUGS):
refresh token stored in plaintext for v1. Fernet-at-rest encryption
deferred to post-launch (Phase 6+). Blast radius: a DB compromise
exposes user calendars; access is read-only so no write-through
damage. Never returned in any API response, never logged.
"""
from alembic import op
import sqlalchemy as sa

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("google_refresh_token", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "google_refresh_token")
