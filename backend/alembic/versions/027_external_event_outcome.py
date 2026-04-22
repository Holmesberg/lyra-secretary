"""Add external_event_outcome table — user-marked attendance on imported events.

Revision ID: 027
Revises: 026
Create Date: 2026-04-21

Operator asked 2026-04-21 for a "Did you attend?" control on the
/today card for imported Google Calendar events. Stores the user's
yes/no answer without persisting the event itself as a Task row
— keeping the research-integrity separation: imported events never
enter `task`, so H1 queries (SELECT FROM task WHERE ...) remain
exclusively Lyra-native.

Schema:
  - user_id: scoped per operator
  - external_source: 'google_calendar' (future: 'ics', 'outlook', etc.)
  - external_id: the opaque event id from the source (Google's id, ICS UID)
  - outcome: 'attended' | 'skipped' (nullable "unknown" stored as row
    absence, not as a value)
  - event_title, event_start_utc, event_end_utc: snapshot at mark time
    — the source event can be edited/deleted later but the user's
    self-report stays tied to what they saw when they clicked
  - marked_at: timestamp of the user action

Uniqueness: (user_id, external_source, external_id) — flipping the
outcome is an UPDATE, not a duplicate row. User can change their mind;
we keep the latest answer.

VT-23 (pre-registered in docs/strategic_decisions_april_21.md §6):
"external-source attendance self-report" — is user-reported attendance
on calendar-imported events a reliable signal? Potential validity
threats: selection bias (users only mark events they remember),
recency bias (marks cluster near fresh events), social desirability
(marking "attended" for events they feel they should have). This
table accumulates the corpus to test these.
"""
from alembic import op
import sqlalchemy as sa

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_event_outcome",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.user_id"), nullable=False, index=True),
        sa.Column("external_source", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(256), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("event_title", sa.Text(), nullable=True),
        sa.Column("event_start_utc", sa.DateTime(), nullable=True),
        sa.Column("event_end_utc", sa.DateTime(), nullable=True),
        sa.Column("marked_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "user_id", "external_source", "external_id",
            name="uq_external_event_outcome_user_source_extid",
        ),
    )


def downgrade() -> None:
    op.drop_table("external_event_outcome")
