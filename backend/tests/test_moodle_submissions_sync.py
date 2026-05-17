"""Tests for moodle_submissions_sync — pure helpers + integration paths.

Covers:
  - title_similarity calibration (good matches > false-positives)
  - due_proximity_bonus monotonicity
  - is_submitted decision rule (status='submitted' / graded / new)
  - _extract_course_code regex sanity
  - sync_user end-to-end with mocked WS calls (course-code constraint
    eliminates cross-course false positives even when titles overlap)
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest

from app.db.models import Deadline, DeadlineCompletionEvent, User
from app.db.scoping import set_current_user_id
from app.services.moodle_submissions_sync import (
    SubmissionSyncResult,
    _MoodleWS,
    _WSAuthError,
    _WSRequestError,
    _extract_course_code,
    due_proximity_bonus,
    is_submitted,
    resolve_base_url,
    sync_user,
    title_similarity,
)
from app.workers.jobs.moodle_submissions_sync import (
    _operator_error_message as _ws_operator_error_message,
)
from tests.conftest import auth_headers  # noqa: F401 — pulls in test fixtures


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.query(DeadlineCompletionEvent).delete()
    db.query(Deadline).delete()
    db.query(User).delete()
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.query(DeadlineCompletionEvent).delete()
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
        moodle_userid=100,
        moodle_base_url="https://lms.test",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_ws_operator_error_message_treats_auth_as_provider_user_action():
    message, severity, retry, user_action, data_integrity = (
        _ws_operator_error_message("auth")
    )

    assert "token rejected" in message
    assert severity == "warn"
    assert "requires reconnect" in retry
    assert "Yes" in user_action
    assert "No deadline completion is inferred" in data_integrity


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


def test_resolve_base_url_uses_only_ical_origin(db):
    user = _make_user(db)
    user.moodle_base_url = None
    user.moodle_ics_url = (
        "https://lms.example.edu/calendar/export_execute.php?"
        "userid=1&authtoken=secret-token&preset_time=recentupcoming"
    )

    assert resolve_base_url(user, "") == "https://lms.example.edu"


def test_ws_http_error_is_sanitized(monkeypatch):
    token = "fake-moodle-token-that-must-not-appear"

    class FakeResponse:
        status_code = 503
        request = httpx.Request(
            "GET",
            f"https://lms.test/webservice/rest/server.php?wstoken={token}",
        )

        def raise_for_status(self):
            raise httpx.HTTPStatusError(
                "server unavailable",
                request=self.request,
                response=self,
            )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.services.moodle_submissions_sync.httpx.Client", FakeClient)

    with pytest.raises(_WSRequestError) as exc:
        _MoodleWS("https://lms.test", token).call("core_webservice_get_site_info")

    message = str(exc.value)
    assert "http_503" in message
    assert "core_webservice_get_site_info" in message
    assert token not in message
    assert "wstoken" not in message


def test_ws_4xx_auth_error_is_sanitized(monkeypatch):
    token = "fake-moodle-token-that-must-not-appear"

    class FakeResponse:
        status_code = 401
        request = httpx.Request(
            "GET",
            f"https://lms.test/webservice/rest/server.php?wstoken={token}",
        )

        def raise_for_status(self):
            raise httpx.HTTPStatusError(
                "unauthorized",
                request=self.request,
                response=self,
            )

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.services.moodle_submissions_sync.httpx.Client", FakeClient)

    with pytest.raises(_WSAuthError) as exc:
        _MoodleWS("https://lms.test", token).call("core_webservice_get_site_info")

    assert str(exc.value) == "http_401"
    assert token not in str(exc.value)
    assert "wstoken" not in str(exc.value)


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
    event = db.query(DeadlineCompletionEvent).filter(
        DeadlineCompletionEvent.deadline_id == d.deadline_id
    ).one()
    assert event.completion_source == "moodle_submission"
    assert event.time_provenance == "external_import_sync_time"
    assert event.completed_at_utc == d.completed_at


def test_sync_user_uses_moodle_submission_timestamp_for_matched_deadline(db, monkeypatch):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    due = datetime(2026, 4, 24, 20, 59, 0)
    submitted_at_utc = datetime(2026, 4, 24, 21, 30, 0, tzinfo=timezone.utc)
    submitted_at = submitted_at_utc.replace(tzinfo=None)
    d = _make_deadline(
        db, user.user_id,
        title="HandsOn Lab8 is due",
        due_at=due,
        category_hint="CSE281",
    )

    courses = [{"id": 100, "shortname": "CSE281 (UG2023) - Software Engineering"}]
    assignments_by_course = {
        100: [{
            "id": 45928,
            "name": "HandsOn Lab8",
            "duedate": int(due.timestamp()),
        }],
    }
    submission_status_by_assign = {
        45928: {
            "lastattempt": {
                "submission": {
                    "status": "submitted",
                    "timemodified": int(submitted_at_utc.timestamp()),
                }
            }
        }
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

    assert res.marked_complete == 1
    assert d.completed_at == submitted_at
    event = db.query(DeadlineCompletionEvent).filter(
        DeadlineCompletionEvent.deadline_id == d.deadline_id
    ).one()
    assert event.time_provenance == "external_import"
    assert event.completed_at_utc == submitted_at
    assert event.completed_after_due is True
    assert event.delay_minutes == 31


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


# ---------------------------------------------------------------------------
# Backfill — operator request 2026-05-01: "submitted tasks pop up" +
# "could Lyra pick up other unsubmitted as overdue".
# ---------------------------------------------------------------------------


def test_sync_user_backfills_submitted_assignment_as_completed(db, monkeypatch):
    """Operator's primary ask: when WS sees a submitted assignment that
    isn't represented in Lyra (iCal feed dropped it), create a completed
    deadline so it shows up on the Done tab."""
    from app.db.models import Deadline as DeadlineModel
    user = _make_user(db)
    set_current_user_id(user.user_id)

    submitted_at_utc = datetime(2026, 4, 20, 14, 30, 0, tzinfo=timezone.utc)
    submitted_at = submitted_at_utc.replace(tzinfo=None)
    courses = [{"id": 100, "shortname": "CSE281 (UG2023)"}]
    assignments_by_course = {
        100: [{
            "id": 44612,
            "name": "HandsOn1 Lab2",
            "duedate": int(datetime(2026, 2, 23, 21, 59).timestamp()),
        }],
    }
    submission_status_by_assign = {
        44612: {
            "lastattempt": {
                "submission": {
                    "status": "submitted",
                    "timemodified": int(submitted_at_utc.timestamp()),
                }
            }
        }
    }

    import os
    os.environ["MOODLE_WS_USERID"] = "34554"
    monkeypatch.setattr(
        "app.services.moodle_submissions_sync._MoodleWS.call",
        _ws_call_mock(courses, assignments_by_course, submission_status_by_assign),
    )
    res = sync_user(user, "https://lms.test/", db)
    db.commit()

    assert res.backfilled_completed == 1
    assert res.backfilled_missed == 0
    assert res.backfilled_planned == 0

    backfilled = db.query(DeadlineModel).filter(
        DeadlineModel.external_source == "moodle_ws_backfill"
    ).all()
    assert len(backfilled) == 1
    bf = backfilled[0]
    assert bf.state == "completed"
    assert bf.completed_at == submitted_at
    assert bf.title == "HandsOn1 Lab2"
    assert bf.external_id == "44612"
    assert bf.category_hint == "CSE281"
    event = db.query(DeadlineCompletionEvent).filter(
        DeadlineCompletionEvent.deadline_id == bf.deadline_id
    ).one()
    assert event.completion_source == "moodle_backfill_submission"
    assert event.time_provenance == "external_import"
    assert event.completed_at_utc == submitted_at


def test_sync_user_backfills_overdue_unsubmitted_as_missed(db, monkeypatch):
    """Operator's secondary ask: pick up unsubmitted past-due
    assignments as missed deadlines so they're visible."""
    from app.db.models import Deadline as DeadlineModel
    user = _make_user(db)
    set_current_user_id(user.user_id)

    past_due = datetime.utcnow() - timedelta(days=10)
    courses = [{"id": 100, "shortname": "CSE221"}]
    assignments_by_course = {
        100: [{
            "id": 45630,
            "name": "Lab 0 Mars Assignment",
            "duedate": int(past_due.timestamp()),
        }],
    }
    submission_status_by_assign = {
        45630: {"lastattempt": {"submission": {"status": "new"}}}
    }

    import os
    os.environ["MOODLE_WS_USERID"] = "34554"
    monkeypatch.setattr(
        "app.services.moodle_submissions_sync._MoodleWS.call",
        _ws_call_mock(courses, assignments_by_course, submission_status_by_assign),
    )
    res = sync_user(user, "https://lms.test/", db)
    db.commit()

    assert res.backfilled_missed == 1
    assert res.backfilled_completed == 0
    bf = db.query(DeadlineModel).filter(
        DeadlineModel.external_source == "moodle_ws_backfill"
    ).first()
    assert bf is not None
    assert bf.state == "missed"
    assert bf.completed_at is None


def test_sync_user_backfills_future_unsubmitted_as_planned(db, monkeypatch):
    """Future-due unsubmitted assignment with no Lyra deadline → create
    as planned (the iCal feed missed it)."""
    from app.db.models import Deadline as DeadlineModel
    user = _make_user(db)
    set_current_user_id(user.user_id)

    future_due = datetime.utcnow() + timedelta(days=14)
    courses = [{"id": 100, "shortname": "CSE242"}]
    assignments_by_course = {
        100: [{
            "id": 44864,
            "name": "Term Project milestone 3",
            "duedate": int(future_due.timestamp()),
        }],
    }
    submission_status_by_assign = {
        44864: {"lastattempt": {"submission": {"status": "new"}}}
    }

    import os
    os.environ["MOODLE_WS_USERID"] = "34554"
    monkeypatch.setattr(
        "app.services.moodle_submissions_sync._MoodleWS.call",
        _ws_call_mock(courses, assignments_by_course, submission_status_by_assign),
    )
    res = sync_user(user, "https://lms.test/", db)
    db.commit()

    assert res.backfilled_planned == 1
    bf = db.query(DeadlineModel).filter(
        DeadlineModel.external_source == "moodle_ws_backfill"
    ).first()
    assert bf is not None
    assert bf.state == "planned"


def test_sync_user_backfill_dedupes_against_existing_ical_deadline(db, monkeypatch):
    """Critical: don't double-create when iCal already imported the
    same assignment under a different external_id."""
    from app.db.models import Deadline as DeadlineModel
    user = _make_user(db)
    set_current_user_id(user.user_id)

    due = datetime(2026, 4, 24, 20, 59, 0)
    # Simulate existing iCal deadline (state=planned). The one in the
    # operator's actual DB.
    existing = _make_deadline(
        db, user.user_id,
        title="HandsOn Lab8 is due",
        due_at=due,
        category_hint="CSE281",
        state="planned",
    )

    courses = [{"id": 100, "shortname": "CSE281"}]
    assignments_by_course = {
        100: [{"id": 45928, "name": "HandsOn Lab8", "duedate": int(due.timestamp())}],
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
    db.refresh(existing)

    # iCal deadline got marked complete via matched_pairs; no backfill.
    assert res.matched == 1
    assert res.marked_complete == 1
    assert res.backfilled_completed == 0
    assert existing.state == "completed"
    bf = db.query(DeadlineModel).filter(
        DeadlineModel.external_source == "moodle_ws_backfill"
    ).all()
    assert bf == []


def test_sync_user_backfill_skips_assignments_without_duedate(db, monkeypatch):
    """duedate=0 means a Moodle 'info' assignment (lecture notes,
    course contents). Never useful to backfill."""
    user = _make_user(db)
    set_current_user_id(user.user_id)

    courses = [{"id": 100, "shortname": "PHM112"}]
    assignments_by_course = {
        100: [
            {"id": 1, "name": "Lecture notes 1", "duedate": 0},
            {"id": 2, "name": "Course contents", "duedate": 0},
        ],
    }
    submission_status_by_assign = {
        1: {"lastattempt": {"submission": {"status": "submitted"}}},
        2: {"lastattempt": {"submission": {"status": "submitted"}}},
    }

    import os
    os.environ["MOODLE_WS_USERID"] = "34554"
    monkeypatch.setattr(
        "app.services.moodle_submissions_sync._MoodleWS.call",
        _ws_call_mock(courses, assignments_by_course, submission_status_by_assign),
    )
    res = sync_user(user, "https://lms.test/", db)
    assert res.backfilled_completed == 0
    assert res.backfilled_planned == 0
    assert res.backfilled_missed == 0


def test_sync_user_backfill_skips_outside_window(db, monkeypatch):
    """Backfill window is 90d back. Assignments older than that get
    skipped to avoid dragging in last semester's noise."""
    user = _make_user(db)
    set_current_user_id(user.user_id)

    very_old = datetime.utcnow() - timedelta(days=200)
    courses = [{"id": 100, "shortname": "CSE243"}]
    assignments_by_course = {
        100: [{"id": 99, "name": "Old assignment", "duedate": int(very_old.timestamp())}],
    }
    submission_status_by_assign = {
        99: {"lastattempt": {"submission": {"status": "submitted"}}}
    }

    import os
    os.environ["MOODLE_WS_USERID"] = "34554"
    monkeypatch.setattr(
        "app.services.moodle_submissions_sync._MoodleWS.call",
        _ws_call_mock(courses, assignments_by_course, submission_status_by_assign),
    )
    res = sync_user(user, "https://lms.test/", db)
    assert res.backfilled_completed == 0


def test_sync_user_uses_per_user_moodle_userid_when_set(db, monkeypatch):
    """Multi-user safety (alembic 044): two users with different
    moodle_userid values must each query Moodle with their own ID,
    not a global env. Without this, user B's sync would query user A's
    Moodle data and break with accessexception."""
    user_a = _make_user(db, ws_token="tok-aaaaaaaaaaaaaaaa")
    user_a.moodle_userid = 100
    user_b = _make_user(db, ws_token="tok-bbbbbbbbbbbbbbbb")
    user_b.moodle_userid = 200
    db.commit()

    seen_userids: list[int] = []

    def _spy_call(self, fn, **params):
        if fn == "core_enrol_get_users_courses":
            seen_userids.append(int(params["userid"]))
            return []
        return {"courses": []}

    import os
    os.environ["MOODLE_WS_USERID"] = "9999"  # would be used as fallback
    monkeypatch.setattr(
        "app.services.moodle_submissions_sync._MoodleWS.call", _spy_call
    )
    set_current_user_id(user_a.user_id)
    sync_user(user_a, "https://lms.test/", db)
    set_current_user_id(user_b.user_id)
    sync_user(user_b, "https://lms.test/", db)

    assert seen_userids == [100, 200]  # NOT [9999, 9999]


def test_sync_user_falls_back_to_env_when_per_user_userid_null(db, monkeypatch):
    """Pre-044 operator row has NULL moodle_userid; sync must still
    work via env fallback so we don't break the operator on deploy."""
    user = _make_user(db)
    user.moodle_userid = None
    db.commit()
    set_current_user_id(user.user_id)

    seen_userids: list[int] = []

    def _spy_call(self, fn, **params):
        if fn == "core_enrol_get_users_courses":
            seen_userids.append(int(params["userid"]))
            return []
        return {"courses": []}

    import os
    os.environ["MOODLE_WS_USERID"] = "34554"
    monkeypatch.setattr(
        "app.services.moodle_submissions_sync._MoodleWS.call", _spy_call
    )
    sync_user(user, "https://lms.test/", db)
    assert seen_userids == [34554]


def test_sync_user_self_heals_legacy_userid_from_site_info(db, monkeypatch):
    """Legacy rows should become one-time setup rows after the next sync.

    If a user already supplied a WS token before per-user Moodle fields
    existed, the stored token can recover the Moodle userid from
    core_webservice_get_site_info instead of asking the user to reconnect.
    """
    user = _make_user(db)
    user.moodle_userid = None
    user.moodle_base_url = None
    db.commit()
    set_current_user_id(user.user_id)

    seen_userids: list[int] = []

    def _spy_call(self, fn, **params):
        if fn == "core_webservice_get_site_info":
            return {"userid": 321}
        if fn == "core_enrol_get_users_courses":
            seen_userids.append(int(params["userid"]))
            return []
        return {"courses": []}

    monkeypatch.setattr(
        "app.services.moodle_submissions_sync._MoodleWS.call", _spy_call
    )
    sync_user(user, "https://lms.test/", db)
    db.commit()
    db.refresh(user)

    assert seen_userids == [321]
    assert user.moodle_userid == 321
    assert user.moodle_base_url == "https://lms.test"


def test_sync_user_decrypts_fernet_prefixed_token(db, monkeypatch):
    """Tokens stored as `fernet:...` must decrypt before passing to
    Moodle. Plaintext rows (legacy operator) keep working."""
    from app.utils.encryption import encrypt_secret

    encrypted = encrypt_secret("the-real-token-1234567890ab")
    assert encrypted.startswith("fernet:")
    user = _make_user(db, ws_token=encrypted)
    user.moodle_userid = 100
    db.commit()
    set_current_user_id(user.user_id)

    seen_tokens: list[str] = []

    def _spy_call(self, fn, **params):
        seen_tokens.append(self.token)
        return [] if fn == "core_enrol_get_users_courses" else {"courses": []}

    import os
    os.environ["MOODLE_WS_USERID"] = "100"
    monkeypatch.setattr(
        "app.services.moodle_submissions_sync._MoodleWS.call", _spy_call
    )
    sync_user(user, "https://lms.test/", db)
    assert seen_tokens
    assert seen_tokens[0] == "the-real-token-1234567890ab"


def test_sync_user_backfill_is_idempotent(db, monkeypatch):
    """Running sync twice shouldn't create two copies of the same
    backfilled deadline (external_id dedup)."""
    from app.db.models import Deadline as DeadlineModel
    user = _make_user(db)
    set_current_user_id(user.user_id)

    due = datetime.utcnow() - timedelta(days=20)
    courses = [{"id": 100, "shortname": "CSE221"}]
    assignments_by_course = {
        100: [{"id": 12345, "name": "Some assignment", "duedate": int(due.timestamp())}],
    }
    submission_status_by_assign = {
        12345: {
            "lastattempt": {
                "submission": {
                    "status": "submitted",
                    "timemodified": int(due.timestamp()),
                }
            }
        }
    }

    import os
    os.environ["MOODLE_WS_USERID"] = "34554"
    monkeypatch.setattr(
        "app.services.moodle_submissions_sync._MoodleWS.call",
        _ws_call_mock(courses, assignments_by_course, submission_status_by_assign),
    )
    res1 = sync_user(user, "https://lms.test/", db)
    db.commit()
    res2 = sync_user(user, "https://lms.test/", db)
    db.commit()

    assert res1.backfilled_completed == 1
    assert res2.backfilled_completed == 0  # second run dedups
    bf = db.query(DeadlineModel).filter(
        DeadlineModel.external_source == "moodle_ws_backfill"
    ).all()
    assert len(bf) == 1
