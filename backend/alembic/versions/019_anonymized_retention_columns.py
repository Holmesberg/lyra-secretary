"""add anonymized retention columns for delete-with-research-retention flow

Revision ID: 019
Revises: 018
Create Date: 2026-04-14

When a user deletes their account with retain_for_research=true,
identifying fields are cleared but behavioral measurements are
preserved for product research (retention analysis, churn patterns).

Two new nullable columns on task and stopwatch_session:
  - post_deletion_retained_at: timestamp when the row was anonymized
  - original_user_id_hash: one-way hash grouping a deleted user's rows
"""
from alembic import op
import sqlalchemy as sa

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("task") as batch:
        batch.add_column(sa.Column("post_deletion_retained_at", sa.DateTime, nullable=True))
        batch.add_column(sa.Column("original_user_id_hash", sa.String(64), nullable=True))

    with op.batch_alter_table("stopwatch_session") as batch:
        batch.add_column(sa.Column("post_deletion_retained_at", sa.DateTime, nullable=True))
        batch.add_column(sa.Column("original_user_id_hash", sa.String(64), nullable=True))


def downgrade():
    with op.batch_alter_table("stopwatch_session") as batch:
        batch.drop_column("original_user_id_hash")
        batch.drop_column("post_deletion_retained_at")

    with op.batch_alter_table("task") as batch:
        batch.drop_column("original_user_id_hash")
        batch.drop_column("post_deletion_retained_at")
