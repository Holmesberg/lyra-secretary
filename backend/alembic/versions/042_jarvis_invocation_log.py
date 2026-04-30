"""JARVIS invocation audit log + task_source 'jarvis' tag.

Revision ID: 042
Revises: 041
Create Date: 2026-04-30

Backs the operator-only JARVIS chat assistant (NVIDIA NIM-powered, 2026-04-30
ship). Two changes:

1. New `jarvis_invocation` table — audit trail for every JARVIS tool call.
   Captures user_id (defense-in-depth: all queries already auto-scoped via
   ContextVar, but the column lets us reconstruct who called what after the
   fact), tool_name, tool_args (JSON), tool_result_summary (truncated for
   non-PII storage), invoked_at, confirmed_at (NULL for read tools that
   execute immediately; populated for write tools after the user clicks the
   confirmation chip).

   Future use cases this enables:
     - "Show me what JARVIS did this week" surface (Apple-tier transparency)
     - Forensic check: "Was this task created by JARVIS or by the user
       typing it themselves?" — disambiguates the source field which only
       knows manual/voice/web/jarvis at the granularity of the entry channel
     - Research-integrity: H1/H2 stratified analysis can exclude
       JARVIS-mediated rows if needed (parallel to external_source filter)

2. TaskSource enum is a String(20) column (not a Postgres ENUM type), so
   adding a new logical value 'jarvis' requires NO schema change — just the
   Python Enum addition in models.py. No-op here, documented for clarity.

Pre-registration footprint:
   - VT-30 (JARVIS-mediated task contamination) candidate. Decision: do NOT
     pre-register yet. v1 is operator-only (is_operator=True gate); only
     operator's data sees JARVIS, and operator data is already excluded
     from the multi-user H1/H2 cohort by the standard exclusion rule. If
     JARVIS opens to non-operator users in v2, append VT-30 to MANIFESTO
     before that ship.

Companion: archive/migration_042_for_supabase_sql_editor.sql for the
operator's pre-pull Supabase paste (per feedback_migration_first.md).
"""
from alembic import op
import sqlalchemy as sa


revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend the task.source CHECK constraint to permit 'jarvis'.
    # Original constraint added in alembic 001, last extended in alembic 016
    # ('web' for retention analytics). SQLite requires batch mode to rewrite
    # table-level CHECK constraints; Postgres uses ALTER TABLE directly.
    with op.batch_alter_table("task") as batch_op:
        batch_op.drop_constraint("check_source", type_="check")
        batch_op.create_check_constraint(
            "check_source",
            "source IN ('manual', 'voice', 'web', 'jarvis')",
        )

    op.create_table(
        "jarvis_invocation",
        sa.Column("invocation_id", sa.String(36), primary_key=True),
        # ON DELETE CASCADE: when a user is deleted (account deletion),
        # the audit trail goes with them — same convention as every other
        # user-scoped table in the schema.
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("user.user_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # The tool function name (e.g., 'list_today_tasks', 'create_task').
        # Indexed because future analytics will group by tool name to see
        # which read/write tools are actually used vs ignored.
        sa.Column("tool_name", sa.String(64), nullable=False, index=True),
        # OpenAI-style tool_args JSON. Bounded by the tool schema — most
        # args are scalars or short strings (task IDs, ISO datetimes,
        # readiness ints). PostgreSQL JSONB on Supabase, plain TEXT on
        # SQLite via SQLAlchemy's generic JSON type.
        sa.Column("tool_args", sa.JSON(), nullable=True),
        # Human-readable one-liner of what the tool returned. Truncated
        # to 500 chars on the write path. Avoids storing full task lists
        # (would balloon the audit log to gigabytes after a few months
        # of heavy JARVIS use).
        sa.Column("tool_result_summary", sa.String(500), nullable=True),
        # Status: 'executed' (read tools, write tools post-confirmation)
        # or 'pending_confirmation' (write tools queued, awaiting user)
        # or 'rejected' (user cancelled the confirmation chip)
        # or 'failed' (tool raised an exception during execution)
        sa.Column("status", sa.String(32), nullable=False, default="executed"),
        # When the agent first dispatched the tool call (always set).
        sa.Column(
            "invoked_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # When the user explicitly confirmed a write action (NULL for
        # read tools and unconfirmed/rejected writes). The confirmed_at
        # − invoked_at delta is a reasoning-time signal: how long does
        # the user think before greenlighting JARVIS to act?
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
    )

    # Composite index for the "show me what JARVIS did today" query
    # pattern. (user_id, invoked_at DESC) covers both the per-user filter
    # and the recency sort without a second sort step.
    op.create_index(
        "ix_jarvis_invocation_user_invoked_at",
        "jarvis_invocation",
        ["user_id", "invoked_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_jarvis_invocation_user_invoked_at", table_name="jarvis_invocation")
    op.drop_table("jarvis_invocation")
    with op.batch_alter_table("task") as batch_op:
        batch_op.drop_constraint("check_source", type_="check")
        batch_op.create_check_constraint(
            "check_source",
            "source IN ('manual', 'voice', 'web')",
        )
