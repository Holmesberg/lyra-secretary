"""Add operational email engagement telemetry.

Revision ID: 054
Revises: 053
Create Date: 2026-06-04

Rows in this table measure campaign opens/clicks for operator retention
visibility. They are explicitly not clean execution evidence.
"""
from alembic import op
import sqlalchemy as sa


revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_engagement_event",
        sa.Column("event_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("campaign_version", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("recipient_key", sa.String(length=32), nullable=False),
        sa.Column("target_url", sa.String(length=1024), nullable=True),
        sa.Column("provider_message_id", sa.String(length=128), nullable=True),
        sa.Column("request_metadata", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "idx_email_engagement_campaign_event",
        "email_engagement_event",
        ["campaign_version", "event_type", "occurred_at"],
    )
    op.create_index(
        "idx_email_engagement_user",
        "email_engagement_event",
        ["user_id", "occurred_at"],
    )
    op.create_index(
        "idx_email_engagement_recipient",
        "email_engagement_event",
        ["campaign_version", "recipient_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_email_engagement_recipient", table_name="email_engagement_event"
    )
    op.drop_index("idx_email_engagement_user", table_name="email_engagement_event")
    op.drop_index(
        "idx_email_engagement_campaign_event", table_name="email_engagement_event"
    )
    op.drop_table("email_engagement_event")
