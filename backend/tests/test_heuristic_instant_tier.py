"""Heuristic-populates-llm_deadline_candidates instant-tier tests (2026-04-28).

When the heuristic produces candidates at create-time, those candidates
populate `task.llm_deadline_candidates` synchronously so the chip can
fire Tier 1/2/3 INSTANTLY rather than waiting for the 5-9s async LLM.

Operator directive (2026-04-28): "ensure tasks are deadline aware,
with tiers we discussed."
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import Deadline, Task, User
from app.db.scoping import set_current_user_id
from app.services.task_manager import TaskManager


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


def _make_user(db) -> User:
    u = User(
        email=f"u{uuid4().hex[:8]}@test",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_deadline(db, user_id: int, title: str) -> Deadline:
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


def _args(title: str, description: str = None) -> dict:
    start = datetime.utcnow() + timedelta(hours=24)
    return dict(
        title=title,
        start=start,
        end=start + timedelta(hours=1),
        description=description,
    )


def test_heuristic_high_confidence_stays_suggestion_only(db):
    """Exact-title match clears suggestion guardrails, but canonical
    binding still requires explicit user confirmation."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    bci = _make_deadline(db, user.user_id, "BCI Paper")
    _make_deadline(db, user.user_id, "Spring School")

    task, _, _ = TaskManager(db).create_task(
        **_args("BCI Paper writeup intro")
    )
    assert task is not None
    assert task.deadline_id is None
    assert task.deadline_match_source is None
    # Candidates pre-populated for the explicit confirmation chip.
    assert task.llm_deadline_candidates is not None
    assert len(task.llm_deadline_candidates) >= 1
    assert task.llm_inferred_deadline_id == bci.deadline_id


def test_heuristic_multi_competitive_populates_candidates_no_bind(db):
    """When multi-competitive guardrail blocks auto-bind, candidates
    still populate synchronously so the chip fires Tier 2 instantly."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    paper_a = _make_deadline(db, user.user_id, "Paper Draft")
    paper_b = _make_deadline(db, user.user_id, "Paper Review")

    # "Paper" alone matches both as substring → multi-competitive
    task, _, _ = TaskManager(db).create_task(**_args("Paper"))

    assert task is not None
    # No canonical bind from heuristic
    assert task.deadline_match_source != "heuristic_exact_title"
    assert task.deadline_match_source != "heuristic_startswith"
    assert task.deadline_match_source != "heuristic_substring"
    # But candidates ARE populated (instant-tier path)
    assert task.llm_deadline_candidates is not None
    assert len(task.llm_deadline_candidates) >= 1
    # Confidence reflects heuristic's top score
    assert task.llm_deadline_match_confidence is not None
    assert task.llm_inferred_deadline_id in (paper_a.deadline_id, paper_b.deadline_id)
    # Status stays 'pending' — LLM may still refine later
    assert task.llm_parse_status == "pending"


def test_no_deadlines_no_candidates(db):
    """When user has no deadlines, no candidates, no chip data."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    task, _, _ = TaskManager(db).create_task(**_args("Anything"))
    assert task is not None
    assert task.llm_deadline_candidates is None
    assert task.llm_inferred_deadline_id is None


def test_explicit_deadline_id_skips_heuristic_population(db):
    """When user passes explicit deadline_id, candidates are NOT
    pre-populated (chip would suppress via user_explicit guard anyway)."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    bci = _make_deadline(db, user.user_id, "BCI Paper")
    _make_deadline(db, user.user_id, "Spring School")

    task, _, _ = TaskManager(db).create_task(
        **_args("BCI Paper writeup", description=None),
        deadline_id=bci.deadline_id,
    )
    assert task is not None
    assert task.deadline_id == bci.deadline_id
    assert task.deadline_match_source == "user_explicit"
    # No candidates — user's explicit choice is the answer
    assert task.llm_deadline_candidates is None


def test_candidate_shape_matches_chip_expectation(db):
    """Each candidate JSON object has deadline_id + title + confidence
    keys — matches LlmDeadlineCandidate type the chip uses."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    _make_deadline(db, user.user_id, "Paper Draft")
    _make_deadline(db, user.user_id, "Paper Review")

    task, _, _ = TaskManager(db).create_task(**_args("Paper"))
    assert task.llm_deadline_candidates is not None
    for c in task.llm_deadline_candidates:
        assert set(c.keys()) == {"deadline_id", "title", "confidence"}
        assert isinstance(c["confidence"], (int, float))
