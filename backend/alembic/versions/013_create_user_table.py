"""create user table

Revision ID: 013
Revises: 012
Create Date: 2026-04-09

Multi-user pivot Phase 1. Creates the user table and backfills the
operator as user_id=1 with is_operator=True and notion_enabled=True.
google_id is nullable until Phase 2 wires Google OAuth.

terms_accepted_at and research_consent_at are seeded to NOW() for the
operator (per Q5 confirmation, Apr 9 2026): the operator wrote both
documents, so implicit acceptance is correct.
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user",
        sa.Column("user_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("google_id", sa.String(64), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Africa/Cairo"),
        # sa.text("false") is portable: SQLite accepts and coerces to 0;
        # Postgres requires a boolean literal (it rejects integer 0 as a
        # BOOLEAN default). Previous value sa.text("0") broke the lyraos
        # deployment migration on Apr 16 2026 with DatatypeMismatch.
        sa.Column("is_operator", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notion_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("archetype_id", sa.String(40), nullable=True),
        sa.Column("terms_accepted_at", sa.DateTime(), nullable=True),
        sa.Column("research_consent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_user_email", "user", ["email"], unique=True)
    op.create_index("idx_user_google_id", "user", ["google_id"], unique=True)

    # Operator backfill — user_id = 1. Portable across SQLite + Postgres:
    #   * "user" quoted because `user` is a Postgres reserved word.
    #   * Booleans as `true`/`false` literals (integer 0/1 is rejected by
    #     Postgres as a BOOLEAN default/value).
    #   * Existence check before insert so the migration is idempotent
    #     when replayed over a DB that already has the seed row (needed
    #     by the lyraos.org Supabase migration Apr 16, where this is
    #     followed by a data-copy step from the operator's SQLite).
    conn = op.get_bind()
    now = datetime.utcnow()
    already = conn.execute(
        sa.text('SELECT 1 FROM "user" WHERE user_id = 1')
    ).fetchone()
    if not already:
        conn.execute(
            sa.text(
                'INSERT INTO "user" (user_id, email, google_id, timezone, is_operator, '
                "notion_enabled, archetype_id, terms_accepted_at, research_consent_at, created_at) "
                "VALUES (1, 'alinassersabry@gmail.com', NULL, 'Africa/Cairo', true, true, NULL, "
                ":now, :now, :now)"
            ),
            {"now": now},
        )


def downgrade():
    op.drop_index("idx_user_google_id", table_name="user")
    op.drop_index("idx_user_email", table_name="user")
    op.drop_table("user")
