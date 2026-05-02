"""reflection_view_log.event_class — promote event_class from JSON payload to top-level column.

Revision ID: 045
Revises: 044
Create Date: 2026-05-02

Phase 1.5 of the 2026-05-02 system transition (`docs/calibration_contract.md` R7.1,
`/home/alina/.claude/plans/alright-listen-up-claude-delegated-garden.md`).

ReflectionViewLog absorbs both UI impressions (low-frequency) and Phase 6
behavioral telemetry (high-frequency: modal_dwell, pause_hesitation, survey
per-item, etc.). The R7 namespace discipline solved data-model cleanliness via
`telemetry_*` reflection_type prefix. But existing analytics queries that filter
telemetry out via `WHERE reflection_type NOT LIKE 'telemetry_%'` would force
sequential scans on Postgres/Supabase as telemetry volume grows — degrading the
VT-21 stratified-analysis substrate.

Fix (per `feedback_event_class_column.md`): promote `event_class` from JSON
payload to a top-level NOT NULL column with a btree index. Existing VT-21
queries change from negation-pattern to equality on indexed column —
planner-friendly and cross-DB portable.

Schema additions on `reflection_view_log`:
  - event_class: VARCHAR(20) NOT NULL DEFAULT 'impression'.
    Values: 'impression' | 'telemetry'.
    Application-layer enforcement (matches the existing reflection_type pattern;
    no DB CHECK constraint).

Backfill is implicit via DEFAULT: every existing row at migration time is an
impression (no telemetry types have been written yet — Phase 6 lands the first
telemetry writes). New writes from old model code that doesn't know about the
column still succeed because DEFAULT applies.

Index: idx_reflection_view_event_class — btree on event_class. Optimizes
WHERE event_class = 'impression' (the post-Phase-6 form of every existing
NOT LIKE filter).

This migration permitted as a minor exception to the plan's "no new schema, no
new migrations" anti-step-10 fence — adding a column to an existing table for
performance, not a new table.

Companion: archive/migration_045_for_supabase_sql_editor.sql for the
pre-pull Supabase paste (per feedback_migration_first.md).
"""
from alembic import op
import sqlalchemy as sa


revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reflection_view_log",
        sa.Column(
            "event_class",
            sa.String(20),
            nullable=False,
            server_default="impression",
        ),
    )
    op.create_index(
        "idx_reflection_view_event_class",
        "reflection_view_log",
        ["event_class"],
    )


def downgrade() -> None:
    op.drop_index("idx_reflection_view_event_class", table_name="reflection_view_log")
    op.drop_column("reflection_view_log", "event_class")
