"""Add frontend exposure acknowledgement event.

Revision ID: 050
Revises: 049
Create Date: 2026-05-13

Wave 6 separates system decision/render rows from authenticated client render
acknowledgements. The unique (exposure_id, event_type) constraint makes
frontend render retries idempotent without introducing delivery-state workflow.
"""
from alembic import op
import sqlalchemy as sa


revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exposure_ack_event",
        sa.Column("ack_id", sa.String(36), primary_key=True),
        sa.Column(
            "exposure_id",
            sa.String(36),
            sa.ForeignKey("exposure_decision_event.exposure_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("user.user_id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("acked_at", sa.DateTime(), nullable=False),
        sa.Column("client_event_id", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "exposure_id",
            "event_type",
            name="uq_exposure_ack_exposure_event_type",
        ),
    )
    op.create_index(
        "idx_exposure_ack_user_acked",
        "exposure_ack_event",
        ["user_id", "acked_at"],
    )
    op.create_index(
        "idx_exposure_ack_exposure",
        "exposure_ack_event",
        ["exposure_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_exposure_ack_exposure", table_name="exposure_ack_event")
    op.drop_index("idx_exposure_ack_user_acked", table_name="exposure_ack_event")
    op.drop_table("exposure_ack_event")
