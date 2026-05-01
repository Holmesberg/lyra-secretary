"""Per-user Moodle userid + base URL — multi-user safety for WS sync.

Revision ID: 044
Revises: 043
Create Date: 2026-05-01

Background — discovered during operator's question "would [WS backfill]
also work for users too?":

The 043 ship resolved Moodle's userid + base URL from globals
(MOODLE_WS_USERID, MOODLE_WS_BASE_URL). Single-tenant by accident — the
operator was the only user with a token, so it worked. Any second user
connecting WS would hit Moodle's permission model: a wstoken is bound
to its user, and `core_enrol_get_users_courses(userid=<other>)` raises
`accessexception` → my sync code flips the user's
`moodle_ws_disconnect_reason='invalidtoken'` even though the token is
valid. Net effect: alpha-blocking for non-operator users.

Schema additions on `user`:
  - moodle_userid: integer Moodle user-id, captured from
    `core_webservice_get_site_info`'s response when the user connects
    WS. NULL for users who haven't connected WS yet (or for the legacy
    operator row pre-this-migration; the env fallback handles that case
    until they re-connect).
  - moodle_base_url: per-user Moodle host (different schools have
    different LMS deployments). Derived at connect time from the body
    param → iCal URL host → env. Stored so future syncs don't need to
    re-resolve.

Token encryption ships in the same change set (utils/encryption.py):
new connections store `"fernet:" + base64(encrypted)` in
`moodle_ws_token`; the legacy operator's plaintext row stays plaintext
and decrypts as-is via the prefix sniff. No data migration needed.

Companion: archive/migration_044_for_supabase_sql_editor.sql for the
pre-pull Supabase paste (per feedback_migration_first.md).
"""
from alembic import op
import sqlalchemy as sa


revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("moodle_userid", sa.Integer(), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("moodle_base_url", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "moodle_base_url")
    op.drop_column("user", "moodle_userid")
