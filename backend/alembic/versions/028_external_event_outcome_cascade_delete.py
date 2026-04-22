"""Add ON DELETE CASCADE to external_event_outcome.user_id FK.

Revision ID: 028
Revises: 027
Create Date: 2026-04-22

Migration 027 introduced external_event_outcome with a bare
`ForeignKey("user.user_id")` — defaults to ON DELETE NO ACTION, which
blocks user row deletion when any outcome row references the user.
Surfaced 2026-04-22 when operator tried to delete alt account u2
(asabryhafez) which had one attendance-marking outcome row left over
from GCal dogfooding — the delete endpoint crashed with a
ForeignKeyViolation and the client saw "fails to fetch".

This migration makes the FK cascade so user deletion purges outcome
rows atomically. Covers every future user-deletion path without the
endpoint having to know about this table.

Retention-consistency caveat (LYR-103, open): task + stopwatch_session
rows are *anonymized* on retention-mode deletion (kept with cleared
identifying fields + post_deletion_retained_at stamp) — they have no
FK to user_id, so they simply stay. external_event_outcome with
CASCADE gets purged instead. If VT-23 aggregate analysis later needs
deleted-user outcome signal, add post_deletion_retained_at +
original_user_id_hash columns to this table (like alembic 019 did
for task/stopwatch_session) and switch the retention branch to
anonymize instead of purge. At current n (1 external_event_outcome
row total in prod), the research signal cost is zero.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres doesn't support ALTER CONSTRAINT for FKs — drop and recreate.
    op.drop_constraint(
        "external_event_outcome_user_id_fkey",
        "external_event_outcome",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "external_event_outcome_user_id_fkey",
        "external_event_outcome",
        "user",
        ["user_id"],
        ["user_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "external_event_outcome_user_id_fkey",
        "external_event_outcome",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "external_event_outcome_user_id_fkey",
        "external_event_outcome",
        "user",
        ["user_id"],
        ["user_id"],
    )
