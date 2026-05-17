"""Add security/governance audit event table.

Revision ID: 051
Revises: 050
Create Date: 2026-05-17

SecurityAuditEvent is append-only and governance-only. It must not become
behavioral telemetry or feed execution/research inference paths.
"""
from alembic import op
import sqlalchemy as sa


revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security_audit_event",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("surface", sa.String(160), nullable=False),
        sa.Column("target_type", sa.String(80), nullable=True),
        sa.Column("target_id", sa.String(160), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("user_agent_hash", sa.String(64), nullable=True),
        sa.Column("redacted_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_security_audit_event_actor_user_id",
        "security_audit_event",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_security_audit_event_user_id",
        "security_audit_event",
        ["user_id"],
    )
    op.create_index(
        "ix_security_audit_event_event_type",
        "security_audit_event",
        ["event_type"],
    )
    op.create_index(
        "ix_security_audit_event_status",
        "security_audit_event",
        ["status"],
    )
    op.create_index(
        "ix_security_audit_event_created_at",
        "security_audit_event",
        ["created_at"],
    )
    op.create_index(
        "idx_security_audit_event_created",
        "security_audit_event",
        ["created_at"],
    )
    op.create_index(
        "idx_security_audit_event_type_created",
        "security_audit_event",
        ["event_type", "created_at"],
    )
    op.create_index(
        "idx_security_audit_actor_created",
        "security_audit_event",
        ["actor_user_id", "created_at"],
    )
    op.create_index(
        "idx_security_audit_user_created",
        "security_audit_event",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_security_audit_user_created", table_name="security_audit_event")
    op.drop_index("idx_security_audit_actor_created", table_name="security_audit_event")
    op.drop_index("idx_security_audit_event_type_created", table_name="security_audit_event")
    op.drop_index("idx_security_audit_event_created", table_name="security_audit_event")
    op.drop_index("ix_security_audit_event_created_at", table_name="security_audit_event")
    op.drop_index("ix_security_audit_event_status", table_name="security_audit_event")
    op.drop_index("ix_security_audit_event_event_type", table_name="security_audit_event")
    op.drop_index("ix_security_audit_event_user_id", table_name="security_audit_event")
    op.drop_index("ix_security_audit_event_actor_user_id", table_name="security_audit_event")
    op.drop_table("security_audit_event")
