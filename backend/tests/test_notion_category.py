"""
Tests for LYR-046: Category must always be present in Notion sync payload.
Previously, the conditional `if task.category` skipped the field on updates,
allowing Notion to drift from SQLite state.
"""
from unittest.mock import MagicMock
from app.services.notion_client import NotionClient
from app.db.models import Task, TaskState


def _make_task(category=None):
    t = MagicMock(spec=Task)
    t.task_id = "test-id"
    t.title = "Test task"
    t.category = category
    t.state = TaskState.EXECUTED
    t.notion_page_id = "page-id"
    t.executed_start_utc = None
    t.executed_end_utc = None
    t.planned_start_utc = None
    t.planned_end_utc = None
    return t


def test_category_always_in_payload_when_set():
    client = NotionClient.__new__(NotionClient)
    task = _make_task(category="development")
    props = client._build_properties(task)
    assert "Category" in props
    assert props["Category"]["multi_select"] == [{"name": "development"}]


def test_category_always_in_payload_when_none():
    """Category must be included even when None — empty array clears Notion field."""
    client = NotionClient.__new__(NotionClient)
    task = _make_task(category=None)
    props = client._build_properties(task)
    assert "Category" in props
    assert props["Category"]["multi_select"] == []


def test_category_always_in_payload_when_empty_string():
    """Empty string category also results in empty multi_select."""
    client = NotionClient.__new__(NotionClient)
    task = _make_task(category="")
    props = client._build_properties(task)
    assert "Category" in props
    assert props["Category"]["multi_select"] == []
