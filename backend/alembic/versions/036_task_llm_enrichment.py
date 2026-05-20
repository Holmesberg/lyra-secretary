"""task LLM-enrichment columns - Workstream 1 of the magic-for-alpha ship.

Revision ID: 036
Revises: 035
Create Date: 2026-04-28

Adds enrichment fields populated after task creation by the LLM enrichment
worker. The canonical user-accepted deadline remains `deadline_id`.

This migration is idempotent for older local SQLite databases that may have
partially applied the original FK-bearing column before SQLite rejected the
constraint ALTER.
"""
from alembic import op
import sqlalchemy as sa


revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def _indexes(table_name: str) -> set[str]:
    return {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def upgrade() -> None:
    sqlite = op.get_context().dialect.name == "sqlite"
    task_columns = _columns("task")

    if "llm_parse_status" not in task_columns:
        op.add_column(
            "task",
            sa.Column(
                "llm_parse_status",
                sa.String(20),
                nullable=False,
                server_default="pending",
            ),
        )
    if "llm_priority" not in task_columns:
        op.add_column("task", sa.Column("llm_priority", sa.Integer, nullable=True))
    if "llm_inferred_deadline_id" not in task_columns:
        inferred_deadline_column = (
            sa.Column("llm_inferred_deadline_id", sa.String(36), nullable=True)
            if sqlite
            else sa.Column(
                "llm_inferred_deadline_id",
                sa.String(36),
                sa.ForeignKey("deadline.deadline_id", ondelete="SET NULL"),
                nullable=True,
            )
        )
        op.add_column("task", inferred_deadline_column)
    if "llm_deadline_match_confidence" not in task_columns:
        op.add_column(
            "task",
            sa.Column("llm_deadline_match_confidence", sa.Float, nullable=True),
        )
    if "llm_deadline_candidates" not in task_columns:
        op.add_column(
            "task",
            sa.Column("llm_deadline_candidates", sa.JSON, nullable=True),
        )
    if "llm_sub_items" not in task_columns:
        op.add_column("task", sa.Column("llm_sub_items", sa.JSON, nullable=True))
    if "llm_parsed_at" not in task_columns:
        op.add_column("task", sa.Column("llm_parsed_at", sa.DateTime, nullable=True))
    if "llm_binding_rejected_at" not in task_columns:
        op.add_column(
            "task",
            sa.Column("llm_binding_rejected_at", sa.DateTime, nullable=True),
        )

    if "idx_task_llm_parse_pending" not in _indexes("task"):
        op.create_index(
            "idx_task_llm_parse_pending",
            "task",
            ["llm_parse_status", "created_at"],
        )


def downgrade() -> None:
    if "idx_task_llm_parse_pending" in _indexes("task"):
        op.drop_index("idx_task_llm_parse_pending", table_name="task")
    for column in (
        "llm_binding_rejected_at",
        "llm_parsed_at",
        "llm_sub_items",
        "llm_deadline_candidates",
        "llm_deadline_match_confidence",
        "llm_inferred_deadline_id",
        "llm_priority",
        "llm_parse_status",
    ):
        if column in _columns("task"):
            op.drop_column("task", column)
