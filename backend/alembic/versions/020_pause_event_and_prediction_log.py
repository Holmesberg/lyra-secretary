"""pause_event table + pause_prediction_log table + stopwatch_session.data_quality_flag retrofit

Revision ID: 020
Revises: 019
Create Date: 2026-04-14

Forged under the Structural Investigation Rule (docs/design_patterns/
structural_investigation_rule.md). Pause-prediction feature specified
assumed pause-event history existed; schema only retained one pause per
session (cleared on resume). This migration adds the missing structure
plus the pause_prediction_log that records what the predictor fired and
what actually happened.

Three changes in one migration, one transaction:

1. pause_event table — per-pause row, created on pause() and closed on
   resume(). Replaces the silent overwrite that was losing earlier pause
   metadata on second-pause-in-session.

2. pause_prediction_log table — pre-registered research artifact for
   VT-17 analyses. Columns match MANIFESTO.md §VT-17 formula:
   fired_at, predicted_at, mechanism, confidence, lead_minutes,
   sample_size, active_task_id, user_response, response_at,
   parent_firing_id (for snooze chains).

3. stopwatch_session.data_quality_flag column — retrofit flag for rows
   the April 14 data-quality audit identified as contaminated:
   - 'possibly_default_pause_metadata' on sessions with
     pause_reason='intentional_break' AND pause_initiator='self' on
     non-voided tasks (n=6, potentially silent-default fill-ins from
     the lines 330-331 defaults being removed in commit 4)
   - 'pause_reason_lost_to_overwrite' on sessions whose task has
     pause_count > 1 on non-voided tasks (n=5, earlier pause's
     reason was overwritten)

Analytics queries MUST filter `data_quality_flag IS NULL` when
analyzing pause metadata before April 15, 2026. The operator notebook
loader (notebooks/operator_analytics.ipynb) should be updated to
default-exclude flagged rows.
"""
from alembic import op
import sqlalchemy as sa


revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade():
    # 1. pause_event — per-pause history
    op.create_table(
        "pause_event",
        sa.Column("pause_event_id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("stopwatch_session.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Denormalized for per-user analytics queries without a join.
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("paused_at_utc", sa.DateTime, nullable=False),
        # NULL while pause is ongoing; filled on resume() or stale-session close.
        sa.Column("resumed_at_utc", sa.DateTime, nullable=True),
        # Float minutes so sub-minute pauses don't truncate (LYR-094 convention).
        sa.Column("duration_minutes", sa.Float, nullable=True),
        # No silent defaults — caller must supply both.
        sa.Column("pause_reason", sa.String(50), nullable=False),
        sa.Column("pause_initiator", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Index("idx_pause_event_user_paused_at", "user_id", "paused_at_utc"),
        sa.Index("idx_pause_event_session", "session_id"),
    )

    # 2. pause_prediction_log — research artifact, VT-17 source of truth
    op.create_table(
        "pause_prediction_log",
        sa.Column("firing_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("fired_at", sa.DateTime, nullable=False),
        sa.Column("predicted_at", sa.DateTime, nullable=False),
        # 'clock_anchor' | 'work_rhythm' — enforced in application layer
        sa.Column("mechanism", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("lead_minutes", sa.Integer, nullable=False),
        sa.Column("sample_size", sa.Integer, nullable=False),
        sa.Column(
            "active_task_id",
            sa.String(36),
            sa.ForeignKey("task.task_id", ondelete="SET NULL"),
            nullable=True,
        ),
        # NULL at fire time, filled by reconciliation job.
        # 'pause_now' | 'dismiss' | 'snooze' | 'no_response'
        sa.Column("user_response", sa.String(20), nullable=True),
        sa.Column("response_at", sa.DateTime, nullable=True),
        sa.Column(
            "parent_firing_id",
            sa.String(36),
            sa.ForeignKey("pause_prediction_log.firing_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Index("idx_pause_pred_user_fired_at", "user_id", "fired_at"),
    )

    # 3. stopwatch_session.data_quality_flag + retrofit the pre-April-15 rows
    with op.batch_alter_table("stopwatch_session") as batch:
        batch.add_column(sa.Column("data_quality_flag", sa.String(50), nullable=True))

    # Retrofit order matters: the 'lost_to_overwrite' flag is more severe
    # (confirms data loss) and must override 'possibly_default' if both apply.
    op.execute(
        """
        UPDATE stopwatch_session
           SET data_quality_flag = 'possibly_default_pause_metadata'
         WHERE pause_reason = 'intentional_break'
           AND pause_initiator = 'self'
           AND task_id IN (
               SELECT task_id FROM task WHERE voided_at IS NULL
           )
        """
    )
    op.execute(
        """
        UPDATE stopwatch_session
           SET data_quality_flag = 'pause_reason_lost_to_overwrite'
         WHERE task_id IN (
               SELECT task_id FROM task
                WHERE pause_count > 1
                  AND voided_at IS NULL
           )
        """
    )


def downgrade():
    with op.batch_alter_table("stopwatch_session") as batch:
        batch.drop_column("data_quality_flag")
    op.drop_index("idx_pause_pred_user_fired_at", table_name="pause_prediction_log")
    op.drop_table("pause_prediction_log")
    op.drop_index("idx_pause_event_session", table_name="pause_event")
    op.drop_index("idx_pause_event_user_paused_at", table_name="pause_event")
    op.drop_table("pause_event")
