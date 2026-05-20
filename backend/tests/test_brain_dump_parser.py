"""Tests for the brain-dump heuristic parser (2026-04-28).

Pure-function tests — no DB. Covers the segmentation rules, kind
classification, date extraction, default scheduling, and the
heuristic→tier binding round-trip. The endpoint layer is tested in
test_brain_dump_endpoint.py.
"""
from datetime import datetime, timedelta

from app.services.brain_dump_parser import parse_brain_dump


# Anchor "now" used by all tests — Wednesday 10:00 AM. Picking a
# weekday lets us exercise "Friday" / "tomorrow" relative parsing
# without ambiguity on whether tomorrow is a weekend.
NOW_LOCAL = datetime(2026, 4, 29, 10, 0, 0)
NOW_ISO = NOW_LOCAL.isoformat()


def test_empty_input_returns_empty_status():
    res = parse_brain_dump("", NOW_ISO)
    assert res.parser_status == "empty"
    assert res.items == []
    assert res.bindings == []


def test_whitespace_only_returns_empty_status():
    res = parse_brain_dump("   \n  \t \n", NOW_ISO)
    assert res.parser_status == "empty"
    assert res.items == []


def test_splits_on_newlines():
    raw = "read chapter 3\nwrite essay\nstudy for midterm"
    res = parse_brain_dump(raw, NOW_ISO)
    assert len(res.items) == 3
    titles = [i.title.lower() for i in res.items]
    assert "read chapter 3" in titles
    assert "write essay" in titles


def test_splits_on_commas():
    raw = "submit assignment, prepare slides, email professor"
    res = parse_brain_dump(raw, NOW_ISO)
    assert len(res.items) == 3


def test_splits_on_then():
    raw = "finish reading then write summary then send to advisor"
    res = parse_brain_dump(raw, NOW_ISO)
    assert len(res.items) == 3


def test_deadline_keyword_classifies_as_deadline():
    raw = "midterm exam Friday at 10am"
    res = parse_brain_dump(raw, NOW_ISO)
    assert len(res.items) == 1
    assert res.items[0].kind == "deadline"
    assert res.items[0].when_local is not None
    assert res.items[0].confidence >= 0.85


def test_action_verb_classifies_as_task():
    raw = "study chapter 4 tomorrow"
    res = parse_brain_dump(raw, NOW_ISO)
    assert len(res.items) == 1
    assert res.items[0].kind == "task"
    assert res.items[0].when_local is not None


def test_undated_task_gets_default_when_and_low_conf():
    raw = "do laundry"
    res = parse_brain_dump(raw, NOW_ISO)
    assert len(res.items) == 1
    item = res.items[0]
    assert item.kind == "task"
    # Defaulted to NOW + 30min stagger; confidence dropped per parser.
    assert item.when_local is not None
    # Default sits at least 30min in the future of the anchor.
    assert item.when_local >= NOW_LOCAL + timedelta(minutes=29)


def test_multiple_undated_tasks_stagger_defaults():
    raw = "do laundry, clean room, organize desk"
    res = parse_brain_dump(raw, NOW_ISO)
    assert len(res.items) == 3
    # Each consecutive default-scheduled task should sit ~30 min later
    # than the previous to avoid /today collisions.
    starts = sorted(i.when_local for i in res.items if i.when_local)
    assert len(starts) == 3
    deltas = [
        (starts[i + 1] - starts[i]).total_seconds() / 60.0
        for i in range(len(starts) - 1)
    ]
    for d in deltas:
        assert d >= 25  # 30min target with some tolerance


def test_deadline_without_date_demoted_to_task():
    # "deadline X" with no parseable date → demotes to task rather
    # than reject (better to schedule than drop).
    raw = "deadline X"
    res = parse_brain_dump(raw, NOW_ISO)
    assert len(res.items) == 1
    assert res.items[0].kind == "task"


def test_binding_suggestion_links_task_to_deadline():
    raw = (
        "BCI paper due Friday\n"
        "read BCI paper tomorrow"
    )
    res = parse_brain_dump(raw, NOW_ISO)
    assert len(res.items) == 2
    deadline = next(i for i in res.items if i.kind == "deadline")
    task = next(i for i in res.items if i.kind == "task")

    assert len(res.bindings) == 1
    b = res.bindings[0]
    assert b.task_item_id == task.item_id
    assert b.deadline_item_id == deadline.item_id
    assert b.tier in ("tier1_auto", "tier2_ask")


def test_no_binding_for_unrelated_items():
    raw = (
        "midterm Friday at 10am\n"
        "buy groceries this weekend"
    )
    res = parse_brain_dump(raw, NOW_ISO)
    assert any(i.kind == "deadline" for i in res.items)
    # Groceries shouldn't bind to a midterm — no shared distinctive
    # tokens, so no tier2+ candidate.
    assert res.bindings == []


def test_title_strips_date_tokens():
    raw = "submit assignment Friday 5pm"
    res = parse_brain_dump(raw, NOW_ISO)
    assert len(res.items) == 1
    title = res.items[0].title.lower()
    # Date tokens should be cleaned out so the task title isn't
    # "submit assignment friday 5pm" forever.
    assert "5pm" not in title
    assert "friday" not in title


def test_task_default_duration_is_30_minutes_when_no_prior_matches():
    raw = "buy printer paper"
    res = parse_brain_dump(raw, NOW_ISO)
    assert res.items[0].duration_minutes == 30
    assert res.items[0].duration_source == "default_30_min"


def test_brain_dump_infers_academic_category_and_duration_prior():
    res = parse_brain_dump("CO tutorial tomorrow at 9am", NOW_ISO)
    item = res.items[0]

    assert item.kind == "task"
    assert item.category == "academic"
    assert item.category_source == "title_heuristic_v1"
    assert item.duration_minutes == 60
    assert item.duration_source == "research_prior_v1"
    assert "tutorial" in (item.duration_basis or "")


def test_brain_dump_infers_study_category_and_duration_prior():
    res = parse_brain_dump("AI final revision tomorrow at 10am", NOW_ISO)
    item = res.items[0]

    assert item.kind == "task"
    assert item.category == "study"
    assert item.duration_minutes == 90
    assert item.duration_source == "research_prior_v1"
    assert "exam-prep" in (item.duration_basis or "")


def test_explicit_duration_wins_over_research_prior():
    res = parse_brain_dump("read CO slides tomorrow for 45 minutes", NOW_ISO)
    item = res.items[0]

    assert item.category == "study"
    assert item.duration_minutes == 45
    assert item.duration_source == "explicit_text"


def test_deadline_has_no_duration():
    raw = "exam Friday 10am"
    res = parse_brain_dump(raw, NOW_ISO)
    deadline = next(i for i in res.items if i.kind == "deadline")
    assert deadline.duration_minutes is None


def test_long_segments_are_truncated_to_200_chars():
    raw = "study " + ("philosophy " * 50)  # well over 200 chars
    res = parse_brain_dump(raw, NOW_ISO)
    assert len(res.items) == 1
    assert len(res.items[0].title) <= 201  # 200 + "…"


# ── 2026-04-29 fix verification ────────────────────────────────────


def test_action_verb_wins_over_deadline_keyword():
    """`study for midterm tomorrow` should be a TASK (action verb wins).
    Bug surfaced in the Apr 28 edge-case battery: "midterm" is a
    deadline keyword, but the user is committing to STUDY — the verb
    is the intent, the keyword is the referent.
    """
    res = parse_brain_dump("study for midterm tomorrow", NOW_ISO)
    assert len(res.items) == 1
    assert res.items[0].kind == "task"


def test_study_for_midterm_binds_to_midterm_deadline():
    """End-to-end check: when study task and midterm deadline coexist,
    a binding suggestion fires. Was failing before action-verb-wins."""
    raw = "midterm Wednesday\nstudy for midterm tomorrow"
    res = parse_brain_dump(raw, NOW_ISO)
    deadlines = [i for i in res.items if i.kind == "deadline"]
    tasks = [i for i in res.items if i.kind == "task"]
    assert len(deadlines) == 1
    assert len(tasks) == 1
    assert len(res.bindings) == 1
    assert res.bindings[0].task_item_id == tasks[0].item_id
    assert res.bindings[0].deadline_item_id == deadlines[0].item_id


def test_trailing_at_stripped_from_title():
    """`call advisor at 3pm` should yield title `call advisor`, not
    `call advisor at`."""
    res = parse_brain_dump("call advisor at 3pm", NOW_ISO)
    assert len(res.items) == 1
    title = res.items[0].title.lower()
    assert title == "call advisor"


def test_trailing_on_stripped_from_title():
    res = parse_brain_dump("submit form on 16/5", NOW_ISO)
    assert len(res.items) == 1
    title = res.items[0].title.lower()
    assert title == "submit form"


def test_all_caps_trailing_preposition_stripped():
    """`EXAM ON FRIDAY 10AM` should yield title `EXAM`, not `EXAM ON`."""
    res = parse_brain_dump("EXAM ON FRIDAY 10AM", NOW_ISO)
    assert len(res.items) == 1
    # Trailing "ON" must be stripped (case-insensitive match in regex,
    # title preserves the original casing).
    assert "on" not in res.items[0].title.lower().split()


def test_leading_bullet_stripped_from_title():
    res = parse_brain_dump("- read chapter 3\n- write essay", NOW_ISO)
    titles = [i.title.lower() for i in res.items]
    assert "read chapter 3" in titles
    assert "write essay" in titles
    for t in titles:
        assert not t.startswith("-")


def test_numbered_bullet_stripped_from_title():
    res = parse_brain_dump("1. read book\n2. write notes\n3. review", NOW_ISO)
    titles = [i.title.lower() for i in res.items]
    assert "read book" in titles
    assert "write notes" in titles


def test_the_nth_date_format_extracted():
    """`exam on the 15th` should produce a deadline with a parsed date
    (the 15th of next month if today is past 15th of current month).
    """
    res = parse_brain_dump("exam on the 15th", NOW_ISO)
    assert len(res.items) == 1
    # "exam" is deadline keyword + we now match "the 15th" → high conf
    # deadline with a real anchor.
    assert res.items[0].kind == "deadline"
    assert res.items[0].when_local is not None


def test_this_weekend_extracts_a_date():
    """`do laundry this weekend` → task with parseable date (no longer
    falls through to default-now)."""
    res = parse_brain_dump("do laundry this weekend", NOW_ISO)
    assert len(res.items) == 1
    assert res.items[0].kind == "task"
    # `this weekend` should resolve to a real future date.
    assert res.items[0].when_local is not None
    assert res.items[0].when_local >= NOW_LOCAL


def test_month_name_date_extracted():
    """`May 16 deadline for X` should parse the May 16 anchor."""
    res = parse_brain_dump("submit X by May 16", NOW_ISO)
    assert len(res.items) == 1
    assert res.items[0].when_local is not None
    assert res.items[0].when_local.month == 5
    assert res.items[0].when_local.day == 16


def test_numeric_slash_dates_use_day_month_order():
    """Cairo-local onboarding users write slash dates as day/month.

    Regression shape: `study lecs DB 6/9` was parsed as June 9 under
    dateparser's default month/day behavior, then `6/9` was stripped from the
    visible title. The task looked ordinary but landed months off.
    """
    res = parse_brain_dump("study lecs DB 6/9", NOW_ISO)
    assert len(res.items) == 1
    assert res.items[0].kind == "task"
    assert res.items[0].title == "study lecs DB"
    assert res.items[0].when_local is not None
    assert res.items[0].when_local.month == 9
    assert res.items[0].when_local.day == 6


def test_decimal_time_format():
    """`meeting at 3:30pm tomorrow` should anchor at 15:30."""
    res = parse_brain_dump("call professor at 3:30pm tomorrow", NOW_ISO)
    assert len(res.items) == 1
    assert res.items[0].when_local is not None
    assert res.items[0].when_local.hour == 15
    assert res.items[0].when_local.minute == 30


def test_plus_separator_splits():
    """` + ` should split segments same as commas."""
    res = parse_brain_dump("read chapter 3 + write essay + review notes", NOW_ISO)
    assert len(res.items) == 3


def test_complex_real_dump_from_screenshot():
    """The exact dump operator pasted in the Apr 28 screenshot:
    `BCI paper deadline friday, read research paper 4 today,
    initiate contract workflow, CO final 16/5 10 am, CO Lec 4 today`

    Expected:
      D: BCI paper           (Friday)
      T: read research paper 4 (today)
      T: initiate contract workflow (default)
      D: CO final            (16/5 10am)
      T: CO Lec 4            (today)
    """
    raw = (
        "BCI paper deadline friday, read research paper 4 today, "
        "initiate contract workflow, CO final 16/5 10 am, CO Lec 4 today"
    )
    res = parse_brain_dump(raw, NOW_ISO)
    assert len(res.items) == 5
    kinds = sorted(i.kind for i in res.items)
    # 2 deadlines + 3 tasks
    assert kinds == ["deadline", "deadline", "task", "task", "task"]
    # Titles should not contain trailing prepositions or date tokens.
    for it in res.items:
        title_lower = it.title.lower()
        for bad in ("today", "friday", "16/5", "10 am"):
            assert bad not in title_lower, f"date token leaked in {it.title!r}"


def test_test_as_verb_is_task_not_deadline():
    """`test the API tomorrow` — `test` is in BOTH DEADLINE_KEYWORDS
    and TASK_LEADING_VERBS. Action-verb-wins should pick task."""
    res = parse_brain_dump("test the API tomorrow", NOW_ISO)
    assert len(res.items) == 1
    assert res.items[0].kind == "task"


def test_deadline_kw_as_substring_does_not_match():
    """`submitting paper tomorrow` — `submit` should NOT trigger
    deadline keyword (substring would, whole-word doesn't)."""
    res = parse_brain_dump("submitting paper tomorrow", NOW_ISO)
    assert len(res.items) == 1
    # No leading verb + no whole-word deadline kw + has date → task 0.55
    # "submitting" isn't in TASK_LEADING_VERBS but the segment shouldn't
    # accidentally get classified as deadline.
    assert res.items[0].kind == "task"
