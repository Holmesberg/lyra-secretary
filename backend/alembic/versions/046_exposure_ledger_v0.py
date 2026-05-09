"""Exposure Ledger v0 decision/render/suppression atoms.

Revision ID: 046
Revises: 045
Create Date: 2026-05-09

Implements the minimal append-only substrate from
docs/cortex_product_research_contract_v0.md section 10.1. The ledger is a
causal firewall for baseline inference, not an attribution system:

- exposure_decision_event records that an information injection was eligible,
  shown, delayed, suppressed, failed, or unknown.
- exposure_render_event records the exact rendered stimulus when something was
  actually shown.
- suppression_event records eligible-but-withheld exposures so "no render" is
  distinguishable from "nothing eligible".

Attention proxies and temporal associations are intentionally deferred.
"""
from alembic import op
import sqlalchemy as sa


revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exposure_decision_event",
        sa.Column("exposure_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.user_id"), nullable=False),
        sa.Column(
            "task_id",
            sa.String(36),
            sa.ForeignKey("task.task_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("eligible_at", sa.DateTime, nullable=False),
        sa.Column("decision_status", sa.String(20), nullable=False),
        sa.Column("initiative", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("exposure_category", sa.String(40), nullable=False),
        sa.Column("content_template_id", sa.String(120), nullable=True),
        sa.Column("trigger_source", sa.String(40), nullable=False, server_default="unknown"),
        sa.Column("generating_model", sa.String(120), nullable=True),
        sa.Column("generating_version", sa.String(120), nullable=True),
        sa.Column("prompt_hash", sa.String(128), nullable=True),
        sa.Column("data_snapshot_hash", sa.String(128), nullable=True),
        sa.Column("randomization_arm", sa.String(20), nullable=False, server_default="none"),
        sa.Column("randomization_policy_version", sa.String(80), nullable=True),
        sa.Column("delivered_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "idx_exposure_decision_user_eligible",
        "exposure_decision_event",
        ["user_id", "eligible_at"],
    )
    op.create_index(
        "idx_exposure_decision_task",
        "exposure_decision_event",
        ["task_id"],
    )
    op.create_index(
        "idx_exposure_decision_category",
        "exposure_decision_event",
        ["exposure_category"],
    )

    op.create_table(
        "exposure_render_event",
        sa.Column("render_id", sa.String(36), primary_key=True),
        sa.Column(
            "exposure_id",
            sa.String(36),
            sa.ForeignKey("exposure_decision_event.exposure_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rendered_at", sa.DateTime, nullable=False),
        sa.Column("surface", sa.String(80), nullable=False),
        sa.Column("channel", sa.String(40), nullable=False),
        sa.Column("content_hash", sa.String(128), nullable=False),
        sa.Column("content_snapshot", sa.Text, nullable=False),
        sa.Column("render_policy_version", sa.String(80), nullable=False),
        sa.Column("interruptiveness", sa.String(20), nullable=False),
        sa.Column("salience_level", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "idx_exposure_render_exposure",
        "exposure_render_event",
        ["exposure_id"],
    )
    op.create_index(
        "idx_exposure_render_rendered",
        "exposure_render_event",
        ["rendered_at"],
    )

    op.create_table(
        "suppression_event",
        sa.Column("suppression_id", sa.String(36), primary_key=True),
        sa.Column(
            "exposure_id",
            sa.String(36),
            sa.ForeignKey("exposure_decision_event.exposure_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("suppressed_at", sa.DateTime, nullable=False),
        sa.Column("suppression_reason", sa.String(40), nullable=False),
        sa.Column("would_have_rendered_template_id", sa.String(120), nullable=True),
        sa.Column("generating_confidence", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "idx_suppression_exposure",
        "suppression_event",
        ["exposure_id"],
    )
    op.create_index(
        "idx_suppression_suppressed",
        "suppression_event",
        ["suppressed_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_suppression_suppressed", table_name="suppression_event")
    op.drop_index("idx_suppression_exposure", table_name="suppression_event")
    op.drop_table("suppression_event")
    op.drop_index("idx_exposure_render_rendered", table_name="exposure_render_event")
    op.drop_index("idx_exposure_render_exposure", table_name="exposure_render_event")
    op.drop_table("exposure_render_event")
    op.drop_index("idx_exposure_decision_category", table_name="exposure_decision_event")
    op.drop_index("idx_exposure_decision_task", table_name="exposure_decision_event")
    op.drop_index("idx_exposure_decision_user_eligible", table_name="exposure_decision_event")
    op.drop_table("exposure_decision_event")
