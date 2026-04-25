"""
Tests for unplanned_execution_rate in GET /v1/analytics/discrepancy.
"""
from unittest.mock import MagicMock, patch
from app.db.models import Task, TaskState, TaskSource
from app.api.v1.endpoints.analytics import get_discrepancy
from app.utils.time_utils import now_utc
from datetime import timedelta
import asyncio


def _make_task(initiation_status="initiated", unplanned_reason=None):
    t = MagicMock(spec=Task)
    t.task_id = f"task-{id(t)}"
    t.title = "Test"
    t.category = "development"
    t.state = TaskState.EXECUTED
    t.initiation_status = initiation_status
    t.unplanned_reason = unplanned_reason
    t.planned_start_utc = now_utc()
    t.planned_end_utc = now_utc() + timedelta(hours=1)
    t.planned_duration_minutes = 60
    t.executed_start_utc = now_utc()
    t.executed_end_utc = now_utc() + timedelta(hours=1)
    t.executed_duration_minutes = 60
    t.duration_delta_minutes = 0
    t.initiation_delay_minutes = None
    t.pause_count = 0
    t.discrepancy_score = None
    t.signed_discrepancy = None
    t.pre_task_readiness = None
    t.post_task_reflection = None
    t.parent_task_id = None
    t.interruption_type = None
    t.replaces_task_id = None
    return t


def test_unplanned_rate_fields_present():
    """research_summary must include unplanned_execution_rate and breakdown."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [
        _make_task("initiated"),
        _make_task("retroactive", "forgot"),
        _make_task("retroactive", "unexpected"),
    ]
    mock_db.query.return_value.filter.return_value.count.return_value = 0
    mock_db.query.return_value.filter.return_value.all.return_value = []

    # Apr 26 perf fix: get_discrepancy is now sync (was `async def` with no
    # await statements; converted to `def` so FastAPI threadpools it).
    result = get_discrepancy(db=mock_db)
    summary = result["research_layer"]["summary"]

    assert "unplanned_execution_rate" in summary
    assert "retroactive_count" in summary
    assert "unplanned_reason_breakdown" in summary


def test_unplanned_rate_calculation():
    """2 retroactive out of 3 total = 0.667 rate."""
    tasks = [
        _make_task("initiated"),
        _make_task("retroactive", "forgot"),
        _make_task("retroactive", "unexpected"),
    ]
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = tasks
    mock_db.query.return_value.filter.return_value.count.return_value = 0
    mock_db.query.return_value.filter.return_value.all.return_value = []

    # Apr 26 perf fix: get_discrepancy is now sync (was `async def` with no
    # await statements; converted to `def` so FastAPI threadpools it).
    result = get_discrepancy(db=mock_db)
    summary = result["research_layer"]["summary"]

    assert summary["retroactive_count"] == 2
    assert summary["unplanned_execution_rate"] == round(2 / 3, 3)
    assert summary["unplanned_reason_breakdown"]["forgot"] == 1
    assert summary["unplanned_reason_breakdown"]["unexpected"] == 1
