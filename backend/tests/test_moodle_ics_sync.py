"""Tests for the Moodle LMS .ics import path (alembic 041, 2026-04-29).

Two layers of coverage:
  1. Pure parsing — feed bytes into parse_calendar(), assert ParsedEvent
     shapes. Uses the sanitized fixture mirroring real ASU Engineering
     Moodle output (Moodle 3.7, 2019052001.1).
  2. DeadlineManager.upsert_external_deadline contract — keyed upsert
     creates / updates / returns 'unchanged' / skips voided rows.

Plus URL-shape validation + authtoken redaction for logging.

The fixture lives at tests/fixtures/moodle_sample.ics. Real PII /
identifying data scrubbed: course codes ABC101 / DEF202 / GHI303 are
fictional, UIDs use lms.example.test domain.
"""
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.db.models import Deadline, User
from app.db.scoping import set_current_user_id
from app.services import moodle_ics_sync
from app.services.deadline_manager import DeadlineManager
from app.workers.jobs.moodle_ics_sync import _operator_error_message


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "moodle_sample.ics"


def test_operator_error_message_distinguishes_503_from_auth_rotation():
    msg, severity, retry, user_action, data_integrity = _operator_error_message(
        "http_503"
    )
    assert "temporarily unavailable" in msg
    assert "retry" in msg
    assert "Reconnect" not in msg
    assert severity == "warn"
    assert "retry" in retry
    assert "No user action" in user_action
    assert "No mutation" in data_integrity

    auth_msg, severity, retry, user_action, data_integrity = _operator_error_message(
        "http_403"
    )
    assert "Reconnect Moodle" in auth_msg
    assert severity == "warn"
    assert "No retry" in retry
    assert "Yes" in user_action
    assert "future Moodle imports are paused" in data_integrity


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


def _make_user(db) -> User:
    u = User(
        email="moodle-test@example.test",
        google_id=None,
        timezone="Africa/Cairo",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ─── Parsing tests ──────────────────────────────────────────────────────


def test_parse_calendar_yields_three_events_from_fixture():
    body = FIXTURE_PATH.read_bytes()
    events = list(moodle_ics_sync.parse_calendar(body))
    assert len(events) == 3


def test_parse_calendar_extracts_uid_and_summary():
    body = FIXTURE_PATH.read_bytes()
    events = list(moodle_ics_sync.parse_calendar(body))
    titles = {e.title for e in events}
    uids = {e.external_uid for e in events}
    assert titles == {
        "Lab 8 Submission is due",
        "Project Submission is due",
        "Phase II Final is due",
    }
    assert uids == {
        "10001@lms.example.test",
        "10002@lms.example.test",
        "10003@lms.example.test",
    }


def test_parse_calendar_normalizes_due_at_utc_to_naive():
    body = FIXTURE_PATH.read_bytes()
    events = list(moodle_ics_sync.parse_calendar(body))
    by_uid = {e.external_uid: e for e in events}
    # 20260424T205900Z → 2026-04-24 20:59:00 naive UTC
    assert by_uid["10001@lms.example.test"].due_at_utc == datetime(2026, 4, 24, 20, 59, 0)
    # All due_at_utc must be naive (tzinfo None) per project convention.
    for e in events:
        assert e.due_at_utc.tzinfo is None


def test_parse_calendar_extracts_course_code_from_categories():
    body = FIXTURE_PATH.read_bytes()
    events = list(moodle_ics_sync.parse_calendar(body))
    by_uid = {e.external_uid: e for e in events}
    # Fixture course codes: ABC101, DEF202, GHI303.
    assert by_uid["10001@lms.example.test"].category_hint == "ABC101"
    assert by_uid["10002@lms.example.test"].category_hint == "DEF202"
    assert by_uid["10003@lms.example.test"].category_hint == "GHI303"


def test_parse_calendar_handles_empty_description():
    body = FIXTURE_PATH.read_bytes()
    events = list(moodle_ics_sync.parse_calendar(body))
    by_uid = {e.external_uid: e for e in events}
    # Event 10002 has DESCRIPTION: (empty) in the fixture.
    assert by_uid["10002@lms.example.test"].description is None


def test_parse_calendar_handles_multiline_folded_description():
    body = FIXTURE_PATH.read_bytes()
    events = list(moodle_ics_sync.parse_calendar(body))
    by_uid = {e.external_uid: e for e in events}
    # Event 10003 has a multi-line folded DESCRIPTION in the fixture.
    desc = by_uid["10003@lms.example.test"].description
    assert desc is not None
    assert "Final project submission" in desc
    # icalendar lib unfolds + unescapes — both should be applied.
    assert "\\n" not in desc  # escape sequences should be unescaped
    assert "team member" in desc


def test_parse_calendar_skips_rrule_events():
    """Recurring lecture schedules (RRULE) are not deadlines — skip."""
    ical = b"""BEGIN:VCALENDAR
PRODID:-//Test//EN
VERSION:2.0
BEGIN:VEVENT
UID:rec-1@example.test
SUMMARY:Weekly Lecture
DTSTART:20260501T100000Z
DTEND:20260501T120000Z
RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=10
END:VEVENT
END:VCALENDAR
"""
    events = list(moodle_ics_sync.parse_calendar(ical))
    assert events == []


def test_parse_calendar_skips_all_day_events():
    """All-day events (DATE not DATE-TIME) lack deadline-time precision."""
    ical = b"""BEGIN:VCALENDAR
PRODID:-//Test//EN
VERSION:2.0
BEGIN:VEVENT
UID:allday-1@example.test
SUMMARY:Holiday
DTSTART;VALUE=DATE:20260501
DTEND;VALUE=DATE:20260502
END:VEVENT
END:VCALENDAR
"""
    events = list(moodle_ics_sync.parse_calendar(ical))
    assert events == []


def test_parse_calendar_skips_event_missing_dtstart():
    """An event without DTSTART can't anchor a deadline — skip."""
    ical = b"""BEGIN:VCALENDAR
PRODID:-//Test//EN
VERSION:2.0
BEGIN:VEVENT
UID:no-dtstart@example.test
SUMMARY:Mystery Event
END:VEVENT
END:VCALENDAR
"""
    events = list(moodle_ics_sync.parse_calendar(ical))
    assert events == []


def test_parse_calendar_skips_event_missing_summary():
    """An event without SUMMARY would render as a blank deadline — skip."""
    ical = b"""BEGIN:VCALENDAR
PRODID:-//Test//EN
VERSION:2.0
BEGIN:VEVENT
UID:no-summary@example.test
DTSTART:20260501T100000Z
END:VEVENT
END:VCALENDAR
"""
    events = list(moodle_ics_sync.parse_calendar(ical))
    assert events == []


# ─── URL shape validation ───────────────────────────────────────────────


def test_validate_url_shape_accepts_well_formed_moodle_url():
    url = (
        "https://lms.example.test/calendar/export_execute.php"
        "?userid=1&authtoken=abcdef&preset_what=all&preset_time=recentupcoming"
    )
    assert moodle_ics_sync.validate_url_shape(url) is None


def test_validate_url_shape_rejects_empty_string():
    assert moodle_ics_sync.validate_url_shape("") == "url_empty"


def test_validate_url_shape_rejects_non_http():
    assert (
        moodle_ics_sync.validate_url_shape("ftp://example.test/foo")
        == "url_not_http"
    )


def test_validate_url_shape_rejects_url_without_export_execute_path():
    assert (
        moodle_ics_sync.validate_url_shape("https://lms.example.test/some/other/page")
        == "url_not_moodle_export"
    )


def test_validate_url_shape_rejects_url_without_authtoken():
    assert (
        moodle_ics_sync.validate_url_shape(
            "https://lms.example.test/calendar/export_execute.php?userid=1"
        )
        == "url_missing_authtoken"
    )


def test_redact_url_masks_the_authtoken():
    url = (
        "https://lms.example.test/calendar/export_execute.php"
        "?userid=1&authtoken=secret123abc&preset_what=all"
    )
    redacted = moodle_ics_sync._redact_url(url)
    assert "secret123abc" not in redacted
    assert "authtoken=•••" in redacted
    # Other parts of the URL are preserved.
    assert "userid=1" in redacted
    assert "lms.example.test" in redacted


# ─── upsert_external_deadline contract ──────────────────────────────────


def test_upsert_external_deadline_creates_new_row(db):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    manager = DeadlineManager(db)

    op = manager.upsert_external_deadline(
        external_source="moodle_ics",
        external_id="evt-1@lms.example.test",
        title="Lab 1 is due",
        due_at_utc=datetime(2026, 5, 10, 23, 59, 0),
        description="First lab.",
        category_hint="CSE101",
    )
    assert op == "created"

    # One row visible, with external_* populated.
    rows = db.query(Deadline).filter(Deadline.user_id == user.user_id).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.external_source == "moodle_ics"
    assert row.external_id == "evt-1@lms.example.test"
    assert row.title == "Lab 1 is due"
    assert row.imported_at is not None
    assert row.state == "planned"


def test_upsert_external_deadline_unchanged_on_no_diff(db):
    user = _make_user(db)
    set_current_user_id(user.user_id)
    manager = DeadlineManager(db)

    common = dict(
        external_source="moodle_ics",
        external_id="evt-2@lms.example.test",
        title="Lab 2 is due",
        due_at_utc=datetime(2026, 5, 12, 10, 0, 0),
        description="Second lab.",
        category_hint="CSE101",
    )
    assert manager.upsert_external_deadline(**common) == "created"
    # Re-running with identical fields → unchanged.
    assert manager.upsert_external_deadline(**common) == "unchanged"

    # Still exactly one row.
    assert db.query(Deadline).filter(Deadline.user_id == user.user_id).count() == 1


def test_upsert_external_deadline_updates_on_due_at_change(db):
    """Moodle deadline extension is the canonical change case."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    manager = DeadlineManager(db)

    base = dict(
        external_source="moodle_ics",
        external_id="evt-3@lms.example.test",
        title="Project is due",
        description=None,
        category_hint="CSE201",
    )
    manager.upsert_external_deadline(
        **base, due_at_utc=datetime(2026, 5, 15, 23, 59, 0),
    )
    op = manager.upsert_external_deadline(
        **base, due_at_utc=datetime(2026, 5, 22, 23, 59, 0),  # extended a week
    )
    assert op == "updated"

    row = (
        db.query(Deadline)
        .filter(
            Deadline.user_id == user.user_id,
            Deadline.external_id == "evt-3@lms.example.test",
        )
        .first()
    )
    assert row.due_at_utc == datetime(2026, 5, 22, 23, 59, 0)
    # imported_at is the FIRST-import timestamp; not overwritten on updates.
    assert row.imported_at <= row.due_at_utc


def test_upsert_external_deadline_skips_voided_rows(db):
    """User explicitly voided imported deadline → don't resurrect."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    manager = DeadlineManager(db)

    common = dict(
        external_source="moodle_ics",
        external_id="evt-4@lms.example.test",
        title="Quiz is due",
        due_at_utc=datetime(2026, 5, 20, 12, 0, 0),
        description=None,
        category_hint="MATH101",
    )
    manager.upsert_external_deadline(**common)
    # User voids it.
    row = (
        db.query(Deadline)
        .filter(Deadline.external_id == "evt-4@lms.example.test")
        .first()
    )
    row.voided_at = datetime.utcnow()
    db.commit()

    # Next sync sees the same event again.
    op = manager.upsert_external_deadline(**common)
    assert op == "skipped_voided"

    # Row is still voided, not resurrected.
    refreshed = (
        db.query(Deadline)
        .filter(Deadline.external_id == "evt-4@lms.example.test")
        .first()
    )
    assert refreshed.voided_at is not None


def test_upsert_external_deadline_isolates_users(db):
    """Different users may have the same external_id (different Moodle accounts)."""
    user_a = _make_user(db)
    user_b = User(
        email="other-user@example.test",
        google_id=None,
        timezone="Africa/Cairo",
    )
    db.add(user_b)
    db.commit()
    db.refresh(user_b)

    common = dict(
        external_source="moodle_ics",
        external_id="evt-shared@lms.example.test",
        title="Shared assignment",
        due_at_utc=datetime(2026, 5, 25, 23, 59, 0),
        description=None,
        category_hint="ENG101",
    )

    set_current_user_id(user_a.user_id)
    op_a = DeadlineManager(db).upsert_external_deadline(**common)
    set_current_user_id(user_b.user_id)
    op_b = DeadlineManager(db).upsert_external_deadline(**common)

    assert op_a == "created"
    assert op_b == "created"
    # Clear scope so the count is across all users, not just user_b.
    set_current_user_id(None)
    assert db.query(Deadline).count() == 2
