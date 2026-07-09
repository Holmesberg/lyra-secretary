"""Tests for POST /v1/parse/deadline-preview.

The endpoint surfaces a guarded deadline suggestion without writing a
task or authorizing a canonical bind. The NewTaskModal can ask the user
to confirm this suggestion, but /v1/create must still receive an explicit
deadline_id before any binding is written.

This file pins the endpoint contract: empty payload when no candidates,
all-None response when no guarded candidate clears the threshold,
voided/terminal deadlines excluded, cross-user invisibility enforced,
and weak single-token description overlap suppressed.
"""
from datetime import datetime, timedelta
import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.models import Deadline, ExposureDecisionEvent, ExposureRenderEvent, Task, User
from app.db.scoping import set_current_user_id
from app.main import app
from tests.conftest import auth_headers


client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM exposure_ack_event"))
    db.execute(text("DELETE FROM suppression_event"))
    db.execute(text("DELETE FROM exposure_render_event"))
    db.execute(text("DELETE FROM exposure_decision_event"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM deadline"))
    db.execute(text("DELETE FROM \"user\""))
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM exposure_ack_event"))
    db.execute(text("DELETE FROM suppression_event"))
    db.execute(text("DELETE FROM exposure_render_event"))
    db.execute(text("DELETE FROM exposure_decision_event"))
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM deadline"))
    db.execute(text("DELETE FROM \"user\""))
    db.commit()


def _make_user(db, user_id: int, email: str) -> User:
    u = User(
        user_id=user_id, email=email,
        is_operator=False, notion_enabled=False,
        timezone="Africa/Cairo", created_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    return u


def _make_deadline(
    db, user_id: int, *,
    title: str,
    description: str | None = None,
    state: str = "planned",
    voided: bool = False,
    days_out: int = 7,
) -> Deadline:
    from uuid import uuid4
    d = Deadline(
        deadline_id=str(uuid4()),
        user_id=user_id,
        title=title,
        description=description,
        due_at_utc=datetime.utcnow() + timedelta(days=days_out),
        state=state,
        voided_at=datetime.utcnow() if voided else None,
        created_at=datetime.utcnow(),
    )
    db.add(d)
    db.commit()
    return d


# ── Empty state ──────────────────────────────────────────────────
# Note: 401 unauth path is defensively coded (`if uid is None`) but is
# unreachable through TestClient because UserScopeMiddleware defaults
# missing X-User-Id to user_id=1. See docs/testing_patterns.md
# §"Footgun: middleware default user".


def test_no_candidates_returns_all_none(db):
    user = _make_user(db, user_id=77, email="empty@x")
    resp = client.post(
        "/v1/parse/deadline-preview",
        json={"title": "study"},
        headers=auth_headers(user.user_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["deadline_id"] is None
    assert body["deadline_title"] is None
    assert body["deadline_match_confidence"] is None
    assert body["deadline_match_source"] is None


def test_deprecated_parse_remains_unauthenticated_compatibility(monkeypatch):
    from app.schemas.task import TaskParseResponse

    class StubParser:
        def __init__(self, **_kwargs):
            pass

        def parse_chained(self, _text):
            start = datetime.utcnow()
            return [
                TaskParseResponse(
                    title="compat parsed task",
                    start=start,
                    end=start + timedelta(minutes=30),
                    duration_minutes=30,
                    category="work",
                    confidence=0.9,
                )
            ]

    monkeypatch.setattr("app.api.v1.endpoints.parse.TaskParser", StubParser)

    resp = client.post(
        "/v1/parse",
        json={"text": "private task at 5pm for 30 minutes"},
    )

    assert resp.status_code == 200


def test_deprecated_parse_logs_do_not_include_raw_text(db, caplog, monkeypatch):
    from app.schemas.task import TaskParseResponse

    user = _make_user(db, user_id=77, email="parse@x")
    raw_text = "PRIVATE TASK TEXT DO NOT LOG at 5pm for 30 minutes"
    caplog.set_level(logging.INFO, logger="app.api.v1.endpoints.parse")

    class StubParser:
        def __init__(self, **_kwargs):
            pass

        def parse_chained(self, _text):
            start = datetime.utcnow()
            return [
                TaskParseResponse(
                    title="redacted parsed task",
                    start=start,
                    end=start + timedelta(minutes=30),
                    duration_minutes=30,
                    category="work",
                    confidence=0.9,
                )
            ]

    monkeypatch.setattr("app.api.v1.endpoints.parse.TaskParser", StubParser)

    resp = client.post(
        "/v1/parse",
        json={"text": raw_text},
        headers=auth_headers(user.user_id),
    )

    assert resp.status_code == 200
    assert raw_text not in caplog.text


def test_deprecated_parse_uses_pure_parser_without_db_categories(monkeypatch):
    calls = {"init": []}

    class SpyParser:
        def __init__(self, *, use_db_categories: bool):
            calls["init"].append(use_db_categories)

        def parse_chained(self, _text):
            start = datetime.utcnow()
            return [
                TaskParseResponse(
                    title="pure parsed task",
                    start=start,
                    end=start + timedelta(minutes=30),
                    duration_minutes=30,
                    category=None,
                    confidence=0.9,
                )
            ]

    from app.schemas.task import TaskParseResponse

    monkeypatch.setattr("app.api.v1.endpoints.parse.TaskParser", SpyParser)

    resp = client.post(
        "/v1/parse",
        json={"text": "pure parse at 5pm for 30 minutes"},
    )

    assert resp.status_code == 200
    assert calls["init"] == [False]


# ── Happy match ──────────────────────────────────────────────────


def test_strong_keyword_match_returns_binding(db):
    user = _make_user(db, user_id=77, email="match@x")
    deadline = _make_deadline(
        db, user.user_id,
        title="BCI Hackathon",
        description="build the speller backend",
    )
    resp = client.post(
        "/v1/parse/deadline-preview",
        json={"title": "BCI hackathon speller prep"},
        headers=auth_headers(user.user_id),
    )
    body = resp.json()
    assert body["deadline_id"] == deadline.deadline_id
    assert body["deadline_title"] == "BCI Hackathon"
    assert body["deadline_match_source"] == "heuristic_exact_title"
    assert body["deadline_match_confidence"] is not None
    assert 0.5 <= body["deadline_match_confidence"] <= 1.0
    assert body["surface_id"] == "task.deadline_binding_suggestion"
    assert body["truth_class"] == "interpretation"
    assert body["signal_targets"] == ["planning_estimate", "deadline_behavior"]
    assert body["clean_profile"] is None
    assert body["fallback_mode"] == "suppress"
    assert body["exposure_id"]
    assert body["render_id"]

    decision = (
        db.query(ExposureDecisionEvent)
        .filter(ExposureDecisionEvent.exposure_id == body["exposure_id"])
        .one()
    )
    render = (
        db.query(ExposureRenderEvent)
        .filter(ExposureRenderEvent.render_id == body["render_id"])
        .one()
    )
    assert decision.user_id == user.user_id
    assert decision.exposure_category == "scheduling_suggestion"
    assert decision.trigger_source == "parse.deadline_preview"
    assert render.surface == "task.deadline_binding_suggestion"
    assert "Barzakh thinks this binds to BCI Hackathon" in render.content_snapshot


def test_binding_suggestion_suppresses_if_exposure_logging_fails(db, monkeypatch):
    user = _make_user(db, user_id=77, email="emit-fail@x")
    _make_deadline(
        db,
        user.user_id,
        title="BCI Hackathon",
        description="build the speller backend",
    )

    def boom(*_args, **_kwargs):
        raise RuntimeError("ledger unavailable")

    monkeypatch.setattr("app.api.v1.endpoints.parse.emit_surface_render", boom)

    resp = client.post(
        "/v1/parse/deadline-preview",
        json={"title": "BCI hackathon speller prep"},
        headers=auth_headers(user.user_id),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["deadline_id"] is None
    assert db.query(ExposureDecisionEvent).count() == 0
    assert db.query(ExposureRenderEvent).count() == 0


def test_single_generic_description_overlap_returns_none(db):
    user = _make_user(db, user_id=77, email="revision@x")
    _make_deadline(
        db,
        user.user_id,
        title="CO Final",
        description="AI revision material",
    )
    resp = client.post(
        "/v1/parse/deadline-preview",
        json={"title": "AI revision"},
        headers=auth_headers(user.user_id),
    )
    body = resp.json()
    assert body["deadline_id"] is None


def test_weak_match_below_threshold_returns_none(db):
    user = _make_user(db, user_id=77, email="weak@x")
    _make_deadline(
        db, user.user_id,
        title="Tax filing",
        description="quarterly returns spreadsheet",
    )
    # Title shares zero meaningful tokens with deadline
    resp = client.post(
        "/v1/parse/deadline-preview",
        json={"title": "buy groceries"},
        headers=auth_headers(user.user_id),
    )
    body = resp.json()
    assert body["deadline_id"] is None


# ── voided_at filter ─────────────────────────────────────────────


def test_voided_deadline_excluded(db):
    user = _make_user(db, user_id=77, email="voided@x")
    _make_deadline(
        db, user.user_id,
        title="BCI Hackathon",
        description="speller backend",
        voided=True,
    )
    resp = client.post(
        "/v1/parse/deadline-preview",
        json={"title": "BCI hackathon prep"},
        headers=auth_headers(user.user_id),
    )
    body = resp.json()
    assert body["deadline_id"] is None


# ── Terminal-state filter ────────────────────────────────────────


@pytest.mark.parametrize("terminal_state", ["completed", "missed", "skipped"])
def test_terminal_state_deadline_excluded(db, terminal_state):
    user = _make_user(db, user_id=77, email=f"{terminal_state}@x")
    _make_deadline(
        db, user.user_id,
        title="BCI Hackathon",
        description="speller backend",
        state=terminal_state,
    )
    resp = client.post(
        "/v1/parse/deadline-preview",
        json={"title": "BCI hackathon prep"},
        headers=auth_headers(user.user_id),
    )
    body = resp.json()
    assert body["deadline_id"] is None


# ── Cross-user isolation ─────────────────────────────────────────


def test_cross_user_invisibility(db):
    user_a = _make_user(db, user_id=77, email="a@x")
    user_b = _make_user(db, user_id=88, email="b@x")
    _make_deadline(
        db, user_a.user_id,
        title="BCI Hackathon",
        description="speller backend",
    )
    # User B previews with text that would match A's deadline
    resp = client.post(
        "/v1/parse/deadline-preview",
        json={"title": "BCI hackathon speller prep"},
        headers=auth_headers(user_b.user_id),
    )
    body = resp.json()
    assert body["deadline_id"] is None
