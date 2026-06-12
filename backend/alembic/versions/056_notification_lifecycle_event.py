"""Create notification lifecycle event table.

Revision ID: 056
Revises: 055
Create Date: 2026-06-08

Durable lifecycle rows separate queued/reserved notifications from browser
render, action, dismissal, expiry, and lost-unrendered outcomes.
"""
from alembic import op
import sqlalchemy as sa


revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_lifecycle_event",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notification_id", sa.String(length=120), nullable=False),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("notification_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("dedupe_key", sa.String(length=200), nullable=True),
        sa.Column("payload_hash", sa.String(length=128), nullable=True),
        sa.Column("content_snapshot", sa.Text(), nullable=True),
        sa.Column("surface_id", sa.String(length=120), nullable=True),
        sa.Column("exposure_id", sa.String(length=36), nullable=True),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("firing_id", sa.String(length=36), nullable=True),
        sa.Column("queued_at", sa.DateTime(), nullable=False),
        sa.Column("reserved_at", sa.DateTime(), nullable=True),
        sa.Column("rendered_at", sa.DateTime(), nullable=True),
        sa.Column("acted_at", sa.DateTime(), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(), nullable=True),
        sa.Column("expired_at", sa.DateTime(), nullable=True),
        sa.Column("lost_unrendered_at", sa.DateTime(), nullable=True),
        sa.Column("last_transition_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["exposure_id"],
            ["exposure_decision_event.exposure_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.user_id"]),
        sa.PrimaryKeyConstraint("event_id"),
        sa.UniqueConstraint(
            "user_id",
            "notification_id",
            "channel",
            name="uq_notification_lifecycle_user_notification_channel",
        ),
    )
    op.create_index(
        "idx_notification_lifecycle_user_created",
        "notification_lifecycle_event",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_notification_lifecycle_status",
        "notification_lifecycle_event",
        ["status"],
        unique=False,
    )
    op.create_index(
        "idx_notification_lifecycle_dedupe",
        "notification_lifecycle_event",
        ["user_id", "dedupe_key"],
        unique=False,
    )
    op.create_index(
        "idx_notification_lifecycle_exposure",
        "notification_lifecycle_event",
        ["exposure_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_notification_lifecycle_exposure",
        table_name="notification_lifecycle_event",
    )
    op.drop_index(
        "idx_notification_lifecycle_dedupe",
        table_name="notification_lifecycle_event",
    )
    op.drop_index(
        "idx_notification_lifecycle_status",
        table_name="notification_lifecycle_event",
    )
    op.drop_index(
        "idx_notification_lifecycle_user_created",
        table_name="notification_lifecycle_event",
    )
    op.drop_table("notification_lifecycle_event")
