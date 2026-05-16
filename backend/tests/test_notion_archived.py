"""
Tests for LYR-091: Notion archived-page errors must short-circuit instead of
feeding back into the retry queue forever.

An archived Notion page is a permanent state — retrying produces pure log
noise every 5 minutes. sync_task must detect the specific "archived" API
error, log once, and return None (no-op success) so the retry worker's
success_count / ltrim mechanism drops the item from the queue head.
"""
from unittest.mock import MagicMock, patch

import logging
import pytest
from notion_client.errors import APIResponseError

from app.services.notion_client import NotionClient
from app.db.models import Task, TaskState


def _make_task():
    t = MagicMock(spec=Task)
    t.task_id = "archived-task-id"
    t.user_id = 1
    t.title = "Task bound to archived page"
    t.category = "work"
    t.state = TaskState.EXECUTED
    t.notion_page_id = "archived-page-id"
    t.executed_start_utc = None
    t.executed_end_utc = None
    t.planned_start_utc = None
    t.planned_end_utc = None
    return t


def _archived_api_error():
    """Build the exact APIResponseError Notion raises for archived blocks."""
    response = MagicMock()
    response.text = (
        '{"object":"error","status":400,"code":"validation_error",'
        '"message":"Can\'t edit block that is archived. You must unarchive '
        'the block before editing."}'
    )
    return APIResponseError(
        response=response,
        message="Can't edit block that is archived. You must unarchive the block before editing.",
        code="validation_error",
    )


def _bypass_owner_gate(client: NotionClient):
    """Stub the per-user notion_enabled gate so sync_task reaches the API call."""
    client.database_id = "fake-database-id"


def test_archived_error_returns_none_and_does_not_raise():
    """sync_task must swallow the archived error and return None."""
    client = NotionClient.__new__(NotionClient)
    _bypass_owner_gate(client)
    client.client = MagicMock()
    client.client.pages.update.side_effect = _archived_api_error()

    task = _make_task()

    with patch("app.services.notion_client.settings") as mock_settings, \
         patch("app.db.session.SessionLocal") as mock_session_local:
        mock_settings.NOTION_API_KEY = "fake-key"
        # Stub the owner lookup to pass the notion_enabled gate.
        fake_session = MagicMock()
        owner = MagicMock()
        owner.notion_enabled = True
        fake_session.query.return_value.filter.return_value.first.return_value = owner
        mock_session_local.return_value = fake_session

        result = client.sync_task(task)

    assert result is None
    # Confirm Notion was actually called — we're not short-circuiting earlier.
    assert client.client.pages.update.called


def test_archived_error_is_not_retried_by_backoff_decorator():
    """@retry_with_backoff must not fire: returning None is a normal return."""
    client = NotionClient.__new__(NotionClient)
    _bypass_owner_gate(client)
    client.client = MagicMock()
    client.client.pages.update.side_effect = _archived_api_error()

    task = _make_task()

    with patch("app.services.notion_client.settings") as mock_settings, \
         patch("app.db.session.SessionLocal") as mock_session_local:
        mock_settings.NOTION_API_KEY = "fake-key"
        fake_session = MagicMock()
        owner = MagicMock()
        owner.notion_enabled = True
        fake_session.query.return_value.filter.return_value.first.return_value = owner
        mock_session_local.return_value = fake_session

        client.sync_task(task)

    # pages.update should be called exactly ONCE — the decorator would retry
    # up to 4 times (initial + 3 retries) if the function raised.
    assert client.client.pages.update.call_count == 1


def test_non_archived_api_error_still_raises():
    """Any other Notion API error must still propagate to the retry path."""
    client = NotionClient.__new__(NotionClient)
    _bypass_owner_gate(client)
    client.client = MagicMock()

    other_err = APIResponseError(
        response=MagicMock(text='{"message":"Rate limited"}'),
        message="Rate limited",
        code="rate_limited",
    )
    client.client.pages.update.side_effect = other_err

    task = _make_task()

    with patch("app.services.notion_client.settings") as mock_settings, \
         patch("app.db.session.SessionLocal") as mock_session_local:
        mock_settings.NOTION_API_KEY = "fake-key"
        fake_session = MagicMock()
        owner = MagicMock()
        owner.notion_enabled = True
        fake_session.query.return_value.filter.return_value.first.return_value = owner
        mock_session_local.return_value = fake_session

        try:
            client.sync_task(task)
        except APIResponseError:
            pass
        else:
            raise AssertionError("Expected rate-limit error to propagate")

    # Non-archived errors go through @retry_with_backoff: 1 initial + 3 retries.
    assert client.client.pages.update.call_count == 4


def test_notion_api_error_log_redacts_task_text(caplog):
    """Private task text may go to Notion, but not into backend logs."""
    client = NotionClient.__new__(NotionClient)
    _bypass_owner_gate(client)
    client.client = MagicMock()

    private_title = "PRIVATE TASK TEXT DO NOT LOG"
    other_err = APIResponseError(
        response=MagicMock(text=f'{{"message":"{private_title}"}}'),
        message=f"Validation failed for {private_title}",
        code="validation_error",
    )
    client.client.pages.update.side_effect = other_err
    task = _make_task()
    task.title = private_title

    caplog.set_level(logging.ERROR, logger="app.services.notion_client")
    with patch("app.services.notion_client.settings") as mock_settings, \
         patch("app.db.session.SessionLocal") as mock_session_local:
        mock_settings.NOTION_API_KEY = "fake-key"
        fake_session = MagicMock()
        owner = MagicMock()
        owner.notion_enabled = True
        fake_session.query.return_value.filter.return_value.first.return_value = owner
        mock_session_local.return_value = fake_session

        with pytest.raises(APIResponseError):
            client.sync_task(task)

    assert private_title not in caplog.text
