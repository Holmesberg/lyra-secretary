"""reflection_view_log.outcome — V3 engagement-signal coverage for Phase 6.

Revision ID: 035
Revises: 034
Create Date: 2026-04-27

Closes the V3 logging-spec gap caught in the Apr 27 drift audit
(`docs/phase_6_architecture_backlog.md:227`): the canonical V3 spec
for the `creation_nudge` reflection_type calls for `outcome (kept /
adjusted / dismissed)` per surface fire, but the existing
`reflection_view_log` schema lacked the column. Without it, the
Phase 6 router has nowhere to read user decisions on the calibration
nudge — V3 training data is incomplete.

Adds a nullable `outcome` VARCHAR(20). NULL when:
- The surface doesn't carry a decision (micro_mirror, banner — they
  are informational, not decisional).
- The surface IS decisional but the user closed the modal without
  deciding (rare; we do not currently capture that explicitly).

Populated when:
- `creation_nudge`: 'kept' | 'adjusted' | 'dismissed' (mapped from
  `CalibrationNudgeEvent.user_decision` at fire time — see
  `task_manager.create_task`).
- `pause_prediction` (forward): 'accepted' | 'snoozed' | 'dismissed'.

Backfill not attempted — historical rows had no decision recorded
beyond the calibration_nudge_event row; outcome column on prior rows
remains NULL by design.
"""
from alembic import op
import sqlalchemy as sa


revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reflection_view_log",
        sa.Column("outcome", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reflection_view_log", "outcome")
