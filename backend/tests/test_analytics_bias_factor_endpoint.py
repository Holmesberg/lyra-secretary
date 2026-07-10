from datetime import timedelta
from uuid import uuid4

from app.db.models import (
    Deadline,
    Task,
    TaskExecutionCorrection,
    TaskState,
    User,
)
from app.utils.time_utils import now_utc
from tests.conftest import auth_headers


def _executed_task(
    *,
    user_id: int,
    title: str,
    planned_start,
    planned_minutes: int = 60,
    executed_minutes: int = 90,
    category: str = "study",
    initiation_status: str = "started",
    is_anchor: bool = False,
    voided: bool = False,
    deadline_id: str | None = None,
) -> Task:
    return Task(
        user_id=user_id,
        title=title,
        category=category,
        planned_start_utc=planned_start,
        planned_end_utc=planned_start + timedelta(minutes=planned_minutes),
        planned_duration_minutes=planned_minutes,
        executed_start_utc=planned_start,
        executed_end_utc=planned_start + timedelta(minutes=executed_minutes),
        executed_duration_minutes=executed_minutes,
        state=TaskState.EXECUTED,
        initiation_status=initiation_status,
        is_anchor=is_anchor,
        voided_at=planned_start if voided else None,
        deadline_id=deadline_id,
    )


def test_bias_factor_endpoint_uses_clean_native_execution_rows(db, client):
    user = User(
        email=f"bias-factor-{uuid4()}@example.com",
        timezone="Africa/Cairo",
        is_operator=False,
    )
    db.add(user)
    db.flush()

    base = now_utc().replace(hour=6, minute=0, second=0, microsecond=0)
    imported_deadline = Deadline(
        user_id=user.user_id,
        title="Imported LMS deadline",
        due_at_utc=base + timedelta(days=14),
        external_source="moodle",
    )
    db.add(imported_deadline)
    db.flush()

    clean_rows = [
        _executed_task(
            user_id=user.user_id,
            title=f"clean-{index}",
            planned_start=base + timedelta(days=index),
            planned_minutes=60,
            executed_minutes=90,
        )
        for index in range(3)
    ]
    corrected = _executed_task(
        user_id=user.user_id,
        title="corrected-row",
        planned_start=base + timedelta(days=4),
        planned_minutes=60,
        executed_minutes=300,
    )
    excluded_rows = [
        corrected,
        _executed_task(
            user_id=user.user_id,
            title="retroactive-row",
            planned_start=base + timedelta(days=5),
            initiation_status="retroactive",
            executed_minutes=300,
        ),
        _executed_task(
            user_id=user.user_id,
            title="system-error-row",
            planned_start=base + timedelta(days=6),
            initiation_status="system_error",
            executed_minutes=300,
        ),
        _executed_task(
            user_id=user.user_id,
            title="anchor-row",
            planned_start=base + timedelta(days=7),
            is_anchor=True,
            executed_minutes=300,
        ),
        _executed_task(
            user_id=user.user_id,
            title="voided-row",
            planned_start=base + timedelta(days=8),
            voided=True,
            executed_minutes=300,
        ),
        _executed_task(
            user_id=user.user_id,
            title="imported-deadline-row",
            planned_start=base + timedelta(days=9),
            executed_minutes=300,
            deadline_id=imported_deadline.deadline_id,
        ),
    ]
    db.add_all(clean_rows + excluded_rows)
    db.flush()
    db.add(
        TaskExecutionCorrection(
            task_id=corrected.task_id,
            user_id=user.user_id,
            original_executed_start_utc=corrected.executed_start_utc,
            original_executed_end_utc=corrected.executed_end_utc,
            original_executed_duration_minutes=corrected.executed_duration_minutes,
            corrected_executed_end_utc=corrected.executed_end_utc,
            corrected_executed_duration_minutes=corrected.executed_duration_minutes,
        )
    )
    db.commit()

    response = client.get(
        "/v1/analytics/bias_factor?min_sessions=3",
        headers=auth_headers(user.user_id),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_executed"] == 3
    assert payload["min_sessions"] == 3
    assert payload["insufficient_cells"] == []
    assert payload["global"]["bias_factor"] == 1.5

    assert payload["cells"] == [
        {
            "bias_factor": 1.5,
            "bias_factor_mean": 1.5,
            "sessions": 3,
            "confidence": "low",
            "interpretation": "underestimates",
            "category": "study",
            "time_of_day": "morning",
        }
    ]
    assert payload["category_only"][0]["category"] == "study"
    assert payload["category_only"][0]["sessions"] == 3
    assert payload["time_of_day_only"][0]["time_of_day"] == "morning"
    assert payload["time_of_day_only"][0]["sessions"] == 3
