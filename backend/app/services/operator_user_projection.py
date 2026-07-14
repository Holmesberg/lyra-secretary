"""Read-only operator user projection and identity helpers."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Iterable

from app.db.models import User


def short_hash(value: str | None) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:12]


def email_hash(email: str | None) -> str:
    return short_hash(email)


def is_test_or_synthetic_user(user: User) -> bool:
    email = (user.email or "").strip().lower()
    return (
        email.endswith(".test")
        or email.endswith("@example.test")
        or email.startswith(
            ("test-", "synthetic-", "wave-", "wave1-", "wave2-", "wave3-")
        )
    )


def pct(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def operator_user_rows_snapshot(
    *,
    users: Iterable[User],
    closed_sessions_by_user: dict[int, int],
    clean_sessions_by_user: dict[int, int],
    task_counts_by_user: dict[int, int],
    sessions_by_user: dict[int, int],
    executed_counts_by_user: dict[int, int],
    open_timer_by_user: dict[int, int],
    stale_open_by_user: dict[int, int],
    active_dates_7d: dict[int, set[str]],
    active_dates_14d: dict[int, set[str]],
    last_activity: dict[int, datetime | None],
) -> list[dict[str, Any]]:
    """Project admitted non-operator users into dashboard rows."""
    rows: list[dict[str, Any]] = []
    for user in users:
        closed_for_user = closed_sessions_by_user.get(user.user_id, 0)
        clean_for_user = clean_sessions_by_user.get(user.user_id, 0)
        if task_counts_by_user.get(user.user_id, 0) == 0:
            stage = "signed_up"
        elif sessions_by_user.get(user.user_id, 0) == 0:
            stage = "task_created"
        elif clean_for_user == 0:
            stage = "timer_started"
        else:
            stage = "clean_loop"
        rows.append({
            "user_id": user.user_id,
            "first_name": user.google_first_name,
            "name_source": "google_profile" if user.google_first_name else None,
            "email_hash": email_hash(user.email),
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_meaningful_activity_at": (
                last_activity[user.user_id].isoformat()
                if last_activity.get(user.user_id)
                else None
            ),
            "active_days_7d": len(active_dates_7d.get(user.user_id, set())),
            "active_days_14d": len(active_dates_14d.get(user.user_id, set())),
            "task_count": task_counts_by_user.get(user.user_id, 0),
            "executed_task_count": executed_counts_by_user.get(user.user_id, 0),
            "stopwatch_session_count": sessions_by_user.get(user.user_id, 0),
            "clean_trace_ratio": pct(clean_for_user, closed_for_user),
            "open_timer_count": open_timer_by_user.get(user.user_id, 0),
            "paused_over_72h_count": stale_open_by_user.get(user.user_id, 0),
            "last_loop_stage": stage,
        })
    return rows
