r"""Unit tests for the Loop 11 scope-bullet counter.

extract_scope_bullets(description) returns:
- None if description is None or empty
- 0 if description has text but no bullets
- N where N is the count of lines starting with `^\s*[-*•·]`

Operationalizes MANIFESTO Rule 12 amendment (`scope_bullet_count_at_plan`).
"""
from app.services.parser import extract_scope_bullets


def test_none_description_returns_none():
    assert extract_scope_bullets(None) is None


def test_empty_string_returns_none():
    # Empty is treated as "no description" → None (distinguishable from 0).
    assert extract_scope_bullets("") is None


def test_no_bullets_returns_zero():
    assert extract_scope_bullets("just a plain description") == 0


def test_three_dash_bullets():
    desc = "- step 1\n- step 2\n- step 3"
    assert extract_scope_bullets(desc) == 3


def test_mixed_bullet_markers():
    # Each marker counts: -, *, •, ·
    desc = "- a\n* b\n• c\n· d"
    assert extract_scope_bullets(desc) == 4


def test_indented_bullets_count():
    desc = "  - indented two spaces\n    * indented four spaces\n\t- tab indented"
    assert extract_scope_bullets(desc) == 3


def test_mid_line_dash_does_not_count():
    # Mid-line dashes (e.g., "task - urgent") are NOT bullets.
    assert extract_scope_bullets("task - urgent") == 0


def test_mixed_bullets_and_mid_line_dashes():
    desc = "- bullet one\nfoo - not a bullet\n- bullet two"
    assert extract_scope_bullets(desc) == 2


def test_unicode_bullets():
    # • is U+2022 (bullet), · is U+00B7 (middle dot).
    desc = "• unicode bullet\n· middle dot bullet"
    assert extract_scope_bullets(desc) == 2


def test_windows_line_endings():
    # \r\n line endings still match (the ^ in MULTILINE mode resets after \n).
    desc = "- step 1\r\n- step 2\r\n"
    assert extract_scope_bullets(desc) == 2


def test_only_whitespace_lines_no_bullets():
    desc = "   \n\t\n   \n"
    assert extract_scope_bullets(desc) == 0


def test_single_bullet():
    assert extract_scope_bullets("- only one") == 1


def test_zero_distinguishable_from_none():
    # Critical: a description with text but no bullets returns 0, not None.
    # This lets analytics distinguish "user wrote a paragraph" from "user
    # wrote nothing".
    assert extract_scope_bullets("a long paragraph with no bullets at all") == 0
    assert extract_scope_bullets(None) is None
