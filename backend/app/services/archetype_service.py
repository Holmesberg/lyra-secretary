"""Instrument scoring + archetype assignment — Phase 5 clustering service.

Pure functions. No DB access; endpoints wire these to ArchetypeAssignment
writes. Supports the 2026-04-22 clustering acceleration (see
docs/strategic_decisions_april_22.md §5 + MANIFESTO.md Rule 13).

Four instruments + assignment algorithm per docs/methodology.md:

  * MEQ-5 (Adan & Almirall 1991): 5-item morningness. Items 1 and 5
    use 1-5 weights; items 2, 3, 4 use 1-4 weights. Sum range 4-25.
    Thresholds: ≤11 evening, 12-17 intermediate, ≥18 morning.

  * BFI-10 C (Rammstedt & John 2007): 2-item conscientiousness.
    Item 1 forward, item 2 reverse-keyed. Sum range 2-10.
    Thresholds: ≤4 low, 5-7 mid, ≥8 high.

  * BSCS-Brief (Tangney, Baumeister, Boone 2004): 13-item self-control.
    Reverse-keyed indices: {2, 3, 4, 5, 7, 9, 10, 12, 13} (9 of 13).
    Sum range 13-65. Tertile thresholds (US college norms):
    ≤33 low, 34-45 mid, ≥46 high.

  * GP-Short (Lay 1986 / Steel 2010 abbreviated): 9-item general
    procrastination. All items forward-keyed (high = more procrastinate).
    Sum range 9-45. Thresholds: ≤20 low, 21-32 mid, ≥33 high.

All Likert response integers are validated 1..max; out-of-range raises
ValueError so corrupted submissions fail loud, not silent.

Discipline z-score composite:
  discipline_z = 0.30 * z(bfi_c) + 0.40 * z(bscs) - 0.30 * z(gp)

Normative params (frozen at Rule 13 launch — MANIFESTO.md v1.10):
  bfi_c:  mean 6.0,  sd 1.8   — Rammstedt & John 2007
  bscs:   mean 39.0, sd 8.0   — Tangney 2004 median + Chebyshev-fitted spread
  gp:     mean 28.0, sd 7.5   — Steel 2010 pooled samples

Tertile discipline classification at z ≤ -0.43 (low) / -0.43 < z < 0.43
(mid) / z ≥ 0.43 (high), matching the 33rd and 67th percentiles of the
standard normal.

Assignment priority (most specific first — methodology.md:85-90 had the
`(_, low) → Procrastinator` pattern listed before
`("morning", low) → Lark Low-Discipline` which if read as ordered
matching would make Lark Low-Discipline unreachable; the table at
methodology.md:46-52 confirms Lark Low-Discipline = morning × low
specifically, so we implement specific-first):

  morning  × high  → disciplined_lark
  evening  × high  → disciplined_owl
  morning  × low   → lark_low_discipline
  _        × low   → procrastinator         (evening+low, intermediate+low)
  _                → diffuse_average        (everything remaining)
"""
from __future__ import annotations

from typing import Literal

Chronotype = Literal["evening", "intermediate", "morning"]
Discipline = Literal["low", "mid", "high"]

# ---------------------------------------------------------------------------
# Frozen normative params — DO NOT MODIFY without a MANIFESTO amendment.
# These values are pre-registered as part of Rule 13.
# ---------------------------------------------------------------------------
NORMATIVE_PARAMS: dict[str, dict[str, float]] = {
    # Rammstedt & John 2007, J Res Pers 41:203-212. Sample of 833 US adults;
    # reported BFI-10 C mean ≈ 6.0, sd ≈ 1.8 on the 2-10 scale.
    "bfi_c": {"mean": 6.0, "sd": 1.8},
    # Tangney, Baumeister, Boone 2004, J Pers 72:271-322. 13-item brief
    # self-control scale; reported median ≈ 39 on college sample with
    # approx SD 8.0 (consistent across multiple replications 2004-2015).
    "bscs": {"mean": 39.0, "sd": 8.0},
    # Lay 1986 / Steel 2010 pooled samples, 9-item short-form GP.
    # Steel 2010 meta-analytic mean ≈ 28.0, sd ≈ 7.5.
    "gp": {"mean": 28.0, "sd": 7.5},
}

# BSCS-Brief reverse-keyed item indices (1-indexed per Tangney 2004 paper).
# Converting to 0-indexed for array access.
_BSCS_REVERSE_INDICES_1 = {2, 3, 4, 5, 7, 9, 10, 12, 13}


def _validate_likert(items: list[int], count: int, low: int, high: int, label: str) -> None:
    """Validate a Likert response array. Raise ValueError on mismatch."""
    if len(items) != count:
        raise ValueError(f"{label}: expected {count} items, got {len(items)}")
    for i, v in enumerate(items):
        if not isinstance(v, int) or v < low or v > high:
            raise ValueError(
                f"{label}: item {i} value {v!r} out of range [{low}, {high}]"
            )


def score_meq(items: list[int]) -> tuple[int, Chronotype]:
    """Score 5-item MEQ short form.

    Items 1, 5 use 1-5 weights; items 2, 3, 4 use 1-4 weights. Frontend
    is responsible for presenting the correct scale and sending already-
    weighted integers. Sum range 4-25.
    """
    if len(items) != 5:
        raise ValueError(f"meq: expected 5 items, got {len(items)}")
    for i, v in enumerate(items):
        lo, hi = (1, 5) if i in (0, 4) else (1, 4)
        if not isinstance(v, int) or v < lo or v > hi:
            raise ValueError(
                f"meq: item {i} value {v!r} out of range [{lo}, {hi}]"
            )
    raw = sum(items)
    if raw <= 11:
        return raw, "evening"
    if raw <= 17:
        return raw, "intermediate"
    return raw, "morning"


def score_bfi_c(items: list[int]) -> tuple[int, Discipline]:
    """Score 2-item BFI-10 C (conscientiousness).

    Item 1 forward-keyed ("I see myself as someone who does a thorough
    job"). Item 2 reverse-keyed ("I see myself as someone who tends to
    be lazy"). Frontend sends raw 1-5 responses; server reverse-keys.
    Sum range 2-10.
    """
    _validate_likert(items, 2, 1, 5, "bfi_c")
    raw = items[0] + (6 - items[1])
    if raw <= 4:
        return raw, "low"
    if raw <= 7:
        return raw, "mid"
    return raw, "high"


def score_bscs(items: list[int]) -> tuple[int, Discipline]:
    """Score 13-item BSCS-Brief (self-control).

    Reverse-keyed items (Tangney 2004 1-indexed): 2, 3, 4, 5, 7, 9, 10,
    12, 13. Frontend sends raw 1-5 responses; server reverse-keys.
    Sum range 13-65. Tertile cutoffs at 33 / 45 per Tangney 2004 US
    college norms.
    """
    _validate_likert(items, 13, 1, 5, "bscs")
    total = 0
    for i, v in enumerate(items):
        idx_1 = i + 1  # BSCS paper uses 1-indexed item numbers
        total += (6 - v) if idx_1 in _BSCS_REVERSE_INDICES_1 else v
    if total <= 33:
        return total, "low"
    if total <= 45:
        return total, "mid"
    return total, "high"


def score_gp(items: list[int]) -> tuple[int, Discipline]:
    """Score 9-item GP-Short (general procrastination).

    All items forward-keyed — high response = more procrastination.
    NOTE: higher GP score implies LOWER discipline, which is why the
    discipline_z composite uses `-0.30 * z(gp)` (negated).
    Sum range 9-45. Thresholds per methodology.md: ≤20 low procrast.,
    21-32 mid, ≥33 high.
    """
    _validate_likert(items, 9, 1, 5, "gp")
    raw = sum(items)
    if raw <= 20:
        return raw, "low"
    if raw <= 32:
        return raw, "mid"
    return raw, "high"


def _z(value: float, key: str) -> float:
    params = NORMATIVE_PARAMS[key]
    return (value - params["mean"]) / params["sd"]


def compute_discipline_z(bfi_c: int, bscs: int, gp: int) -> float:
    """Weighted z-composite per methodology.md:40.

    discipline_z = 0.30*z(bfi_c) + 0.40*z(bscs) - 0.30*z(gp)

    BSCS gets largest weight (0.40) because it asks about actions, not
    self-image. GP is negated because high GP = high procrastination
    = low discipline.
    """
    return (
        0.30 * _z(bfi_c, "bfi_c")
        + 0.40 * _z(bscs, "bscs")
        - 0.30 * _z(gp, "gp")
    )


def classify_discipline(z_score: float) -> Discipline:
    """Tertile split at z = ±0.43 (33rd/67th percentiles of standard normal)."""
    if z_score <= -0.43:
        return "low"
    if z_score >= 0.43:
        return "high"
    return "mid"


def assign_archetype(chronotype: Chronotype, discipline: Discipline) -> str:
    """Return archetype_id for a (chronotype, discipline) pair.

    Specific-first priority (see module docstring for the methodology.md
    ambiguity note). Lark Low-Discipline catches morning+low BEFORE
    the general Procrastinator branch catches any other low-discipline.
    """
    if chronotype == "morning" and discipline == "high":
        return "disciplined_lark"
    if chronotype == "evening" and discipline == "high":
        return "disciplined_owl"
    if chronotype == "morning" and discipline == "low":
        return "lark_low_discipline"
    if discipline == "low":
        return "procrastinator"
    return "diffuse_average"


DIFFUSE_AVERAGE_ID = "diffuse_average"
