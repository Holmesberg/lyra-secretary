"""JARVIS endpoint + tool tests (operator-only, NIM-mocked).

Covers:
  - operator-only auth gate (non-operator → 403, unauth → 401)
  - NIM-not-configured graceful degradation (returns error: 'JARVIS offline')
  - read-tool execution via mocked NIM tool calls
  - write-tool confirmation flow (queue → confirm → execute)
  - write-tool rejection flow (queue → cancel → audit row marked rejected)
  - audit log row written for each invocation

We mock nvidia_nim_client.chat_completion so the tests don't hit the
network. The real NIM is exercised only in manual smoke (per the JARVIS
plan's verification matrix).
"""
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.db.models import (
    Deadline,
    JarvisInvocation,
    Task,
    TaskState,
    User,
)
from app.db.scoping import set_current_user_id
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.query(JarvisInvocation).delete()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.query(JarvisInvocation).delete()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()


def _make_user(db, *, is_operator: bool = False) -> User:
    u = User(
        email=f"u{uuid4().hex[:8]}@test",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=is_operator,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _nim_response(*, content=None, tool_calls=None, model="meta/llama-3.3-70b-instruct"):
    """Construct an OpenAI-shaped chat-completion response dict."""
    message = {"role": "assistant"}
    if content is not None:
        message["content"] = content
    if tool_calls is not None:
        message["tool_calls"] = tool_calls
    return {
        "id": "chatcmpl-" + uuid4().hex[:12],
        "model": model,
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
    }


def _tool_call(name, args, tc_id=None):
    import json as _json

    return {
        "id": tc_id or "call_" + uuid4().hex[:8],
        "type": "function",
        "function": {"name": name, "arguments": _json.dumps(args)},
    }


# ---------------------------------------------------------------------------
# Auth gates
# ---------------------------------------------------------------------------


def test_jarvis_ask_non_operator_forbidden(client, db):
    user = _make_user(db, is_operator=False)
    r = client.post(
        "/v1/jarvis/ask",
        json={"message": "hi", "history": []},
        headers=auth_headers(user.user_id),
    )
    assert r.status_code == 403


def test_jarvis_ask_unauthenticated(client):
    r = client.post("/v1/jarvis/ask", json={"message": "hi", "history": []})
    assert r.status_code == 401


def test_jarvis_health_non_operator_forbidden(client, db):
    user = _make_user(db, is_operator=False)
    r = client.get("/v1/jarvis/health", headers=auth_headers(user.user_id))
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# NIM-not-configured graceful degradation
# ---------------------------------------------------------------------------


def test_jarvis_offline_when_nim_not_configured(client, db, monkeypatch):
    op = _make_user(db, is_operator=True)
    monkeypatch.setattr(
        "app.services.nvidia_nim_client.is_configured", lambda: False
    )
    r = client.post(
        "/v1/jarvis/ask",
        json={"message": "what's overdue?", "history": []},
        headers=auth_headers(op.user_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["error"] is not None
    assert "offline" in body["answer"].lower() or "offline" in body["error"].lower()


# ---------------------------------------------------------------------------
# Read-tool execution
# ---------------------------------------------------------------------------


def test_read_tool_executes_and_logs_audit(client, db, monkeypatch):
    op = _make_user(db, is_operator=True)
    # Seed a deadline so list_deadlines has something to return.
    d = Deadline(
        deadline_id=str(uuid4()),
        user_id=op.user_id,
        title="Lab 8",
        due_at_utc=datetime.utcnow() + timedelta(days=2),
        state="active",
    )
    db.add(d)
    db.commit()

    # First NIM call → returns a list_deadlines tool call.
    # Second NIM call (after we feed back the result) → returns plain text.
    responses = iter(
        [
            _nim_response(tool_calls=[_tool_call("list_deadlines", {"window_days": 7})]),
            _nim_response(content="You have 1 upcoming deadline: Lab 8."),
        ]
    )
    monkeypatch.setattr(
        "app.services.nvidia_nim_client.is_configured", lambda: True
    )
    monkeypatch.setattr(
        "app.services.nvidia_nim_client.chat_completion",
        lambda **kwargs: next(responses),
    )

    r = client.post(
        "/v1/jarvis/ask",
        json={"message": "what's coming up?", "history": []},
        headers=auth_headers(op.user_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["error"] is None
    assert "Lab 8" in body["answer"]
    assert len(body["tool_calls_executed"]) == 1
    assert body["tool_calls_executed"][0]["name"] == "list_deadlines"
    assert body["pending_confirmations"] == []

    # Audit row written.
    rows = db.query(JarvisInvocation).filter(
        JarvisInvocation.user_id == op.user_id
    ).all()
    assert len(rows) == 1
    assert rows[0].tool_name == "list_deadlines"
    assert rows[0].status == "executed"
    assert rows[0].confirmed_at is None  # read tools don't get confirmed_at


# ---------------------------------------------------------------------------
# Write-tool queue + confirm flow
# ---------------------------------------------------------------------------


def test_write_tool_queues_for_confirmation(client, db, monkeypatch):
    op = _make_user(db, is_operator=True)
    when_iso = (datetime.utcnow() + timedelta(hours=6)).replace(microsecond=0).isoformat() + "Z"

    responses = iter(
        [
            _nim_response(
                tool_calls=[
                    _tool_call(
                        "create_task",
                        {
                            "title": "Lab 8 problem set",
                            "when_iso": when_iso,
                            "duration_minutes": 30,
                        },
                    )
                ]
            ),
            # Second turn → NIM produces the "queued" summary.
            _nim_response(
                content="Queued: create Lab 8 problem set at " + when_iso + "."
            ),
        ]
    )
    monkeypatch.setattr(
        "app.services.nvidia_nim_client.is_configured", lambda: True
    )
    monkeypatch.setattr(
        "app.services.nvidia_nim_client.chat_completion",
        lambda **kwargs: next(responses),
    )

    r = client.post(
        "/v1/jarvis/ask",
        json={"message": "create a study task", "history": []},
        headers=auth_headers(op.user_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["pending_confirmations"]) == 1
    assert body["pending_confirmations"][0]["name"] == "create_task"

    # Audit row inserted with status=pending_confirmation.
    rows = db.query(JarvisInvocation).filter(
        JarvisInvocation.tool_name == "create_task"
    ).all()
    assert len(rows) == 1
    assert rows[0].status == "pending_confirmation"
    assert rows[0].confirmed_at is None

    # Crucially: NO Task row created yet (write was queued, not executed).
    task_count = db.query(Task).filter(Task.user_id == op.user_id).count()
    assert task_count == 0


def test_write_tool_confirmation_executes_and_creates_task(db, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app, raise_server_exceptions=True)
    op = _make_user(db, is_operator=True)
    # Tz-aware UTC future time so the executor's tz handling treats it as
    # UTC (not Cairo-local-shifted-back-into-the-past). +6h gives plenty
    # of headroom past TaskManager's 5-min-past guard regardless of how
    # USER_TIMEZONE shifts naive datetimes.
    when_iso = (datetime.utcnow() + timedelta(hours=6)).replace(microsecond=0).isoformat() + "Z"

    # Confirmation re-enters the agent loop — needs one NIM response for the
    # follow-up sentence.
    monkeypatch.setattr(
        "app.services.nvidia_nim_client.is_configured", lambda: True
    )
    monkeypatch.setattr(
        "app.services.nvidia_nim_client.chat_completion",
        lambda **kwargs: _nim_response(content="Done — created Lab 8."),
    )

    pending = {
        "tool_call_id": "call_x",
        "name": "create_task",
        "args": {
            "title": "Lab 8",
            "when_iso": when_iso,
            "duration_minutes": 30,
        },
    }
    r = client.post(
        "/v1/jarvis/confirm",
        json={**pending, "history": [], "confirmed": True},
        headers=auth_headers(op.user_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["error"] is None
    assert "Lab 8" in body["answer"]

    # Task should now exist with TaskSource.JARVIS.
    tasks = db.query(Task).filter(Task.user_id == op.user_id).all()
    assert len(tasks) == 1
    assert tasks[0].title == "Lab 8"
    # Source is the enum value 'jarvis' (string column).
    assert str(tasks[0].source).endswith("jarvis") or tasks[0].source == "jarvis"


def test_write_tool_rejection_does_not_execute(client, db, monkeypatch):
    op = _make_user(db, is_operator=True)
    set_current_user_id(op.user_id)
    # Seed a pending row so reject has something to flip.
    pending_row = JarvisInvocation(
        invocation_id=str(uuid4()),
        user_id=op.user_id,
        tool_name="create_task",
        tool_args={"title": "Skip me"},
        tool_result_summary="{queued: true}",
        status="pending_confirmation",
        invoked_at=datetime.utcnow(),
    )
    db.add(pending_row)
    db.commit()
    set_current_user_id(None)

    monkeypatch.setattr(
        "app.services.nvidia_nim_client.is_configured", lambda: True
    )

    r = client.post(
        "/v1/jarvis/confirm",
        json={
            "tool_call_id": "call_x",
            "name": "create_task",
            "args": {"title": "Skip me"},
            "history": [],
            "confirmed": False,
        },
        headers=auth_headers(op.user_id),
    )
    assert r.status_code == 200
    body = r.json()
    assert "Cancelled" in body["answer"]

    # Audit row flipped to rejected; no Task created.
    db.refresh(pending_row)
    assert pending_row.status == "rejected"
    assert db.query(Task).filter(Task.user_id == op.user_id).count() == 0
