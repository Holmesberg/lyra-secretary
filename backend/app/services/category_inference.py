"""Deterministic category and duration priors for early task capture.

This module is intentionally small and synchronous. It is used by both
brain-dump parse previews and TaskManager creation so Baseet-style flows
where students never choose a category still land in the same taxonomy.

Boundary frozen 2026-05-20:
  - academic: institution/provided or prescheduled structure such as
    deadlines, lectures, tutorials, labs, classes, and sections.
  - study: user-owned self-study such as revision, reading, slide review,
    practice, homework, and problem-solving blocks.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional


ACADEMIC_SCHEDULE_TOKENS = {
    "class",
    "course",
    "lab",
    "labs",
    "lec",
    "lecture",
    "lectures",
    "practical",
    "section",
    "seminar",
    "tut",
    "tutorial",
    "tutorials",
}

STUDY_SESSION_TOKENS = {
    "assignment",
    "homework",
    "practice",
    "problem",
    "read",
    "reading",
    "rev",
    "review",
    "revise",
    "revision",
    "sheet",
    "slides",
    "solve",
    "study",
}

ACADEMIC_DURATION_PRIORS = (
    ({"lab", "labs", "practical"}, 120, "academic lab/practical block prior"),
    ({"lec", "lecture", "lectures", "class", "course", "seminar"}, 90, "academic lecture/class block prior"),
    ({"tut", "tutorial", "tutorials", "section"}, 60, "academic tutorial/section block prior"),
)

STUDY_DURATION_PRIORS = (
    ({"assignment", "homework", "practice", "problem", "sheet", "solve"}, 90, "study problem-set/work block prior"),
    ({"final", "finals", "midterm", "midterms", "exam", "exams", "quiz", "test"}, 90, "study exam-prep block prior"),
    ({"read", "reading", "slides", "review", "revise", "revision", "rev", "study"}, 60, "study review/reading block prior"),
)


@dataclass(frozen=True)
class DurationPrior:
    minutes: int
    source: str
    confidence: float
    basis: str


def title_tokens(title: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (title or "").lower()))


def infer_academic_category(title: str) -> Optional[str]:
    """Return the deterministic academic/study category, if one matches."""
    title_lower = (title or "").lower()
    words = title_tokens(title_lower)
    if words & ACADEMIC_SCHEDULE_TOKENS:
        return "academic"
    if words & STUDY_SESSION_TOKENS or "problem set" in title_lower:
        return "study"
    return None


def infer_research_duration_prior(
    title: str,
    category: Optional[str],
) -> Optional[DurationPrior]:
    """Return a low-authority starting duration when the user omitted one.

    These are session-block priors, not full workload estimates. For example,
    "final revision" becomes a suggested study block, not the total expected
    preparation time for the final.
    """
    cat = (category or "").strip().lower()
    words = title_tokens(title)
    prior_rows = (
        ACADEMIC_DURATION_PRIORS if cat == "academic"
        else STUDY_DURATION_PRIORS if cat == "study"
        else ()
    )
    for tokens, minutes, basis in prior_rows:
        if words & tokens or ("problem set" in (title or "").lower() and "problem" in tokens):
            return DurationPrior(
                minutes=minutes,
                source="research_prior_v1",
                confidence=0.55,
                basis=basis,
            )
    return None
