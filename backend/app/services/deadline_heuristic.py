"""Tier 0 deterministic deadline-suggestion heuristic (2026-04-28).

Sibling of the LLM enrichment path. Runs synchronously inside POST
/v1/create with sub-10ms latency. When confident, populates
`task.llm_deadline_candidates` immediately so the user sees a candidate
the moment the task lands on /today.

Operator-locked design (2026-04-28 conversation):

  Score components (additive, then capped at +1.0):
    +1.0  exact normalized title match (full title in haystack)
    +0.8  haystack startswith deadline.title (case + punct normalized)
    +0.6  deadline.title is substring of haystack
    +0.4  meaningful-token overlap (post stopword strip)
    -0.5  applied per competing candidate above 0.5 (multi-match penalty)

  Strong suggestion requires ALL:
    1. top.score >= AUTO_BIND_MIN_SCORE (0.6)
    2. top.score - second.score >= UNIQUENESS_MARGIN (0.2)
    3. count(c for c in candidates if c.score >= 0.5) <= 1
    4. NOT brittle_match — if removing generic tokens drops score below
       BRITTLE_FLOOR (0.5), the match is incidental ("paper" matched but
       nothing semantically distinctive)

  Failing any guardrail → return ranked candidates anyway, but
  `auto_bind=False`. The chip surfaces them; user decides. Despite the
  legacy field name, `auto_bind=True` now means "safe to preview as the
  top suggestion"; /v1/create does not write a canonical deadline_id
  unless the request carries an explicit deadline_id.

Source enum granularity (per operator's research-integrity guidance —
Rule 14 stratification stays sharp):
  - 'heuristic_exact_title'   score >= 1.0
  - 'heuristic_startswith'    0.8 <= score < 1.0
  - 'heuristic_substring'     0.6 <= score < 0.8
  - 'heuristic_alias'         (reserved — for future user-defined alias
                               table; not populated yet)

Override priority (chip + LLM worker respect this order):
    manual_user > heuristic_exact_title > llm_auto_confirmed >
    user_corrected > heuristic_startswith > heuristic_substring >
    parser_auto > null

Pre-registration footnote: the four new `deadline_match_source` values
extend Rule 14's stratification list (per docs/manifesto_alignment_audit_
2026_04_28.md item #2 pattern). Documented in the commit message + the
heuristic registry doc.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional

from app.db.models import Deadline


AUTO_BIND_MIN_SCORE = 0.6
UNIQUENESS_MARGIN = 0.2
BRITTLE_FLOOR = 0.5

# Course-code constraint (operator decision 2026-05-01 after a false-
# positive cross-subject match: a CSE221 task bound to a PHM112
# deadline because the brittle-token guard didn't catch a multi-
# generic overlap). When both task title AND deadline title carry a
# parseable course code (regex below) and the codes differ, the match
# is structurally rejected — score = 0. When only one side has a
# code, fall through to title-only matching (degraded mode for
# manually-created deadlines without a code in the title).
#
# Same regex shape as moodle_submissions_sync._COURSE_CODE_RE; kept
# duplicated rather than extracted to a shared util because the two
# systems have different downstream use of the match (matcher vs
# category derivation) and a future refactor may want to diverge.
_COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,5}\d{2,4})\b")

# Generic tokens that should NOT be the sole semantic anchor for an
# auto-bind. If removing these from the input drops the score below
# BRITTLE_FLOOR, the match is brittle (e.g. "paper reading" vs deadline
# "BCI Paper" — the only shared token is the generic "paper"). The list
# is operator-curated for the alpha cohort; a future amendment can ship
# per-user-typed banlist if abuse appears.
BRITTLE_TOKENS = {
    "paper", "project", "task", "work", "thing", "stuff",
    "time", "plan", "review", "session", "block", "todo",
    "report", "doc", "note", "writeup",
}
GENERIC_DEADLINE_TOKENS = {
    "final", "finals", "exam", "exams", "quiz", "quizzes",
    "lab", "labs", "lecture", "lectures", "lec", "tutorial",
    "tutorials", "assignment", "assignments", "submission",
}

_NORMALIZE_RE = re.compile(r"[^a-z0-9\s]+")
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "to", "for", "of", "and", "or", "in", "on",
    "at", "by", "with", "due", "today", "tomorrow", "deadline",
    "is", "are", "be", "am", "pm", *GENERIC_DEADLINE_TOKENS,
}


@dataclass
class HeuristicCandidate:
    deadline_id: str
    title: str
    score: float
    source: str  # heuristic_exact_title | heuristic_startswith | heuristic_substring


@dataclass
class HeuristicMatch:
    """Returned to /v1/create and /parse/deadline-preview.

    `auto_bind=True` is a legacy name. It now means the top candidate is
    strong enough to show as the default suggestion; canonical binding
    still requires explicit user confirmation.
    """
    candidates: list[HeuristicCandidate]
    auto_bind: bool
    rejected_reason: Optional[str]  # debug/audit-only label when auto_bind=False


def _normalize(s: str) -> str:
    return _NORMALIZE_RE.sub(" ", (s or "").lower()).strip()


def _meaningful_tokens(s: str) -> set[str]:
    return {
        t for t in _TOKEN_RE.findall((s or "").lower())
        if t not in _STOPWORDS and (len(t) >= 3 or len(t) == 2)
    }


def _subject_tokens_from_tokens(tokens: set[str]) -> set[str]:
    """Short academic identity tokens such as AI/CO/OS/CV.

    These are too short for ordinary keyword matching but highly
    discriminative for imported course/deadline titles. Generic deadline
    words stay excluded, so "final" alone cannot bind two unrelated rows.
    """
    return {
        t for t in tokens
        if (len(t) == 2 or any(ch.isdigit() for ch in t))
        and t not in _STOPWORDS
        and t not in BRITTLE_TOKENS
        and t not in GENERIC_DEADLINE_TOKENS
    }


def _subject_tokens(s: Optional[str]) -> set[str]:
    out: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9]+", s or ""):
        t = raw.lower()
        if t in _STOPWORDS or t in BRITTLE_TOKENS or t in GENERIC_DEADLINE_TOKENS:
            continue
        if len(t) == 2:
            out.add(t)
        elif 3 <= len(t) <= 5 and (raw.isupper() or any(ch.isdigit() for ch in raw)):
            out.add(t)
    return out


def _score_one(haystack_norm: str, haystack_tokens: set[str], deadline: Deadline) -> tuple[float, str]:
    """Return (score, source) for a single deadline match attempt.
    Source is the highest-confidence component that contributed."""
    title_norm = _normalize(deadline.title)
    if not title_norm:
        return 0.0, "heuristic_substring"
    title_tokens = _meaningful_tokens(deadline.title)

    if not haystack_norm:
        return 0.0, "heuristic_substring"

    # Exact title match (haystack contains title as a phrase OR title equals haystack)
    if haystack_norm == title_norm:
        return 1.0, "heuristic_exact_title"
    if title_norm in haystack_norm.split():  # exact-word boundary
        # If the title is a single token that appears as a word, treat
        # as exact only when the title is multi-character; single-letter
        # matches don't qualify.
        if len(title_norm) >= 3:
            return 1.0, "heuristic_exact_title"

    # Multi-word phrase match (sliding window word-level)
    title_phrase = title_norm
    if title_phrase in haystack_norm and " " in title_phrase:
        # Multi-word phrase appearing literally → highest confidence
        return 1.0, "heuristic_exact_title"

    # Startswith (haystack starts with the title)
    if haystack_norm.startswith(title_norm + " ") or haystack_norm == title_norm:
        return 0.8, "heuristic_startswith"

    # Single-token title appearing word-boundary in haystack
    if len(title_norm.split()) == 1 and title_norm in haystack_tokens:
        return 0.8, "heuristic_startswith"

    # Academic acronym match: "AI project revision" should prefer
    # "AI final" over "CO Final"; the generic word "final" is not enough.
    subject_overlap = (
        _subject_tokens_from_tokens(haystack_tokens)
        & _subject_tokens_from_tokens(title_tokens)
    )
    if subject_overlap:
        return 0.7, "heuristic_substring"

    # Plain substring match (case-insensitive)
    if title_norm in haystack_norm:
        return 0.6, "heuristic_substring"

    # Token overlap fallback
    if title_tokens and haystack_tokens:
        overlap = title_tokens & haystack_tokens
        if not overlap:
            return 0.0, "heuristic_substring"
        # Jaccard-like ratio over the deadline title's tokens
        ratio = len(overlap) / len(title_tokens)
        if ratio >= 0.5:
            return min(0.6, 0.4 + 0.2 * (ratio - 0.5)), "heuristic_substring"
        return 0.4 * ratio, "heuristic_substring"

    return 0.0, "heuristic_substring"


def _course_code_of(s: Optional[str]) -> Optional[str]:
    """First parseable course code in `s` (e.g., 'CSE281' from
    'HandsOn CSE281 Lab8 is due'). Returns None if no code present —
    callers treat None as 'unconstrained' rather than 'no match'."""
    if not s:
        return None
    m = _COURSE_CODE_RE.search(s)
    return m.group(1) if m else None


def _course_codes_collide(haystack: str, deadline: Deadline) -> bool:
    """True when both the task haystack AND the deadline title have a
    parseable course code AND they are different. False when either
    side lacks a code (degraded mode — no constraint applied) OR the
    codes match. Operator-locked structural noise filter — see
    _COURSE_CODE_RE comment for incident context.

    The deadline's category_hint is also consulted because Moodle iCal
    imports stash the course code there (e.g. 'CSE221'); the deadline
    title itself often omits it ('Major Task - Phase II is due')."""
    haystack_code = _course_code_of(haystack)
    if haystack_code is None:
        return False
    deadline_code = _course_code_of(deadline.title) or _course_code_of(
        getattr(deadline, "category_hint", None)
    )
    if deadline_code is None:
        # Fall through to short academic identity tokens below.
        pass
    elif haystack_code != deadline_code:
        return True

    haystack_subjects = _subject_tokens(haystack)
    deadline_subjects = (
        _subject_tokens(deadline.title)
        | _subject_tokens(getattr(deadline, "category_hint", None))
    )
    if haystack_subjects and deadline_subjects:
        return haystack_subjects.isdisjoint(deadline_subjects)
    return False


def _is_brittle(haystack_tokens: set[str], deadline: Deadline) -> bool:
    """True when the match would disappear if we removed brittle tokens
    from the haystack — i.e. the score depends on a generic word like
    'paper' rather than something semantically distinctive."""
    title_tokens = _meaningful_tokens(deadline.title)
    if not title_tokens:
        return False
    overlap_with_brittle = haystack_tokens & title_tokens
    overlap_without_brittle = (haystack_tokens - BRITTLE_TOKENS) & (title_tokens - BRITTLE_TOKENS)
    if not overlap_with_brittle:
        return False  # no overlap to be brittle about
    # If filtering brittle tokens drops overlap to zero AND there were
    # only 1-2 shared tokens to begin with, the match is brittle.
    if not overlap_without_brittle and len(overlap_with_brittle) <= 2:
        return True
    return False


def score_deadlines(
    title: str,
    description: Optional[str],
    deadlines: list[Deadline],
) -> HeuristicMatch:
    """Score every deadline against the task's title+description.
    Returns ranked candidates + auto-bind decision per operator's
    4-rule guardrail.
    """
    if not deadlines:
        return HeuristicMatch(candidates=[], auto_bind=False, rejected_reason="no_deadlines")

    haystack = f"{title or ''} {description or ''}"
    haystack_norm = _normalize(haystack)
    haystack_tokens = _meaningful_tokens(haystack)

    scored: list[HeuristicCandidate] = []
    for d in deadlines:
        # Subject-code constraint: if both sides carry course codes
        # and they differ, structural reject before scoring tokens.
        # See _course_codes_collide docstring for incident context.
        if _course_codes_collide(haystack, d):
            continue
        score, source = _score_one(haystack_norm, haystack_tokens, d)
        if score > 0.0:
            scored.append(HeuristicCandidate(
                deadline_id=d.deadline_id,
                title=d.title,
                score=round(score, 3),
                source=source,
            ))

    scored.sort(key=lambda c: -c.score)

    # Apply multi-match penalty to the top candidate's effective score
    # for guardrail evaluation, but report the raw score on the chip
    # data — the user sees the raw number, the auto-bind logic uses the
    # adjusted one.
    competing = sum(1 for c in scored[1:] if c.score >= 0.5)
    if not scored:
        return HeuristicMatch(candidates=[], auto_bind=False, rejected_reason="no_score")

    top = scored[0]

    # Guardrail 1: top score must clear minimum
    if top.score < AUTO_BIND_MIN_SCORE:
        return HeuristicMatch(candidates=scored, auto_bind=False, rejected_reason="below_min_score")

    # Guardrail 2: uniqueness margin
    if len(scored) >= 2:
        margin = top.score - scored[1].score
        if margin < UNIQUENESS_MARGIN:
            return HeuristicMatch(candidates=scored, auto_bind=False, rejected_reason="uniqueness_margin")

    # Guardrail 3: at most one competitive candidate
    if competing > 0:
        return HeuristicMatch(candidates=scored, auto_bind=False, rejected_reason="multi_competitive")

    # Guardrail 4: brittle match (only generic tokens shared)
    top_deadline = next((d for d in deadlines if d.deadline_id == top.deadline_id), None)
    if top_deadline is not None and _is_brittle(haystack_tokens, top_deadline):
        # Demote brittle exact-token matches but keep showing the chip.
        # Don't auto-bind something the user might call generic.
        return HeuristicMatch(candidates=scored, auto_bind=False, rejected_reason="brittle_match")

    return HeuristicMatch(candidates=scored, auto_bind=True, rejected_reason=None)
