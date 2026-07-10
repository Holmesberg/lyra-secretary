from datetime import datetime

from app.db.models import User
from app.services.operator_user_projection import (
    email_hash,
    is_test_or_synthetic_user,
    operator_user_rows_snapshot,
    pct,
    short_hash,
)


def _user(user_id: int, email: str, *, first_name: str | None = None) -> User:
    return User(
        user_id=user_id,
        email=email,
        google_first_name=first_name,
        created_at=datetime(2026, 7, 10, 9, 0, 0),
    )


def test_test_or_synthetic_user_classifier_contract():
    synthetic_emails = [
        "fixture.test",
        "student@example.test",
        "test-alpha@example.com",
        "synthetic-alpha@example.com",
        "wave-alpha@example.com",
        "wave1-alpha@example.com",
        "wave2-alpha@example.com",
        "wave3-alpha@example.com",
    ]

    for index, email in enumerate(synthetic_emails, start=1):
        assert is_test_or_synthetic_user(_user(index, email)), email

    for index, email in enumerate(
        ["student@example.com", "wave@example.com", "real-wave-alpha@example.com"],
        start=100,
    ):
        assert not is_test_or_synthetic_user(_user(index, email)), email


def test_hash_helpers_are_stable_and_do_not_emit_email():
    email = "student@example.com"

    assert short_hash(email) == email_hash(email)
    assert len(email_hash(email)) == 12
    assert email not in email_hash(email)
    assert email_hash(None) == short_hash("")


def test_operator_user_rows_snapshot_redacts_email_and_preserves_stage_contract():
    users = [
        _user(1, "signed-up@example.com", first_name="Signed"),
        _user(2, "task-created@example.com", first_name="Task"),
        _user(3, "timer-started@example.com", first_name="Timer"),
        _user(4, "clean-loop@example.com", first_name="Clean"),
    ]
    last_activity = {
        4: datetime(2026, 7, 10, 10, 30, 0),
    }

    rows = operator_user_rows_snapshot(
        users=users,
        closed_sessions_by_user={3: 2, 4: 4},
        clean_sessions_by_user={4: 3},
        task_counts_by_user={2: 1, 3: 1, 4: 1},
        sessions_by_user={3: 2, 4: 4},
        executed_counts_by_user={4: 2},
        open_timer_by_user={3: 1},
        stale_open_by_user={3: 1},
        active_dates_7d={4: {"2026-07-10"}},
        active_dates_14d={4: {"2026-07-09", "2026-07-10"}},
        last_activity=last_activity,
    )

    by_id = {row["user_id"]: row for row in rows}

    assert by_id[1]["last_loop_stage"] == "signed_up"
    assert by_id[2]["last_loop_stage"] == "task_created"
    assert by_id[3]["last_loop_stage"] == "timer_started"
    assert by_id[4]["last_loop_stage"] == "clean_loop"
    assert by_id[4]["clean_trace_ratio"] == 0.75
    assert by_id[4]["active_days_7d"] == 1
    assert by_id[4]["active_days_14d"] == 2
    assert by_id[4]["last_meaningful_activity_at"] == "2026-07-10T10:30:00"

    for user in users:
        row = by_id[user.user_id]
        assert "email" not in row
        assert row["email_hash"] == email_hash(user.email)


def test_pct_handles_empty_denominator():
    assert pct(1, 0) is None
    assert pct(3, 4) == 0.75
