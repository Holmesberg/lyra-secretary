"""Phase G — parser Pass 2 keyword-overlap deadline-binding tests.

Two layers tested:
1. `infer_deadline_binding(title, candidates)` — pure function unit tests.
2. End-to-end via TaskManager.create_task — when deadline_id is None,
   Pass 2 fires and binds the task with deadline_match_source='parser_auto'.

Stoplist behavior, threshold, tie-breaking, and the asymmetric ratio
(over task_tokens) are all covered.
"""
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import MagicMock

import pytest

from app.db.models import Deadline, Task, TaskState, User
from app.db.scoping import set_current_user_id
from app.services.parser import (
    infer_deadline_binding,
    _tokenize_for_binding,
)
from app.services.task_manager import TaskManager


# ── Pure-function unit tests ─────────────────────────────────────


def _fake_deadline(title, description=None, due_at=None):
    """Build a minimal mock Deadline for unit tests."""
    d = MagicMock()
    d.title = title
    d.description = description
    d.due_at_utc = due_at or datetime(2026, 6, 1)
    d.deadline_id = str(uuid4())
    return d


def test_tokenize_strips_stoplist():
    tokens = _tokenize_for_binding("the BCI hackathon today")
    assert "bci" in tokens
    assert "hackathon" in tokens
    # 'the' and 'today' are stop-listed
    assert "the" not in tokens
    assert "today" not in tokens


def test_tokenize_strips_short_tokens():
    tokens = _tokenize_for_binding("AI is fun")
    # 'ai' is 2 chars → dropped (len ≥ 3 required)
    assert "ai" not in tokens
    assert "fun" in tokens


def test_no_match_returns_none():
    deadlines = [_fake_deadline("BCI Hackathon", "build speller backend")]
    result = infer_deadline_binding("buy groceries", deadlines)
    assert result is None


def test_full_overlap_matches():
    deadlines = [_fake_deadline("BCI Hackathon", "build speller backend")]
    # Task title fully contained: 'speller backend' ⊆ deadline tokens
    result = infer_deadline_binding("write speller backend tests", deadlines)
    assert result is not None
    deadline, confidence = result
    assert confidence >= 0.5


def test_partial_overlap_above_threshold():
    deadlines = [_fake_deadline("BCI Hackathon", "build speller backend")]
    # Task tokens: {bci, code} (len 2), shared: {bci} → ratio 0.5
    result = infer_deadline_binding("BCI code", deadlines)
    assert result is not None
    _, confidence = result
    assert confidence == 0.5


def test_below_threshold_no_match():
    deadlines = [_fake_deadline("BCI Hackathon", "build speller backend")]
    # Task tokens: {gym, workout, evening, bci} after stoplist
    # Wait — "evening" is in stoplist. Tokens: {gym, workout, bci}
    # Shared with deadline: {bci} → ratio = 1/3 = 0.33 (< 0.5)
    result = infer_deadline_binding("gym workout BCI", deadlines)
    assert result is None


def test_picks_best_when_multiple_match():
    a = _fake_deadline("BCI Hackathon", "build speller", due_at=datetime(2026, 6, 1))
    b = _fake_deadline("Speller Demo", "demo speller backend", due_at=datetime(2026, 7, 1))

    # Task: "speller backend" (2 tokens). Both match.
    # vs A tokens: {bci, hackathon, build, speller}; shared: {speller}; ratio 1/2 = 0.5
    # vs B tokens: {speller, demo, backend}; shared: {speller, backend}; ratio 2/2 = 1.0
    # B wins on higher ratio
    result = infer_deadline_binding("speller backend", [a, b])
    assert result is not None
    deadline, confidence = result
    assert deadline.title == "Speller Demo"
    assert confidence == 1.0


def test_tie_breaks_on_earliest_due_at():
    earlier = _fake_deadline("BCI write postmortem", due_at=datetime(2026, 6, 1))
    later = _fake_deadline("BCI write postmortem", due_at=datetime(2026, 7, 1))

    # Task: "write postmortem" → both match equally
    result = infer_deadline_binding("write postmortem", [earlier, later])
    assert result is not None
    deadline, _ = result
    # Earlier due_at_utc wins on tie
    assert deadline.due_at_utc == datetime(2026, 6, 1)


def test_empty_task_title_no_match():
    deadlines = [_fake_deadline("BCI", "speller")]
    assert infer_deadline_binding("", deadlines) is None
    # All-stoplist title also yields no tokens → no match
    assert infer_deadline_binding("the a today", deadlines) is None


def test_empty_candidates_no_match():
    assert infer_deadline_binding("BCI work", []) is None


# ── Integration via TaskManager.create_task ──────────────────────


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


def _make_user(db, email: str) -> User:
    u = User(
        email=email,
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


def test_pass2_binds_with_parser_auto_source(db):
    user = _make_user(db, "g1@example.com")
    set_current_user_id(user.user_id)

    deadline = Deadline(
        deadline_id=str(uuid4()),
        user_id=user.user_id,
        title="BCI Hackathon submission",
        description="speller backend, test bench",
        due_at_utc=datetime.utcnow() + timedelta(days=7),
        state="planned",
    )
    db.add(deadline)
    db.commit()
    db.refresh(deadline)

    tm = TaskManager(db)
    start = datetime.utcnow() + timedelta(hours=24)
    task, _, _ = tm.create_task(
        title="write speller backend tests",
        start=start,
        end=start + timedelta(hours=1),
    )
    assert task is not None
    assert task.deadline_id == deadline.deadline_id
    assert task.deadline_match_source == "parser_auto"
    # Confidence is the overlap ratio (between 0 and 1)
    assert 0.5 <= task.deadline_match_confidence <= 1.0


def test_pass2_does_not_bind_when_no_overlap(db):
    user = _make_user(db, "g2@example.com")
    set_current_user_id(user.user_id)

    deadline = Deadline(
        deadline_id=str(uuid4()),
        user_id=user.user_id,
        title="BCI Hackathon",
        description="speller backend",
        due_at_utc=datetime.utcnow() + timedelta(days=7),
        state="planned",
    )
    db.add(deadline)
    db.commit()

    tm = TaskManager(db)
    start = datetime.utcnow() + timedelta(hours=24)
    task, _, _ = tm.create_task(
        title="buy groceries",
        start=start,
        end=start + timedelta(hours=1),
    )
    assert task is not None
    assert task.deadline_id is None
    assert task.deadline_match_source is None


def test_pass2_skips_voided_deadlines(db):
    user = _make_user(db, "g3@example.com")
    set_current_user_id(user.user_id)

    deadline = Deadline(
        deadline_id=str(uuid4()),
        user_id=user.user_id,
        title="BCI Hackathon",
        due_at_utc=datetime.utcnow() + timedelta(days=7),
        state="active",
        voided_at=datetime.utcnow(),
    )
    db.add(deadline)
    db.commit()

    tm = TaskManager(db)
    start = datetime.utcnow() + timedelta(hours=24)
    task, _, _ = tm.create_task(
        title="BCI work",
        start=start,
        end=start + timedelta(hours=1),
    )
    assert task is not None
    assert task.deadline_id is None  # voided deadline excluded


def test_pass2_skips_terminal_deadlines(db):
    user = _make_user(db, "g4@example.com")
    set_current_user_id(user.user_id)

    deadline = Deadline(
        deadline_id=str(uuid4()),
        user_id=user.user_id,
        title="BCI Hackathon",
        due_at_utc=datetime.utcnow() + timedelta(days=7),
        state="completed",  # terminal
    )
    db.add(deadline)
    db.commit()

    tm = TaskManager(db)
    start = datetime.utcnow() + timedelta(hours=24)
    task, _, _ = tm.create_task(
        title="BCI work",
        start=start,
        end=start + timedelta(hours=1),
    )
    assert task is not None
    assert task.deadline_id is None  # state=completed not in {planned, active}


def test_explicit_deadline_id_overrides_pass2(db):
    """When deadline_id is provided, Pass 1 fires; Pass 2 doesn't run."""
    user = _make_user(db, "g5@example.com")
    set_current_user_id(user.user_id)

    bci = Deadline(
        deadline_id=str(uuid4()),
        user_id=user.user_id,
        title="BCI Hackathon",
        description="speller backend",
        due_at_utc=datetime.utcnow() + timedelta(days=7),
        state="planned",
    )
    other = Deadline(
        deadline_id=str(uuid4()),
        user_id=user.user_id,
        title="Different deadline",
        due_at_utc=datetime.utcnow() + timedelta(days=14),
        state="planned",
    )
    db.add_all([bci, other])
    db.commit()

    tm = TaskManager(db)
    start = datetime.utcnow() + timedelta(hours=24)
    # Task title strongly overlaps with BCI; explicit binding to 'other'.
    task, _, _ = tm.create_task(
        title="speller backend tests",
        start=start,
        end=start + timedelta(hours=1),
        deadline_id=other.deadline_id,
    )
    assert task is not None
    # Pass 1 wins — explicit binding to 'other', NOT inferred BCI.
    assert task.deadline_id == other.deadline_id
    assert task.deadline_match_source == "user_explicit"
    assert task.deadline_match_confidence == 1.0


def test_pass2_does_not_bind_across_users(db):
    """Deadlines belonging to other users are invisible to Pass 2."""
    alice = _make_user(db, "g-alice@example.com")
    bob = _make_user(db, "g-bob@example.com")

    set_current_user_id(alice.user_id)
    alice_deadline = Deadline(
        deadline_id=str(uuid4()),
        user_id=alice.user_id,
        title="BCI Hackathon",
        description="speller backend",
        due_at_utc=datetime.utcnow() + timedelta(days=7),
        state="planned",
    )
    db.add(alice_deadline)
    db.commit()

    # Bob creates a task with overlapping title — should NOT bind to Alice's deadline
    set_current_user_id(bob.user_id)
    tm = TaskManager(db)
    start = datetime.utcnow() + timedelta(hours=24)
    task, _, _ = tm.create_task(
        title="speller backend work",
        start=start,
        end=start + timedelta(hours=1),
    )
    assert task is not None
    assert task.deadline_id is None  # cross-user invisibility holds
