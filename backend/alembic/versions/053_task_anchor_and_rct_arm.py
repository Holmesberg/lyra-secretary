"""Add task anchor and RCT arm telemetry gates.

Revision ID: 053
Revises: 052
Create Date: 2026-05-19

Anchor rows are descriptive schedule structure, not clean calibration evidence.
RCT arm is stamped at task creation so Rule 16 analyses never infer assignment
after the fact.
"""
from alembic import op
import sqlalchemy as sa


revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "task",
        sa.Column(
            "is_anchor",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("task", sa.Column("rct_arm", sa.String(40), nullable=True))

    # Conservative historical backfill for obvious fixed routine blocks.
    # These rows remain descriptive history, but are excluded from clean
    # bias_factor calibration by the service layer.
    op.execute(
        """
        UPDATE task
        SET is_anchor = TRUE
        WHERE lower(coalesce(category, '')) IN ('prayer', 'sleep')
           OR lower(coalesce(title, '')) LIKE '%prayer%'
           OR lower(coalesce(title, '')) LIKE '%fajr%'
           OR lower(coalesce(title, '')) LIKE '%dhuhr%'
           OR lower(coalesce(title, '')) LIKE '%zuhr%'
           OR lower(coalesce(title, '')) LIKE '%asr%'
           OR lower(coalesce(title, '')) LIKE '%maghrib%'
           OR lower(coalesce(title, '')) LIKE '%isha%'
           OR lower(coalesce(title, '')) LIKE '%taraweeh%'
           OR lower(coalesce(title, '')) LIKE '%sleep%'
           OR lower(coalesce(title, '')) LIKE '%nap%'
        """
    )

    op.create_index("idx_task_user_anchor", "task", ["user_id", "is_anchor"])
    op.create_index("idx_task_rct_arm", "task", ["rct_arm"])


def downgrade() -> None:
    op.drop_index("idx_task_rct_arm", table_name="task")
    op.drop_index("idx_task_user_anchor", table_name="task")
    op.drop_column("task", "rct_arm")
    op.drop_column("task", "is_anchor")
