"""Exposure policy effect diagnostic log.

Revision ID: 047
Revises: 046
Create Date: 2026-05-09

Adds a non-behavioral diagnostic table that records how horizon policies affect
baseline gates over time. This guards against "policy becomes invisible truth":
the system can see when UNKNOWN or ledger_incomplete rates make the gate too
strict, too weak, or incoherent.
"""
from alembic import op
import sqlalchemy as sa


revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exposure_policy_effect_log",
        sa.Column("log_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.user_id"), nullable=False),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("exposure_category", sa.String(40), nullable=False),
        sa.Column("signal_target", sa.String(40), nullable=False),
        sa.Column("state_distribution_counts", sa.JSON, nullable=False),
        sa.Column("unknown_rate", sa.Float, nullable=False),
        sa.Column("ledger_incomplete_rate", sa.Float, nullable=False),
        sa.Column("sample_count", sa.Integer, nullable=False),
        sa.Column("window_start", sa.DateTime, nullable=False),
        sa.Column("window_end", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "idx_exposure_policy_effect_user_created",
        "exposure_policy_effect_log",
        ["user_id", "created_at"],
    )
    op.create_index(
        "idx_exposure_policy_effect_policy_target",
        "exposure_policy_effect_log",
        ["policy_version", "signal_target"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_exposure_policy_effect_policy_target",
        table_name="exposure_policy_effect_log",
    )
    op.drop_index(
        "idx_exposure_policy_effect_user_created",
        table_name="exposure_policy_effect_log",
    )
    op.drop_table("exposure_policy_effect_log")
