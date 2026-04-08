"""add session_index_in_day to task (immutable cascade chain position)

Revision ID: 012
Revises: 011
Create Date: 2026-04-08

Stores session_index_in_day at task creation time so the cascade chain
(Paper 2) is computed against an immutable foundation rather than a
recomputed-at-query-time index that mutates whenever any task is
deleted or voided.

Index resets per local-tz date (Africa/Cairo). Voided rows
(initiation_status='system_error') are excluded from the chain — they do
not occupy a slot. Tiebreaker for identical planned_start_utc:
created_at ASC.
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None

CAIRO = ZoneInfo("Africa/Cairo")
UTC = ZoneInfo("UTC")


def upgrade():
    op.add_column(
        "task",
        sa.Column("session_index_in_day", sa.Integer(), nullable=True),
    )

    # Backfill: replicate the same algorithm the runtime helper will use,
    # so historical data and new data are computed identically.
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT task_id, planned_start_utc, created_at, initiation_status "
        "FROM task "
        "ORDER BY planned_start_utc ASC, created_at ASC"
    )).fetchall()

    day_counter: dict[str, int] = {}
    updates: list[tuple[int, str]] = []
    for row in rows:
        task_id = row[0]
        planned_start_utc = row[1]
        init = row[3]

        if planned_start_utc is None:
            continue
        if init == "system_error":
            # Voided contamination — does not occupy a chain slot
            continue

        # SQLite returns datetime strings; SQLAlchemy may already give a datetime
        if isinstance(planned_start_utc, str):
            ps = datetime.fromisoformat(planned_start_utc)
        else:
            ps = planned_start_utc
        if ps.tzinfo is None:
            ps = ps.replace(tzinfo=UTC)

        local_date = ps.astimezone(CAIRO).date().isoformat()
        idx = day_counter.get(local_date, 0)
        updates.append((idx, task_id))
        day_counter[local_date] = idx + 1

    for idx, task_id in updates:
        conn.execute(
            sa.text("UPDATE task SET session_index_in_day = :idx WHERE task_id = :tid"),
            {"idx": idx, "tid": task_id},
        )


def downgrade():
    op.drop_column("task", "session_index_in_day")
