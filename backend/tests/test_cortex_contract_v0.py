"""Cortex Core v0 contract tests."""

import math
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import (
    Deadline,
    PauseEvent,
    StopwatchSession,
    Task,
    TaskState,
    User,
)
from app.services.cortex import (
    classify_topology,
    cortex_event,
    measured_execution_query,
    pause_process_query,
    planning_calibration_query,
    task_metrics,
)
from tests.conftest import auth_headers


def _recent_start() -> datetime:
    return (datetime.utcnow() - timedelta(days=2)).replace(
        hour=9,
        minute=0,
        second=0,
        microsecond=0,
    )


@pytest.fixture(autouse=True)
def _clean(db):
    db.rollback()
    for model in (PauseEvent, StopwatchSession, Task, Deadline, User):
        db.query(model).delete()
    db.commit()
    yield
    db.rollback()
    for model in (PauseEvent, StopwatchSession, Task, Deadline, User):
        db.query(model).delete()
    db.commit()


def _user(db, *, is_operator: bool = False) -> User:
    u = User(
        email=f"{uuid4()}@test.local",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=is_operator,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _task(
    user_id: int,
    *,
    planned: int = 60,
    executed: int | None = 90,
    state: TaskState = TaskState.EXECUTED,
    initiation_status: str = "initiated",
    category: str = "development",
    deadline_id: str | None = None,
    start: datetime | None = None,
) -> Task:
    start = start or _recent_start()
    end = start + timedelta(minutes=planned)
    executed_start = start if executed is not None else None
    executed_end = start + timedelta(minutes=executed) if executed is not None else None
    return Task(
        task_id=str(uuid4()),
        user_id=user_id,
        title="cortex task",
        category=category,
        planned_start_utc=start,
        planned_end_utc=end,
        planned_duration_minutes=planned,
        executed_start_utc=executed_start,
        executed_end_utc=executed_end,
        executed_duration_minutes=executed,
        state=state,
        initiation_status=initiation_status,
        deadline_id=deadline_id,
    )


def _session(
    task: Task,
    *,
    user_id: int,
    auto_closed: bool = False,
    data_quality_flag: str | None = None,
    start: datetime | None = None,
) -> StopwatchSession:
    start = start or task.executed_start_utc or task.planned_start_utc
    end = task.executed_end_utc or (start + timedelta(minutes=task.planned_duration_minutes))
    return StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=user_id,
        start_time_utc=start,
        end_time_utc=end,
        auto_closed=auto_closed,
        total_paused_minutes=0.0,
        data_quality_flag=data_quality_flag,
    )


def test_task_metrics_use_executed_over_planned_and_log_symmetry():
    over = _task(1, planned=60, executed=120)
    under = _task(1, planned=60, executed=30)

    over_m = task_metrics(over)
    under_m = task_metrics(under)

    assert over_m.execution_multiplier == 2.0
    assert under_m.execution_multiplier == 0.5
    assert over_m.log_execution_multiplier == pytest.approx(math.log(2.0))
    assert under_m.log_execution_multiplier == pytest.approx(-math.log(2.0))
    assert over_m.active_delta_minutes == 60.0
    assert over_m.legacy_duration_delta_minutes == -60.0


def test_cortex_event_envelope_is_exact_and_rejects_derived_or_latent_payload():
    evt = cortex_event(
        source="task",
        source_id="task-1",
        user_id=7,
        task_id="task-1",
        event_type="TASK_CREATED",
        occurred_at=datetime(2026, 5, 1, 9, 0, 0),
        provenance="observed",
        exposure_state="unknown",
        payload={"planned_duration_minutes": 60},
    )

    assert list(evt.to_dict().keys()) == [
        "event_id",
        "source",
        "source_id",
        "user_id",
        "task_id",
        "event_type",
        "occurred_at",
        "provenance",
        "exposure_state",
        "payload",
    ]

    with pytest.raises(ValueError, match="derived"):
        cortex_event(
            source="task",
            source_id="task-1",
            user_id=7,
            task_id="task-1",
            event_type="STOP",
            occurred_at=datetime(2026, 5, 1, 10, 0, 0),
            provenance="observed",
            exposure_state="none",
            payload={"execution_multiplier": 1.5},
        )

    with pytest.raises(ValueError, match="latent"):
        cortex_event(
            source="task",
            source_id="task-1",
            user_id=7,
            task_id="task-1",
            event_type="STOP",
            occurred_at=datetime(2026, 5, 1, 10, 0, 0),
            provenance="observed",
            exposure_state="none",
            payload={"flow": True},
        )


def test_clean_data_profiles_exclude_contaminated_rows(db):
    user = _user(db)
    external_deadline = Deadline(
        deadline_id=str(uuid4()),
        user_id=user.user_id,
        title="external",
        due_at_utc=datetime(2026, 5, 3, 12, 0, 0),
        state="active",
        external_source="moodle_ics",
        external_id="x-1",
    )
    db.add(external_deadline)

    clean = _task(user.user_id, planned=60, executed=120, category="development")
    external = _task(
        user.user_id,
        planned=60,
        executed=90,
        category="study",
        deadline_id=external_deadline.deadline_id,
    )
    retro = _task(user.user_id, planned=60, executed=60, initiation_status="retroactive")
    system_error = _task(user.user_id, planned=60, executed=60, initiation_status="system_error")
    missing_exec = _task(user.user_id, planned=60, executed=None)
    under_floor = _task(user.user_id, planned=4, executed=5)
    skipped = _task(user.user_id, planned=60, executed=None, state=TaskState.SKIPPED)
    no_stopwatch = _task(user.user_id, planned=60, executed=75)
    auto_closed = _task(user.user_id, planned=60, executed=75)
    flagged = _task(user.user_id, planned=60, executed=75)
    db.add_all([
        clean,
        external,
        retro,
        system_error,
        missing_exec,
        under_floor,
        skipped,
        no_stopwatch,
        auto_closed,
        flagged,
    ])
    db.flush()
    db.add_all([
        _session(clean, user_id=user.user_id),
        _session(external, user_id=user.user_id),
        _session(retro, user_id=user.user_id),
        _session(system_error, user_id=user.user_id),
        _session(under_floor, user_id=user.user_id),
        _session(auto_closed, user_id=user.user_id, auto_closed=True),
        _session(flagged, user_id=user.user_id, data_quality_flag="pause_reason_lost_to_overwrite"),
    ])
    db.commit()

    measured_ids = {t.task_id for t in measured_execution_query(db, user_id=user.user_id).all()}
    planning_ids = {t.task_id for t in planning_calibration_query(db, user_id=user.user_id).all()}

    assert measured_ids == {clean.task_id, external.task_id}
    assert planning_ids == {clean.task_id}


def test_pause_process_profile_excludes_retroactive_and_flagged_pause_rows(db):
    user = _user(db)
    task = _task(user.user_id, planned=60, executed=90)
    db.add(task)
    db.commit()

    clean_session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=user.user_id,
        start_time_utc=datetime(2026, 5, 1, 9, 0, 0),
        end_time_utc=datetime(2026, 5, 1, 10, 30, 0),
        total_paused_minutes=10.0,
        data_quality_flag=None,
    )
    flagged_session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=user.user_id,
        start_time_utc=datetime(2026, 5, 1, 11, 0, 0),
        end_time_utc=datetime(2026, 5, 1, 12, 30, 0),
        total_paused_minutes=10.0,
        data_quality_flag="pause_reason_lost_to_overwrite",
    )
    auto_closed_session = StopwatchSession(
        session_id=str(uuid4()),
        task_id=task.task_id,
        user_id=user.user_id,
        start_time_utc=datetime(2026, 5, 1, 13, 0, 0),
        end_time_utc=datetime(2026, 5, 1, 14, 30, 0),
        auto_closed=True,
        total_paused_minutes=10.0,
        data_quality_flag=None,
    )
    db.add_all([clean_session, flagged_session, auto_closed_session])
    db.flush()
    db.add_all([
        PauseEvent(
            pause_event_id=str(uuid4()),
            session_id=clean_session.session_id,
            user_id=user.user_id,
            paused_at_utc=datetime(2026, 5, 1, 9, 30, 0),
            resumed_at_utc=datetime(2026, 5, 1, 9, 40, 0),
            duration_minutes=10.0,
            pause_reason="distraction",
            pause_initiator="self",
            self_reported_retroactively=False,
        ),
        PauseEvent(
            pause_event_id=str(uuid4()),
            session_id=clean_session.session_id,
            user_id=user.user_id,
            paused_at_utc=datetime(2026, 5, 1, 9, 50, 0),
            resumed_at_utc=datetime(2026, 5, 1, 10, 0, 0),
            duration_minutes=10.0,
            pause_reason="intentional_break",
            pause_initiator="self",
            self_reported_retroactively=True,
        ),
        PauseEvent(
            pause_event_id=str(uuid4()),
            session_id=flagged_session.session_id,
            user_id=user.user_id,
            paused_at_utc=datetime(2026, 5, 1, 11, 30, 0),
            resumed_at_utc=datetime(2026, 5, 1, 11, 40, 0),
            duration_minutes=10.0,
            pause_reason="distraction",
            pause_initiator="self",
            self_reported_retroactively=False,
        ),
        PauseEvent(
            pause_event_id=str(uuid4()),
            session_id=auto_closed_session.session_id,
            user_id=user.user_id,
            paused_at_utc=datetime(2026, 5, 1, 13, 30, 0),
            resumed_at_utc=datetime(2026, 5, 1, 13, 40, 0),
            duration_minutes=10.0,
            pause_reason="distraction",
            pause_initiator="self",
            self_reported_retroactively=False,
        ),
    ])
    db.commit()

    rows = pause_process_query(db, user_id=user.user_id).all()
    assert len(rows) == 1
    assert rows[0].pause_reason == "distraction"
    assert rows[0].session_id == clean_session.session_id


def test_topology_defaults_unknown_and_requires_explicit_evidence():
    assert classify_topology(_task(1)) == "unknown"

    expanded = _task(1)
    expanded.scope_outcome = "expanded"
    assert classify_topology(expanded) == "expanding"

    bullet_expanded = _task(1)
    bullet_expanded.scope_bullet_count_at_plan = 2
    bullet_expanded.scope_bullet_count_at_execute = 4
    assert classify_topology(bullet_expanded) == "expanding"

    fragmented = _task(1)
    fragmented.pause_count = 3
    assert classify_topology(fragmented) == "fragmented"

    biological = _task(1, category="sleep")
    assert classify_topology(biological) == "biological"

    conflicting = _task(1, category="sleep")
    conflicting.pause_count = 3
    assert classify_topology(conflicting) == "unknown"


def test_cortex_diagnostics_endpoint_is_operator_only(db, client):
    user = _user(db, is_operator=False)
    response = client.get(
        "/v1/analytics/cortex/diagnostics",
        headers=auth_headers(user.user_id),
    )
    assert response.status_code == 403


def test_cortex_diagnostics_endpoint_returns_contract_counts(db, client):
    operator = _user(db, is_operator=True)
    other_user = _user(db, is_operator=False)
    clean = _task(operator.user_id, planned=60, executed=120, category="development")
    retro = _task(operator.user_id, planned=60, executed=60, initiation_status="retroactive")
    other = _task(other_user.user_id, planned=60, executed=300, category="study")
    db.add_all([clean, retro, other])
    db.flush()
    db.add_all([
        _session(clean, user_id=operator.user_id),
        _session(retro, user_id=operator.user_id),
        _session(other, user_id=other_user.user_id),
    ])
    db.commit()

    response = client.get(
        "/v1/analytics/cortex/diagnostics?window_days=30",
        headers=auth_headers(operator.user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "cortex_contract_v0"
    assert body["counts"]["tasks_in_window"] == 2
    assert body["counts"]["measured_execution"] == 1
    assert body["exclusions"]["retroactive"] == 1
    assert body["by_category"]["development"]["execution_multiplier_sum_ratio"] == 2.0
    assert "study" not in body["by_category"]
    assert body["invariant_violations"] == []
