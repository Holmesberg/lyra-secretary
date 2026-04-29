"""Moodle LMS integration — external-source columns on deadline + user URL.

Revision ID: 041
Revises: 040
Create Date: 2026-04-29

Adds the schema needed for the Moodle iCal subscription import.

Per `docs/strategic_decisions_april_29.md` (LMS wedge call) and Appendix C
of the strategic plan: imported deadlines live in the `deadline` table
alongside native ones (clean UX), but are flagged with an external_source
marker so H2 research queries (Rules 14-16) can filter them out via
`WHERE external_source IS NULL`. This mirrors the
`external_event_outcome` template (alembic 027) — same convention.

Mechanism:
  - User pastes a private Moodle .ics subscription URL into /settings.
  - Backend stores it in user.moodle_ics_url (Text, plaintext in v1 —
    Fernet encryption deferred to Phase 6+ security debt, matches
    user.google_refresh_token convention).
  - APScheduler job runs every 6h per connected user, fetches the URL,
    parses VEVENTs, upserts into `deadline` keyed on
    (user_id, external_source='moodle_ics', external_id=<iCal UID>).
  - On token revocation (4xx), moodle_ics_url cleared,
    moodle_disconnect_reason set so frontend can surface "reconnect needed"
    instead of failing silently.

Pre-registration: VT-29 (External-deadline contamination) appended to
MANIFESTO.md — distinguishing test required at H2 publication time.

Companion: archive/migration_041_for_supabase_sql_editor.sql for the
operator's pre-pull Supabase paste (per feedback_migration_first.md).
"""
from alembic import op
import sqlalchemy as sa


revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Deadline: external-source flagging columns. NULL on all existing
    # rows = native (operator-or-user-typed) deadline. Non-NULL =
    # imported from a third-party source; H2 queries MUST filter
    # `WHERE external_source IS NULL`.
    op.add_column(
        "deadline",
        sa.Column("external_source", sa.String(32), nullable=True),
    )
    op.add_column(
        "deadline",
        sa.Column("external_id", sa.String(256), nullable=True),
    )
    op.add_column(
        "deadline",
        sa.Column("imported_at", sa.DateTime(), nullable=True),
    )

    # Composite unique index, partial (only enforced for imported rows).
    # Native deadlines have NULL external_*, so they don't participate
    # in uniqueness. Used by upsert_external_deadline as the conflict
    # key for ON CONFLICT-style logic.
    op.create_index(
        "uq_deadline_external",
        "deadline",
        ["user_id", "external_source", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_source IS NOT NULL"),
        sqlite_where=sa.text("external_source IS NOT NULL"),
    )

    # User: Moodle integration columns.
    # moodle_ics_url is credential-equivalent (anyone with the URL can
    # read the user's calendar). Plaintext storage in v1 — same trust
    # class as google_refresh_token (line 564 in models.py); Fernet
    # encryption deferred to Phase 6+ security debt. NEVER returned in
    # any API response, NEVER logged in full.
    op.add_column(
        "user",
        sa.Column("moodle_ics_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("moodle_last_synced_at", sa.DateTime(), nullable=True),
    )
    # Set when sync fails permanently (e.g., 4xx — token revoked).
    # Frontend reads this to surface "Reconnect needed" instead of
    # silently failing. Cleared when user reconnects.
    op.add_column(
        "user",
        sa.Column("moodle_disconnect_reason", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "moodle_disconnect_reason")
    op.drop_column("user", "moodle_last_synced_at")
    op.drop_column("user", "moodle_ics_url")
    op.drop_index("uq_deadline_external", table_name="deadline")
    op.drop_column("deadline", "imported_at")
    op.drop_column("deadline", "external_id")
    op.drop_column("deadline", "external_source")
