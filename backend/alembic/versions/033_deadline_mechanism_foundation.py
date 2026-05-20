"""Loop 11 - deadline mechanism foundation + scope-bullet instruments.

Revision ID: 033
Revises: 032
Create Date: 2026-04-26

Adds the first-class deadline table, immutable task-deadline outcome table,
and task columns used by the deadline and scope-inflation research paths.

This revision is intentionally idempotent because older local SQLite databases
may have partially applied the original migration before failing on SQLite's
foreign-key ALTER limitations.
"""
from alembic import op
import sqlalchemy as sa


revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _columns(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def upgrade() -> None:
    sqlite = op.get_context().dialect.name == "sqlite"

    if not _table_exists("deadline"):
        op.create_table(
            "deadline",
            sa.Column("deadline_id", sa.String(36), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("user.user_id"),
                nullable=False,
            ),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("due_at_utc", sa.DateTime, nullable=False),
            sa.Column("category_hint", sa.String(100), nullable=True),
            sa.Column(
                "state",
                sa.String(20),
                nullable=False,
                server_default="planned",
            ),
            sa.Column("completed_at", sa.DateTime, nullable=True),
            sa.Column("voided_at", sa.DateTime, nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime,
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
    if "idx_deadline_user_state" not in _indexes("deadline"):
        op.create_index(
            "idx_deadline_user_state",
            "deadline",
            ["user_id", "state", "voided_at"],
        )

    if not _table_exists("task_deadline_outcome"):
        op.create_table(
            "task_deadline_outcome",
            sa.Column(
                "task_id",
                sa.String(36),
                sa.ForeignKey("task.task_id"),
                primary_key=True,
            ),
            sa.Column("user_id", sa.Integer, nullable=False),
            sa.Column("computed_at", sa.DateTime, nullable=False),
            sa.Column("deadline_utc_at_compute", sa.DateTime, nullable=False),
            sa.Column("executed_end_utc_at_compute", sa.DateTime, nullable=False),
            sa.Column("deadline_met", sa.Boolean, nullable=False),
            sa.Column("delay_minutes", sa.Integer, nullable=False),
            sa.Column("voided_at", sa.DateTime, nullable=True),
        )
    if "idx_tdo_user_computed" not in _indexes("task_deadline_outcome"):
        op.create_index(
            "idx_tdo_user_computed",
            "task_deadline_outcome",
            ["user_id", "computed_at"],
        )

    task_columns = _columns("task")
    if "deadline_id" not in task_columns:
        deadline_id_column = (
            sa.Column("deadline_id", sa.String(36), nullable=True)
            if sqlite
            else sa.Column(
                "deadline_id",
                sa.String(36),
                sa.ForeignKey("deadline.deadline_id"),
                nullable=True,
            )
        )
        op.add_column("task", deadline_id_column)
    if "deadline_match_confidence" not in task_columns:
        op.add_column(
            "task",
            sa.Column("deadline_match_confidence", sa.Float, nullable=True),
        )
    if "deadline_match_source" not in task_columns:
        op.add_column(
            "task",
            sa.Column("deadline_match_source", sa.String(20), nullable=True),
        )
    if "scope_bullet_count_at_plan" not in task_columns:
        op.add_column(
            "task",
            sa.Column("scope_bullet_count_at_plan", sa.Integer, nullable=True),
        )
    if "scope_bullet_count_at_execute" not in task_columns:
        op.add_column(
            "task",
            sa.Column("scope_bullet_count_at_execute", sa.Integer, nullable=True),
        )
    if "idx_task_deadline_id" not in _indexes("task"):
        op.create_index("idx_task_deadline_id", "task", ["deadline_id"])


def downgrade() -> None:
    if "idx_task_deadline_id" in _indexes("task"):
        op.drop_index("idx_task_deadline_id", table_name="task")
    for column in (
        "scope_bullet_count_at_execute",
        "scope_bullet_count_at_plan",
        "deadline_match_source",
        "deadline_match_confidence",
        "deadline_id",
    ):
        if column in _columns("task"):
            op.drop_column("task", column)
    if _table_exists("task_deadline_outcome"):
        if "idx_tdo_user_computed" in _indexes("task_deadline_outcome"):
            op.drop_index("idx_tdo_user_computed", table_name="task_deadline_outcome")
        op.drop_table("task_deadline_outcome")
    if _table_exists("deadline"):
        if "idx_deadline_user_state" in _indexes("deadline"):
            op.drop_index("idx_deadline_user_state", table_name="deadline")
        op.drop_table("deadline")
