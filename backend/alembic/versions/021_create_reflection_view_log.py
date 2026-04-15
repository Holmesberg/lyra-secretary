"""reflection_view_log table — persistence for retention-signal impressions

Revision ID: 021
Revises: 020
Create Date: 2026-04-15

Ships as LYR-098 Commit 2b. Required by `docs/design_patterns/
notification_patterns.md` §Saved-to-history: every fired notification
surface writes a row here so a user who dismissed a micro_mirror can
later find it in /insights, and research can compare
surface-exposed vs surface-naive subsequent estimates (VT-21 candidate,
MANIFESTO.md).

Columns:
- view_id: uuid PK, handed back to the client so /viewed and
  /dismissed callbacks can locate the row.
- user_id: scoping column. Auto-filtered by app.db.scoping hook.
- reflection_type: 'micro_mirror' | 'calibration_nudge' (others later
  — archetype reveal, milestone banner).
- task_id: NULLABLE FK to task. Task-bound reflections link back for
  contextual history; non-task reflections (archetype reveal, milestone
  banner) use NULL.
- payload: the rendered string the user actually saw. Stored verbatim
  because helper text changes between releases (e.g., the 2a
  neutralization); historical rows must not be rewritten by
  later-version helpers.
- fired_at: when the backend rendered it.
- viewed_at: NULL until client reports impression.
- dismissed_at: NULL until client reports dismissal.
- dwell_seconds: viewed_at → dismissed_at, computed on dismiss.
- created_at: audit.

Index (user_id, fired_at) supports /insights chronological history.
"""
from alembic import op
import sqlalchemy as sa


revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reflection_view_log",
        sa.Column("view_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("reflection_type", sa.String(30), nullable=False),
        sa.Column(
            "task_id",
            sa.String(36),
            sa.ForeignKey("task.task_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("payload", sa.Text, nullable=False),
        sa.Column("fired_at", sa.DateTime, nullable=False),
        sa.Column("viewed_at", sa.DateTime, nullable=True),
        sa.Column("dismissed_at", sa.DateTime, nullable=True),
        sa.Column("dwell_seconds", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Index("idx_reflection_view_user_fired_at", "user_id", "fired_at"),
    )


def downgrade():
    op.drop_index(
        "idx_reflection_view_user_fired_at", table_name="reflection_view_log"
    )
    op.drop_table("reflection_view_log")
