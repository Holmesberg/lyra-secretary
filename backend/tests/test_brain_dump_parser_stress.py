"""Brain-dump parser regression tests — derived from the 2026-04-30
moriartyholmesberg stress test (61 cases, full report at
docs/brain_dump_stress_test_2026_04_30.md).

These pin down 20 representative parse behaviors so future changes to
brain_dump_parser.py / parser.py / deadline_heuristic.py don't silently
regress them. Pure-function tests over `parse_brain_dump` — no DB,
no LLM dependency, no network.

Test design:
- Tests that snapshot CURRENT-correct behavior (use plain `def test_`).
- Tests that snapshot CURRENT-broken behavior (use `pytest.mark.xfail` with
  `strict=True` so the test turns green when the bug is fixed and the CI
  notices it should be promoted to a regular passing test). The xfail
  marker carries the bug number / shape in its `reason=`.

Anchor "now" is fixed at 2026-04-30 14:00 local (matches the stress run's
mid-afternoon timing so "tomorrow at 10am" stays in the future).
"""
from datetime import datetime

import pytest

from app.services.brain_dump_parser import parse_brain_dump


# Fixed time anchor — Thursday afternoon. "Tomorrow" = Friday May 1.
NOW_LOCAL = datetime(2026, 4, 30, 14, 0, 0)
NOW_ISO = NOW_LOCAL.isoformat()


# ---------------------------------------------------------------------------
# Currently-correct behavior (snapshot to prevent regression)
# ---------------------------------------------------------------------------


def test_simple_time_anchored_task():
    """Stress case A1 (corrected anchor): time-anchored single task."""
    res = parse_brain_dump("Lab 8 problem set tomorrow at 3pm", NOW_ISO)
    assert len(res.items) == 1
    item = res.items[0]
    assert item.kind == "task"
    assert "Lab 8 problem set" in item.title
    assert item.when_local == datetime(2026, 5, 1, 15, 0, 0)


def test_explicit_deadline_with_date():
    """Stress case B1: explicit deadline keyword + date → kind=deadline."""
    res = parse_brain_dump("Algorithms midterm May 15", NOW_ISO)
    assert len(res.items) == 1
    item = res.items[0]
    assert item.kind == "deadline"
    assert item.title == "Algorithms midterm"
    assert item.when_local.month == 5
    assert item.when_local.day == 15


def test_verb_beats_deadline_keyword():
    """Stress case B3: action verb wins over 'midterm' keyword.

    Operator-locked decision (brain_dump_parser.py:147-181).
    """
    res = parse_brain_dump("study for midterm tomorrow", NOW_ISO)
    assert len(res.items) == 1
    assert res.items[0].kind == "task"
    assert "study" in res.items[0].title.lower()


def test_deadline_without_date_stays_deadline_candidate():
    """Stress case B5: 'deadline X' has no date — ask for one, don't hide it."""
    res = parse_brain_dump("deadline X", NOW_ISO)
    assert len(res.items) == 1
    assert res.items[0].kind == "deadline"
    assert res.items[0].when_local is None
    # Title strips the leading "deadline" keyword
    assert res.items[0].title == "X"


def test_chained_then_separator():
    """Stress case G1-ish: 'then' splits segments."""
    res = parse_brain_dump("finish reading then write summary then send to advisor", NOW_ISO)
    assert len(res.items) == 3


def test_comma_separator():
    res = parse_brain_dump("task A, task B, task C", NOW_ISO)
    assert len(res.items) == 3


def test_semicolon_separator():
    res = parse_brain_dump("task A; task B; task C", NOW_ISO)
    assert len(res.items) == 3


def test_mixed_delimiters():
    """Stress case G4: mix of `;`, `,`, `then`, `+` all split."""
    res = parse_brain_dump("task A; task B, task C then task D + task E", NOW_ISO)
    assert len(res.items) == 5


def test_undated_tasks_get_30min_stagger():
    """Stress case C2: 3 undated tasks → +30, +60, +90 from now."""
    res = parse_brain_dump("do dishes, fold laundry, take out trash", NOW_ISO)
    assert len(res.items) == 3
    deltas = [(it.when_local - NOW_LOCAL).total_seconds() / 60 for it in res.items]
    # First at +30, then +60, +90 (stagger from brain_dump_parser._default_when_for_task)
    assert deltas == [30.0, 60.0, 90.0]


def test_stagger_holds_at_10_items():
    """Stress case C4: 10 undated tasks all get distinct stagger slots."""
    res = parse_brain_dump(
        "task A, task B, task C, task D, task E, task F, task G, task H, task I, task J",
        NOW_ISO,
    )
    assert len(res.items) == 10
    starts = [it.when_local for it in res.items]
    # All distinct
    assert len(set(starts)) == 10


def test_this_weekend_rewrite():
    """Stress case A8: 'this weekend' → Saturday."""
    res = parse_brain_dump("do laundry this weekend", NOW_ISO)
    assert len(res.items) == 1
    item = res.items[0]
    assert item.when_local.weekday() == 5  # Saturday


def test_explicit_date_format():
    """Stress case A9: 'May 15' parses cleanly."""
    res = parse_brain_dump("submit report May 15", NOW_ISO)
    assert len(res.items) == 1
    item = res.items[0]
    assert item.when_local.month == 5
    assert item.when_local.day == 15


def test_emoji_preserved_in_title():
    """Stress case H3: emoji prefix stays in title."""
    res = parse_brain_dump("🏋️ workout tomorrow at 6pm", NOW_ISO)
    assert len(res.items) == 1
    assert "🏋" in res.items[0].title


def test_url_preserved_in_title():
    """Stress case H7: URL stays intact in title (not interpreted as date)."""
    res = parse_brain_dump("check https://example.com tomorrow at 5pm", NOW_ISO)
    assert len(res.items) == 1
    assert "https://example.com" in res.items[0].title


def test_bullet_list_one_task_per_bullet():
    """Stress case H8: '- task N' lines each become an item."""
    res = parse_brain_dump("- task 1\n- task 2\n- task 3", NOW_ISO)
    assert len(res.items) == 3


def test_empty_input_returns_empty_status():
    """Stress case H1."""
    res = parse_brain_dump("   \n  \t \n", NOW_ISO)
    assert res.parser_status == "empty"
    assert res.items == []


def test_cross_segment_binding_tier1_auto():
    """Stress case E1: high-overlap deadline + task → tier1_auto.

    Snapshots the heuristic's auto-bind behavior — confidence 1.00,
    deadline_match_source becomes user_explicit at commit time.
    """
    res = parse_brain_dump(
        "BCI paper due Friday\nread BCI paper tomorrow at 7pm",
        NOW_ISO,
    )
    assert len(res.items) == 2
    # One deadline, one task
    deadlines = [it for it in res.items if it.kind == "deadline"]
    tasks = [it for it in res.items if it.kind == "task"]
    assert len(deadlines) == 1
    assert len(tasks) == 1
    # Binding suggested at tier1_auto with confidence 1.00
    assert len(res.bindings) == 1
    binding = res.bindings[0]
    assert binding.tier == "tier1_auto"
    assert binding.confidence >= 0.95
    assert binding.deadline_title == "BCI paper"


def test_brittle_token_does_not_auto_bind():
    """Stress case E2: 'paper' is a brittle token per deadline_heuristic.py.

    Even with shared 'paper' token, no tier1_auto suggestion fires.
    """
    res = parse_brain_dump(
        "Paper review due Friday\nwrite paper summary tomorrow 5pm",
        NOW_ISO,
    )
    # 1 deadline + 1 task parsed
    assert any(it.kind == "deadline" for it in res.items)
    assert any(it.kind == "task" for it in res.items)
    # NO binding suggestion — brittle token rejection
    assert len(res.bindings) == 0


def test_unique_match_among_competing_deadlines():
    """Stress case E5: 'work on the report' picks Report (not Paper).

    Both Paper and Report parsed as deadlines; task title says 'report' →
    binding correctly chooses Report at tier1_auto.
    """
    res = parse_brain_dump(
        "Paper due Monday\nReport due Tuesday\nwork on the report tomorrow 4pm",
        NOW_ISO,
    )
    deadlines = [it for it in res.items if it.kind == "deadline"]
    tasks = [it for it in res.items if it.kind == "task"]
    assert len(deadlines) == 2
    assert len(tasks) == 1
    # Auto-bind to Report
    assert len(res.bindings) == 1
    assert res.bindings[0].deadline_title == "Report"
    assert res.bindings[0].tier == "tier1_auto"


def test_arabic_text_preserved_no_crash():
    """Stress case H5: Arabic text doesn't crash the parser.

    Date isn't parsed (parser doesn't speak Arabic), but the segment
    survives intact in the title.
    """
    res = parse_brain_dump("ادرس الفصل الرابع غدا", NOW_ISO)
    assert len(res.items) == 1
    assert "ادرس" in res.items[0].title


# ---------------------------------------------------------------------------
# Currently-broken behavior — xfail markers so a fix turns the test green
# ---------------------------------------------------------------------------


def test_explicit_duration_extracted():
    """LYR-115 fix landed 2026-04-30 — durations now extracted from
    text. Was an xfail; now a passing snapshot."""
    res = parse_brain_dump("PHM lecture tomorrow at 10am 60 min", NOW_ISO)
    assert len(res.items) == 1
    assert res.items[0].duration_minutes == 60


def test_title_strip_removes_at_for():
    """LYR-115-adjacent fix landed 2026-04-30 — duration tokens now
    strip first, exposing trailing 'at'/'for' for the existing
    trailing-prep peel. Was an xfail; now a passing snapshot."""
    res = parse_brain_dump("Lab 8 problem set tomorrow at 3pm for 30 minutes", NOW_ISO)
    title = res.items[0].title
    assert " at " not in title.lower() and not title.lower().endswith(" at")
    assert " for " not in title.lower() and not title.lower().endswith(" for")


@pytest.mark.xfail(
    strict=True,
    reason=(
        "P1: SEGMENT_SPLIT regex doesn't include 'and'. Natural-language "
        "inputs like 'study from 2-4pm and meeting from 3-4pm' get treated "
        "as ONE segment. Surfaced by 2026-04-30 stress test cases F1, F5."
    ),
)
def test_xfail_and_separator_splits_segments():
    res = parse_brain_dump(
        "study tomorrow at 3pm and meeting tomorrow at 4pm",
        NOW_ISO,
    )
    assert len(res.items) == 2


def test_time_range_extracts_duration():
    """Time-range fix landed 2026-04-30 — '1-5pm' now extracts both
    start time AND duration via TIME_RANGE_RE pre-pass. Was an xfail;
    now a passing snapshot."""
    res = parse_brain_dump("study tomorrow 1-5pm", NOW_ISO)
    assert len(res.items) == 1
    item = res.items[0]
    # Should land at 13:00 with 240-min duration
    assert item.when_local == datetime(2026, 5, 1, 13, 0, 0)
    assert item.duration_minutes == 240
