from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from app.db.models import PauseEvent, StopwatchSession, Task, TaskState
from app.services.interruption_metrics import (
    occupancy_projection,
    pause_overhead_samples_for_signal,
    task_interruption_metrics,
)


@pytest.fixture(autouse=True)
def _clean(db):
    db.execute(text("DELETE FROM pause_event"))
    db.execute(text("DELETE FROM stopwatch_session"))
    db.execute(text("DELETE FROM task"))
    db.commit()
    yield
    db.execute(text("DELETE FROM pause_event"))
    db.execute(text("DELETE FROM stopwatch_session"))
    db.execute(text("DELETE FROM task"))
    db.commit()


def _task(db, idx: int, *, executed: int = 60, category: str = "study") -> Task:
    start = datetime(2026, 5, 1 + idx, 9, 0)
    task = Task(
        task_id=f"interrupt-task-{idx}",
        title=f"task {idx}",
        category=category,
        planned_start_utc=start,
        planned_end_utc=start + timedelta(minutes=60),
        planned_duration_minutes=60,
        executed_start_utc=start,
        executed_end_utc=start + timedelta(minutes=executed),
        executed_duration_minutes=executed,
        state=TaskState.EXECUTED,
        initiation_status="initiated",
        user_id=901,
    )
    db.add(task)
    db.commit()
    return task


def _session(
    db,
    task: Task,
    *,
    pause: float,
    wall: int | None = None,
    auto_closed: bool = False,
    data_quality_flag: str | None = None,
) -> StopwatchSession:
    span = wall if wall is not None else int((task.executed_duration_minutes or 0) + pause)
    session = StopwatchSession(
        task_id=task.task_id,
        user_id=task.user_id,
        start_time_utc=task.executed_start_utc,
        end_time_utc=task.executed_start_utc + timedelta(minutes=span),
        total_paused_minutes=pause,
        auto_closed=auto_closed,
        data_quality_flag=data_quality_flag,
    )
    db.add(session)
    db.commit()
    return session


def test_task_metrics_keep_execution_clean_and_span_includes_pause(db):
    task = _task(db, 1, executed=60)
    session = _session(db, task, pause=60, wall=120)
    db.add(
        PauseEvent(
            session_id=session.session_id,
            user_id=task.user_id,
            paused_at_utc=task.executed_start_utc + timedelta(minutes=30),
            resumed_at_utc=task.executed_start_utc + timedelta(minutes=90),
            duration_minutes=60,
            pause_reason="context_switch",
            pause_initiator="user",
            self_reported_retroactively=False,
        )
    )
    db.commit()

    metrics = task_interruption_metrics(db, task)

    assert metrics.execution_time_minutes == 60
    assert metrics.session_span_minutes == 120
    assert metrics.pause_overhead_minutes == 60
    assert metrics.occupancy_time_minutes == 120
    assert metrics.execution_efficiency == 0.5
    assert metrics.recovery_friction_minutes == 60


def test_pause_overhead_samples_include_zero_and_exclude_dirty_or_stale(db):
    tasks = [_task(db, i) for i in range(6)]
    _session(db, tasks[0], pause=0)
    _session(db, tasks[1], pause=20)
    _session(db, tasks[2], pause=40)
    _session(db, tasks[3], pause=10, auto_closed=True)
    _session(db, tasks[4], pause=10, data_quality_flag="pause_reason_lost_to_overwrite")
    _session(db, tasks[5], pause=300, wall=420)
    tasks[5].initiation_status = "retroactive"
    db.commit()

    samples = pause_overhead_samples_for_signal(
        db,
        tasks=tasks,
        category="study",
        tod="afternoon",
        planned_minutes=60,
        signal_level="category_tod_duration",
    )

    assert samples == [0, 20, 40]


def test_pause_overhead_samples_exclude_forgotten_timer_scale_pauses(db):
    tasks = [_task(db, i) for i in range(4)]
    _session(db, tasks[0], pause=0)
    _session(db, tasks[1], pause=20)
    _session(db, tasks[2], pause=40)
    _session(db, tasks[3], pause=9 * 60, wall=10 * 60)

    samples = pause_overhead_samples_for_signal(
        db,
        tasks=tasks,
        category="study",
        tod="afternoon",
        planned_minutes=60,
        signal_level="category_tod_duration",
    )

    assert samples == [0, 20, 40]


def test_occupancy_projection_adds_bounded_pause_overhead_without_changing_bias(db):
    tasks = [_task(db, i) for i in range(3)]
    for task, pause in zip(tasks, [0, 15, 30]):
        _session(db, task, pause=pause)

    projection = occupancy_projection(
        db,
        tasks=tasks,
        category="study",
        tod="afternoon",
        planned_minutes=60,
        bias_factor_final=1.25,
        source="personal",
        signal_level="category_tod_duration",
    )

    assert projection["execution_suggested_minutes"] == 75
    assert projection["pause_overhead_minutes"] == 15
    assert projection["pause_overhead_sample_size"] == 3
    assert projection["occupancy_suggested_minutes"] == 90
