"""task LLM-enrichment columns — Workstream 1 of the magic-for-alpha ship.

Revision ID: 036
Revises: 035
Create Date: 2026-04-28

Adds enrichment fields populated by the async background `llm_enrichment`
APScheduler job. The fast path (POST /v1/create) is unchanged — these
columns are written *after* task creation by `enrich_task_via_llm` in
`backend/app/services/llm_parser.py`.

Architectural rule (operator-locked guardrail #1, plan section
"Operator-pushback"): Ollama is enrichment, not critical-path. Existing
fields like `scope_bullet_count_at_plan` (regex) and `deadline_id`
(parser_auto / user_explicit) remain canonical. The new `llm_*` fields
sit alongside as a parallel signal that the user can confirm into the
canonical fields via POST /v1/tasks/{id}/llm-confirm.

`llm_inferred_deadline_id` deliberately does NOT replace `deadline_id`
on enrichment — the user must confirm to copy it across. This preserves
guardrail #2 (no silent auto-binding) at the schema layer: the source
of truth on what the user actually accepted is `deadline_id`, not
`llm_inferred_deadline_id`.

`llm_parse_status` enum semantics:
  - 'pending'      — created, awaiting LLM enrichment
  - 'enriched'     — LLM call succeeded, fields populated
  - 'unavailable'  — Ollama unreachable; UI falls back to regex output
  - 'failed'       — Ollama returned invalid JSON or schema mismatch
                     (after 1 retry); UI also falls back

`llm_sub_items` JSON shape: `[{"text": "...", "scope_bullet": bool}, ...]`
"""
from alembic import op
import sqlalchemy as sa


revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "task",
        sa.Column(
            "llm_parse_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "task",
        sa.Column("llm_priority", sa.Integer, nullable=True),
    )
    op.add_column(
        "task",
        sa.Column(
            "llm_inferred_deadline_id",
            sa.String(36),
            sa.ForeignKey("deadline.deadline_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "task",
        sa.Column("llm_deadline_match_confidence", sa.Float, nullable=True),
    )
    # Tier system per operator-locked UX (2026-04-28):
    #   Tier 1 — silent infer (top confidence > 0.85): auto chip with confirm
    #   Tier 2 — soft ask (top confidence 0.45-0.85): "Related to one of these?"
    #             with the top 2-3 candidates listed
    #   Tier 3 — silent (top confidence < 0.45): no chip
    #   Tier 4 — manual override always available via DeadlinePickerSlot
    # `llm_deadline_candidates` is the list backing Tier 2's options.
    # Shape: [{"deadline_id": "...", "title": "...", "confidence": 0.0-1.0}, ...]
    # Ordered by confidence desc; max 5 entries. Top entry mirrors
    # llm_inferred_deadline_id + llm_deadline_match_confidence for query
    # convenience (frontend reads the JSON list).
    op.add_column(
        "task",
        sa.Column("llm_deadline_candidates", sa.JSON, nullable=True),
    )
    op.add_column(
        "task",
        sa.Column("llm_sub_items", sa.JSON, nullable=True),
    )
    op.add_column(
        "task",
        sa.Column("llm_parsed_at", sa.DateTime, nullable=True),
    )
    # Audit field for guardrail #2 (no silent auto-binding). Stamped when
    # the user explicitly rejects the LLM-suggested binding via
    # POST /v1/tasks/{id}/reject-llm-binding (Workstream 4). Lets us
    # measure precision/recall against user feedback without leaking
    # rejection state into the canonical deadline_id.
    op.add_column(
        "task",
        sa.Column("llm_binding_rejected_at", sa.DateTime, nullable=True),
    )

    # Index the worker query: pending rows ordered by creation time.
    op.create_index(
        "idx_task_llm_parse_pending",
        "task",
        ["llm_parse_status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_task_llm_parse_pending", table_name="task")
    op.drop_column("task", "llm_binding_rejected_at")
    op.drop_column("task", "llm_parsed_at")
    op.drop_column("task", "llm_sub_items")
    op.drop_column("task", "llm_deadline_candidates")
    op.drop_column("task", "llm_deadline_match_confidence")
    op.drop_column("task", "llm_inferred_deadline_id")
    op.drop_column("task", "llm_priority")
    op.drop_column("task", "llm_parse_status")
