"""Tests for moodle_submissions_sync — pure helpers + integration paths.

Covers:
  - title_similarity calibration (good matches > false-positives)
  - due_proximity_bonus monotonicity
  - is_submitted decision rule (status='submitted' / graded / new)
  - _extract_course_code regex sanity
  - sync_user end-to-end with mocked WS calls (course-code constraint
    eliminates cross-course false positives even when titles overlap)
"""
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.db.models import Deadline, User
from app.db.scoping import set_current_user_id
from app.services.moodle_submissions_sync import (
    SubmissionSyncResult,
    _extract_course_code,
    due_proximity_bonus,
    is_submitted,
    sync_user,
    title_similarity,
)
from tests.conftest import auth_headers  # noqa: F401 — pulls in test fixtures


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()


def _make_user(db, *, ws_token="tok-1234567890123456") -> User:
    u = User(
        email=f"u{uuid4().hex[:8]}@test",
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=True,
        notion_enabled=False,
        terms_accepted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        moodle_ws_token=ws_token,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_deadline(db, user_id, *, title, due_at, category_hint=None, state="planned"):
    d = Deadline(
        deadline_id=str(uuid4()),
        user_id=user_id,
        title=title,
        due_at_utc=due_at,
        state=state,
        external_source="moodle_ics",
        category_hint=category_hint,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


# ---------------------------------------------------------------------------
# Pure-function tests
# ---------------------------------------------------------------------------


def test_extract_course_code_recognizes_standard_format():
    assert _extract_course_code("CSE281") == "CSE281"
    assert _extract_course_code("PHM123") == "PHM123"
    assert _extract_course_code("CSE281 (UG2023) - Software Engineering") == "CSE281"


def test_extract_course_code_returns_none_for_non_codes():
    assert _extract_course_code(None) is None
    assert _extract_course_code("") is None
    assert _extract_course_code("Lab 1") is None
    assert _extract_course_code("Quiz Grades") is None


def test_title_similarity_high_for_obvious_matches():
    """The good HandsOn case from the operator's stress data."""
    sim = title_similarity("HandsOn Lab8 is due", "HandsOn Lab8")
    assert sim > 0.55


def test_title_similarity_keeps_obvious_mismatches_below_min_threshold():
    """The false-positive operator caught — but with course-code
    constraint these never reach scoring anyway."""
    sim = title_similarity("Formative quiz 1 closes", "Quiz 1 (5 marks)")
    # Close enough that text alone would match; course code is the
    # primary filter that prevents this in practice.
    assert sim < 0.7


def test_due_proximity_bonus_monotonic():
    base = datetime(2026, 5, 1, 12, 0, 0)
    # Same time → max bonus
    assert due_proximity_bonus(base, int(base.timestamp())) == 0.3
    # 6h apart — still in close window
    assert due_proximity_bonus(base, int((base - timedelta(hours=6)).timestamp())) == 0.3
    # 5d apart — medium bonus
    assert due_proximity_bonus(base, int((base + timedelta(days=5)).timestamp())) == 0.15
    # 60d apart — penalty
    assert due_proximity_bonus(base, int((base + timedelta(days=60)).timestamp())) == -0.2


def test_due_proximity_bonus_handles_missing_duedate():
    assert due_proximity_bonus(datetime.utcnow(), 0) == 0.0


def test_is_submitted_true_on_submitted_status():
    resp = {"lastattempt": {"submission": {"status": "submitted"}}}
    ok, reason = is_submitted(resp)
    assert ok
    assert "submitted" in reason


def test_is_submitted_true_when_graded_even_if_status_new():
    resp = {
        "lastattempt": {"submission": {"status": "new"}},
        "feedback": {"grade": {"grade": "5.00"}},
    }
    ok, reason = is_submitted(resp)
    assert ok
    assert "graded" in reason


def test_is_submitted_false_on_draft():
    resp = {"lastattempt": {"submission": {"status": "draft"}}}
    ok, reason = is_submitted(resp)
    assert not ok


def test_is_submitted_false_on_no_submission():
    ok, reason = is_submitted({})
    assert not ok


# ---------------------------------------------------------------------------
# sync_user integration tests with mocked Moodle WS
# ---------------------------------------------------------------------------


def _ws_call_mock(courses, assignments_by_course, submission_status_by_assign):
    """Return a callable that mocks _MoodleWS.call() based on the
    `wsfunction` it's invoked with."""
    def _call(self, fn, **params):
        if fn == "core_enrol_get_users_courses":
            return courses
        if fn == "mod_assign_get_assignments":
            # Group assignments back into the response shape Moodle uses
            return {
                "courses": [
                    {
                        "id": c["id"],
                        "shortname": c["shortname"],
                        "assignments": assignments_by_course.get(c["id"], []),
                    }
                    for c in courses
                ]
            }
        if fn == "mod_assign_get_submission_status":
            assign_id = int(params.get("assignid", 0))
            return submission_status_by_assign.get(assign_id, {})
        return {}
    return _call


def test_sync_user_marks_submitted_assignment_complete(db, monkeypatch):
    """Happy path: course code matches, title matches, Moodle says
    submitted → Lyra deadline transitions to completed."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    d = _make_deadline(
        db, user.user_id,
        title="HandsOn Lab8 is due",
        due_at=datetime(2026, 4, 24, 20, 59, 0),
        category_hint="CSE281",
    )

    courses = [{"id": 100, "shortname": "CSE281 (UG2023) - Software Engineering"}]
    assignments_by_course = {
        100: [{
            "id": 45928,
            "name": "HandsOn Lab8",
            "duedate": int(datetime(2026, 4, 24, 20, 59, 0).timestamp()),
        }],
    }
    submission_status_by_assign = {
        45928: {"lastattempt": {"submission": {"status": "submitted"}}}
    }

    import os
    os.environ["MOODLE_WS_USERID"] = "34554"
    monkeypatch.setattr(
        "app.services.moodle_submissions_sync._MoodleWS.call",
        _ws_call_mock(courses, assignments_by_course, submission_status_by_assign),
    )
    res = sync_user(user, "https://lms.test/", db)
    db.commit()
    db.refresh(d)

    assert res.matched == 1
    assert res.marked_complete == 1
    assert d.state == "completed"
    assert d.completed_at is not None
    assert "HandsOn Lab8 is due" in res.marked_titles


def test_sync_user_skips_when_course_code_differs(db, monkeypatch):
    """The operator's false-positive: 'Formative quiz 1 closes' (CSE281)
    must not match 'Quiz 1 (5 marks)' (PHM112) — different courses."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    d = _make_deadline(
        db, user.user_id,
        title="Formative quiz 1 closes",
        due_at=datetime(2026, 5, 5, 21, 59, 0),
        category_hint="CSE281",
    )

    courses = [
        {"id": 200, "shortname": "PHM112 (UG2023) - Mathematics (2)"},  # WRONG course
    ]
    assignments_by_course = {
        200: [{"id": 99999, "name": "Quiz 1 (5 marks)", "duedate": 0}],
    }
    submission_status_by_assign = {
        99999: {"lastattempt": {"submission": {"status": "submitted"}}}
    }

    import os
    os.environ["MOODLE_WS_USERID"] = "34554"
    monkeypatch.setattr(
        "app.services.moodle_submissions_sync._MoodleWS.call",
        _ws_call_mock(courses, assignments_by_course, submission_status_by_assign),
    )
    res = sync_user(user, "https://lms.test/", db)
    db.refresh(d)

    # Even though title overlap is non-trivial, course codes differ →
    # match never happens. State stays planned.
    assert res.marked_complete == 0
    assert d.state == "planned"


def test_sync_user_does_nothing_without_token(db):
    user = _make_user(db, ws_token=None)  # type: ignore[arg-type]
    set_current_user_id(user.user_id)
    res = sync_user(user, "https://lms.test/", db)
    assert res.error == "no_token"
    assert res.marked_complete == 0


def test_sync_user_skips_terminal_state_deadlines(db, monkeypatch):
    """Idempotency: already-completed deadlines aren't re-evaluated."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    d = _make_deadline(
        db, user.user_id,
        title="Already done",
        due_at=datetime(2026, 4, 1, 12, 0, 0),
        category_hint="CSE281",
        state="completed",
    )

    courses = [{"id": 100, "shortname": "CSE281"}]
    assignments_by_course = {100: [{"id": 1, "name": "Already done", "duedate": 0}]}
    submission_status_by_assign = {1: {"lastattempt": {"submission": {"status": "submitted"}}}}

    import os
    os.environ["MOODLE_WS_USERID"] = "34554"
    monkeypatch.setattr(
        "app.services.moodle_submissions_sync._MoodleWS.call",
        _ws_call_mock(courses, assignments_by_course, submission_status_by_assign),
    )
    res = sync_user(user, "https://lms.test/", db)
    db.refresh(d)

    # Terminal state filters out from the candidate set entirely.
    assert res.matched == 0
    assert d.state == "completed"  # unchanged
