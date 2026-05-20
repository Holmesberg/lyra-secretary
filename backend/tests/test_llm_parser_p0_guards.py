"""P0 stress-test guards on the LLM enrichment service (2026-04-28).

Two integrity guards, both shipped in the W1-frontend commit:

1. **voided_at race guard** — `enrich_task_via_llm` re-fetches the task with
   `voided_at IS NULL`. If the task was voided between the worker's SELECT
   and the per-task call, enrichment must NOT write to the soft-deleted
   row (silent audit-trail contamination).

2. **deadline_match_source guard** — when the user has already taken
   ownership of the binding (`deadline_match_source` ∈ {`'user_explicit'`,
   `'user_corrected'`, `'llm_auto_confirmed'`}), enrichment writes
   audit-trail fields only and leaves the deadline columns alone. User
   intent always wins over async LLM.

The Ollama HTTP call is monkeypatched out — these tests verify the guards,
not the LLM itself.
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import Deadline, Task, TaskState, User
from app.db.scoping import set_current_user_id
from app.services import llm_parser


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.query(Task).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
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
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_task(db, user_id: int, **kwargs) -> Task:
    now = datetime.utcnow()
    defaults = dict(
        task_id=str(uuid4()),
        user_id=user_id,
        title="Test task",
        description="- one\n- two",
        category="work",
        planned_start_utc=now + timedelta(hours=1),
        planned_end_utc=now + timedelta(hours=2),
        planned_duration_minutes=60,
        state=TaskState.PLANNED,
        source="manual",
        created_at=now,
        last_modified_at=now,
        llm_parse_status="pending",
    )
    defaults.update(kwargs)
    t = Task(**defaults)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _make_deadline(db, user_id: int, title: str = "BCI paper") -> Deadline:
    d = Deadline(
        deadline_id=str(uuid4()),
        user_id=user_id,
        title=title,
        due_at_utc=datetime.utcnow() + timedelta(days=7),
        state="planned",
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def _stub_ollama(monkeypatch, response: dict):
    """Replace _call_ollama with a fixed response.

    Also disables NIM (post-2026-04-30 swap) so the Ollama path is
    exercised — these tests verify guard logic that's backend-agnostic,
    so stubbing one backend + disabling the other keeps the tests
    deterministic regardless of which LLM is actually configured.
    """
    def fake(prompt: str) -> dict:
        return response
    monkeypatch.setattr(llm_parser, "_call_ollama", fake)
    # Disable NIM so enrich_task_via_llm falls through to Ollama path.
    monkeypatch.setattr(
        "app.services.nvidia_nim_client.is_configured", lambda: False
    )


def test_voided_task_is_skipped_no_writes(db, monkeypatch):
    """Voided-task race guard: if voided_at is set, enrichment returns
    'voided_or_missing' and writes nothing.
    """
    user = _make_user(db)
    task = _make_task(db, user.user_id, voided_at=datetime.utcnow())
    _stub_ollama(monkeypatch, {
        "priority": 2,
        "deadline_name": "anything",
        "sub_items": ["a", "b"],
        "scope_estimate_minutes": 60,
    })

    result = llm_parser.enrich_task_via_llm(db, task.task_id)

    assert result == "voided_or_missing"
    db.refresh(task)
    assert task.llm_parse_status == "pending"  # unchanged
    assert task.llm_priority is None
    assert task.llm_sub_items is None


def test_missing_task_returns_voided_or_missing(db, monkeypatch):
    """Pre-existing 'missing task' path also returns the unified label."""
    _stub_ollama(monkeypatch, {})

    result = llm_parser.enrich_task_via_llm(db, "nonexistent-id")

    assert result == "voided_or_missing"


def test_deadline_write_guard_user_explicit(db, monkeypatch):
    """When deadline_match_source='user_explicit', enrichment populates
    audit-trail columns but does NOT touch deadline-related fields.
    """
    user = _make_user(db)
    deadline = _make_deadline(db, user.user_id)
    task = _make_task(
        db,
        user.user_id,
        deadline_id=deadline.deadline_id,
        deadline_match_source="user_explicit",
        deadline_match_confidence=1.0,
    )
    _stub_ollama(monkeypatch, {
        "priority": 3,
        "deadline_name": "BCI paper",
        "sub_items": ["one", "two"],
        "scope_estimate_minutes": 90,
    })

    result = llm_parser.enrich_task_via_llm(db, task.task_id)

    assert result == "enriched"
    db.refresh(task)
    # Audit fields written
    assert task.llm_parse_status == "enriched"
    assert task.llm_priority == 3
    assert task.llm_sub_items == [
        {"text": "one", "scope_bullet": True},
        {"text": "two", "scope_bullet": True},
    ]
    assert task.llm_parsed_at is not None
    # Deadline-related columns NOT written
    assert task.llm_inferred_deadline_id is None
    assert task.llm_deadline_match_confidence is None
    assert task.llm_deadline_candidates is None
    # Canonical deadline binding untouched
    assert task.deadline_id == deadline.deadline_id
    assert task.deadline_match_source == "user_explicit"


def test_deadline_write_guard_parser_auto_allows_writes(db, monkeypatch):
    """When deadline_match_source IS 'parser_auto', enrichment IS allowed
    to populate the LLM deadline fields (the chip will then ask the user
    to confirm — parser_auto is a soft binding, not user intent).
    """
    user = _make_user(db)
    deadline = _make_deadline(db, user.user_id, title="BCI paper")
    task = _make_task(
        db,
        user.user_id,
        deadline_id=deadline.deadline_id,
        deadline_match_source="parser_auto",
        deadline_match_confidence=0.7,
    )
    _stub_ollama(monkeypatch, {
        "priority": 2,
        "deadline_name": "BCI paper",
        "sub_items": ["one"],
        "scope_estimate_minutes": 60,
    })

    result = llm_parser.enrich_task_via_llm(db, task.task_id)

    assert result == "enriched"
    db.refresh(task)
    # LLM deadline columns populated
    assert task.llm_inferred_deadline_id == deadline.deadline_id
    assert task.llm_deadline_match_confidence is not None
    assert task.llm_deadline_match_confidence > 0
    assert task.llm_deadline_candidates is not None
    assert len(task.llm_deadline_candidates) >= 1
    # Canonical fields untouched (chip handles user accept/reject)
    assert task.deadline_id == deadline.deadline_id
    assert task.deadline_match_source == "parser_auto"


def test_deadline_write_guard_no_existing_binding(db, monkeypatch):
    """When deadline_match_source is None (unbound), enrichment populates
    LLM fields normally.
    """
    user = _make_user(db)
    deadline = _make_deadline(db, user.user_id, title="BCI paper")
    task = _make_task(db, user.user_id)  # no deadline_id, no source
    _stub_ollama(monkeypatch, {
        "priority": 1,
        "deadline_name": "BCI paper",
        "sub_items": [],
        "scope_estimate_minutes": None,
    })

    result = llm_parser.enrich_task_via_llm(db, task.task_id)

    assert result == "enriched"
    db.refresh(task)
    assert task.llm_inferred_deadline_id == deadline.deadline_id
    assert task.deadline_id is None  # never auto-bound by enrichment


def test_llm_deadline_ranker_prefers_matching_academic_acronym(db, monkeypatch):
    """Task-level academic acronyms beat a wrong LLM deadline hint.

    Regression for "AI project revision" surfacing "CO Final" above
    "AI final": short subject tokens are identity, while "final" is generic.
    """
    user = _make_user(db)
    ai = _make_deadline(db, user.user_id, title="AI final")
    co = _make_deadline(db, user.user_id, title="CO Final")
    task = _make_task(db, user.user_id, title="AI project revision")
    _stub_ollama(monkeypatch, {
        "priority": 2,
        "deadline_name": "CO Final",
        "sub_items": [],
        "scope_estimate_minutes": None,
    })

    result = llm_parser.enrich_task_via_llm(db, task.task_id)

    assert result == "enriched"
    db.refresh(task)
    assert task.llm_inferred_deadline_id == ai.deadline_id
    assert task.llm_deadline_candidates is not None
    assert task.llm_deadline_candidates[0]["deadline_id"] == ai.deadline_id
    assert all(c["deadline_id"] != co.deadline_id for c in task.llm_deadline_candidates)


def test_hosted_nim_skipped_for_non_operator_owner(db, monkeypatch):
    """Non-operator task text must not leave the local enrichment boundary."""
    user = _make_user(db, is_operator=False)
    task = _make_task(db, user.user_id)
    monkeypatch.setattr(llm_parser.nvidia_nim_client, "is_configured", lambda: True)

    def fail_nim(_prompt: str) -> dict:
        raise AssertionError("hosted NIM must not be called for non-operator tasks")

    monkeypatch.setattr(llm_parser, "_call_nim", fail_nim)
    monkeypatch.setattr(
        llm_parser,
        "_call_ollama",
        lambda _prompt: {
            "priority": 4,
            "deadline_name": None,
            "sub_items": [],
            "scope_estimate_minutes": None,
        },
    )

    result = llm_parser.enrich_task_via_llm(db, task.task_id)

    assert result == "enriched"
    db.refresh(task)
    assert task.llm_parse_status == "enriched"
    assert task.llm_priority == 4


def test_hosted_nim_allowed_for_operator_owner(db, monkeypatch):
    user = _make_user(db, is_operator=True)
    task = _make_task(db, user.user_id)
    calls = {"nim": 0}
    monkeypatch.setattr(llm_parser.nvidia_nim_client, "is_configured", lambda: True)

    def fake_nim(_prompt: str) -> dict:
        calls["nim"] += 1
        return {
            "priority": 2,
            "deadline_name": None,
            "sub_items": ["operator item"],
            "scope_estimate_minutes": 45,
        }

    monkeypatch.setattr(llm_parser, "_call_nim", fake_nim)
    monkeypatch.setattr(
        llm_parser,
        "_call_ollama",
        lambda _prompt: (_ for _ in ()).throw(
            AssertionError("Ollama should not run after a successful NIM call")
        ),
    )

    result = llm_parser.enrich_task_via_llm(db, task.task_id)

    assert result == "enriched"
    assert calls["nim"] == 1
    db.refresh(task)
    assert task.llm_priority == 2
