"""add void_reason_detail for 'other' free-text void reason

Revision ID: 018
Revises: 017
Create Date: 2026-04-09

Phase 3.2 void rule redesign. The existing `voided_reason` column is
repurposed to store the void-reason enum
(test_contamination|duplicate|system_error|data_quality|other).
`void_reason_detail` is a new optional free-text column, required only
when voided_reason='other'. Endpoint and schema enforce this.

Analytics exclusion moves from `initiation_status != 'system_error'`
to ALSO filtering `voided_at IS NULL`, so voided PLANNED/SKIPPED/etc
tasks are hidden from downstream metrics.
"""
from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("task") as batch:
        batch.add_column(sa.Column("void_reason_detail", sa.String(500), nullable=True))


def downgrade():
    with op.batch_alter_table("task") as batch:
        batch.drop_column("void_reason_detail")
