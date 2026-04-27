"""calibration_nudge_event — Loop 1 outcome log per feedback_loops_closure_plan.md.

Revision ID: 034
Revises: 033
Create Date: 2026-04-27

Closes the highest-leverage research feedback loop: does the calibration
nudge mechanism actually improve calibration? Captures every NewTaskModal
nudge fire + user decision (accept | dismiss) + the executed-duration
outcome once the task transitions to EXECUTED. Pre-registered metric is
the delta-difference between accepted-vs-dismissed (mean overrun on
accepted nudges should be lower if the suggestion was helpful).

Mirrors the pause_prediction_log template from alembic 020 — fire-time
insertion with nullable outcome columns, reconciliation fills them in.
But we go INLINE in TaskManager.complete_task instead of an APScheduler
job (single UPDATE per stop, sub-millisecond) — cheaper than the per-
user sweep loop pause_prediction needed.

Includes voided_at column for symmetry with task voiding (LYR-095
pattern + Loop 11 task_deadline_outcome precedent). If the underlying
task is voided post-creation, the nudge event is invalidatable
(NOT deleted — preserves the audit trail) and analytics queries filter
voided_at IS NULL.
"""
from alembic import op
import sqlalchemy as sa


revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calibration_nudge_event",
        sa.Column("event_id", sa.String(36), primary_key=True),
        # Denormalized for per-user analytics queries without a join.
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("user.user_id"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            sa.String(36),
            sa.ForeignKey("task.task_id"),
            nullable=False,
        ),
        # What Lyra suggested at nudge-fire time.
        sa.Column(
            "suggested_duration_minutes",
            sa.Integer,
            nullable=False,
        ),
        # What the user actually typed in. Decision compares these two.
        sa.Column(
            "user_planned_duration_minutes",
            sa.Integer,
            nullable=False,
        ),
        # Snapshot of bias_factor used to compute the suggestion (pre-
        # registered Rule-13 blend output).
        sa.Column("bias_factor", sa.Float, nullable=False),
        # n_sessions_in_cell at nudge-fire time. <30 → prior-dominant blend.
        sa.Column("sample_size", sa.Integer, nullable=False),
        # 'accepted' (user used suggested_duration) or 'dismissed'
        # (kept their own typed duration). Enforced in application layer.
        sa.Column("user_decision", sa.String(16), nullable=False),
        sa.Column("decided_at", sa.DateTime, nullable=False),
        # Filled by TaskManager.complete_task inline reconciliation when
        # the task hits EXECUTED. NULL = task hasn't completed yet OR was
        # skipped/voided (in which case it stays NULL forever).
        sa.Column("executed_duration_minutes", sa.Integer, nullable=True),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
        # Symmetry with task voiding. If the parent task is voided, set
        # this to invalidate the row from analytics. Don't delete.
        sa.Column("voided_at", sa.DateTime, nullable=True),
    )
    op.create_index(
        "idx_cne_user_decided",
        "calibration_nudge_event",
        ["user_id", "decided_at"],
    )
    op.create_index(
        "idx_cne_task",
        "calibration_nudge_event",
        ["task_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_cne_task", table_name="calibration_nudge_event")
    op.drop_index("idx_cne_user_decided", table_name="calibration_nudge_event")
    op.drop_table("calibration_nudge_event")
