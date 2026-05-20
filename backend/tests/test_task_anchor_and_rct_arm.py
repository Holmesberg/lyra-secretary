"""Contracts for anchor-task exclusion and soft-warning RCT arm stamps."""
from datetime import datetime, timedelta

import pytest

from app.db.models import Archetype, Task, TaskState, User
from app.db.scoping import set_current_user_id
from app.services.bias_factor_service import _adaptive_calibration, blend
from app.services.task_manager import (
    RCT_ARM_CONTROL,
    RCT_ARM_TREATMENT,
    TaskManager,
    _rct_arm_for_user,
)


@pytest.fixture(autouse=True)
def _clean_task_rows(db):
    set_current_user_id(None)
    db.rollback()
    db.query(Task).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.query(Task).delete()
    db.commit()


def _make_user(db, email: str) -> User:
    user = User(
        email=email,
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_archetypes(db) -> None:
    rows = [
        ("disciplined_lark", "Disciplined Lark", 0.95, 0.15),
        ("disciplined_owl", "Disciplined Owl", 1.05, 0.20),
        ("diffuse_average", "Diffuse Average", 1.30, 0.30),
        ("procrastinator", "Procrastinator", 1.80, 0.40),
        ("lark_low_discipline", "Lark, Low Discipline", 1.50, 0.35),
    ]
    for archetype_id, name, prior, sigma in rows:
        if db.query(Archetype).filter_by(archetype_id=archetype_id).first():
            continue
        db.add(
            Archetype(
                archetype_id=archetype_id,
                name=name,
                prior_bias_factor=prior,
                prior_sigma=sigma,
            )
        )
    db.commit()


def _task(
    task_id: str,
    user_id: int,
    *,
    day: int,
    planned: int = 60,
    executed: int = 90,
    is_anchor: bool = False,
) -> Task:
    start = datetime(2026, 5, day, 9, 0)
    return Task(
        task_id=task_id,
        title="Fajr prayer" if is_anchor else f"Study session {day}",
        category="study",
        planned_start_utc=start,
        planned_end_utc=start + timedelta(minutes=planned),
        planned_duration_minutes=planned,
        created_at=start,
        executed_start_utc=start,
        executed_end_utc=start + timedelta(minutes=executed),
        executed_duration_minutes=executed,
        state=TaskState.EXECUTED,
        initiation_status="initiated",
        user_id=user_id,
        is_anchor=is_anchor,
        rct_arm=_rct_arm_for_user(user_id),
    )


def test_task_creation_stamps_anchor_and_rct_arm(db):
    user = _make_user(db, "anchor-rct@example.com")
    set_current_user_id(user.user_id)

    start = datetime.utcnow() + timedelta(hours=24)
    task, conflicts, _ = TaskManager(db).create_task(
        title="Fajr prayer",
        start=start,
        end=start + timedelta(minutes=20),
        category=None,
    )

    assert task is not None
    assert conflicts == []
    assert task.is_anchor is True
    assert task.rct_arm == _rct_arm_for_user(user.user_id)
    assert task.rct_arm in {RCT_ARM_CONTROL, RCT_ARM_TREATMENT}


def test_adaptive_calibration_excludes_anchor_rows():
    user_id = 77
    tasks = [
        _task(f"clean-{i}", user_id, day=i, executed=90, is_anchor=False)
        for i in range(1, 4)
    ] + [
        _task(f"anchor-{i}", user_id, day=i + 10, executed=600, is_anchor=True)
        for i in range(1, 4)
    ]

    result = _adaptive_calibration(tasks, "study", "morning", 60)

    assert result["source"] == "personal"
    assert result["cell"]["sessions"] == 3
    assert result["cell"]["bias_factor"] == 1.5


def test_blend_excludes_anchor_rows_from_personal_weight(db):
    _seed_archetypes(db)
    user = _make_user(db, "blend-anchor@example.com")
    set_current_user_id(user.user_id)
    tasks = [
        _task(f"blend-clean-{i}", user.user_id, day=i, executed=90, is_anchor=False)
        for i in range(1, 4)
    ] + [
        _task(f"blend-anchor-{i}", user.user_id, day=i + 10, executed=600, is_anchor=True)
        for i in range(1, 4)
    ]
    for task in tasks:
        db.add(task)
    db.commit()

    result = blend(db, user.user_id, tasks, "study", "morning", 60)

    assert result["source"] == "personal"
    assert result["cell"]["sessions"] == 3
    assert result["personal_weight"] == 0.1
