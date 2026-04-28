"""Trust-not-rewrite contract — task.llm_alternative_suggestion column.

Revision ID: 039
Revises: 038
Create Date: 2026-04-28

Adds a JSONB column for the magic-for-alpha "possible better match"
flow. When a heuristic-bound or user-bound task gets a competing
deadline suggestion from the async LLM enrichment, the LLM stores its
alternative here INSTEAD of overwriting task.deadline_id. The frontend
chip renders "Possible better match — [keep current] [switch]" when
this field is non-null. User decides; the system never silently
rewrites a binding the user has already seen.

Pre-registration footnote: this column is audit-trail data only and
does not enter Rule 14's H2 ρ computation. Rule 14 reads
deadline_match_source on the canonical task.deadline_id binding;
llm_alternative_suggestion is read by the chip render path and
analytics-side comparisons (LLM-vs-heuristic agreement rate) but
never substitutes for the canonical column.

Companion: archive/migration_039_for_supabase_sql_editor.sql.
"""
from alembic import op
import sqlalchemy as sa


revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "task",
        sa.Column("llm_alternative_suggestion", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("task", "llm_alternative_suggestion")
