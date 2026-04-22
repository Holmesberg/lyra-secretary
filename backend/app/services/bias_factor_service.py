"""bias_factor computation service — extracted from analytics.py (2026-04-22).

Pure-function module. Hosts:
  * `_bias_cell` — sum-ratio cell builder with confidence tier
  * `_confidence` — n-based confidence label (shared with analytics.py)
  * `RESEARCH_PRIORS` + `RESEARCH_PRIOR_DEFAULT` — published population priors
  * `_adaptive_calibration` — 4-level personal-data signal cascade
  * `blend` (added in Phase C) — archetype-prior shrinkage on top of personal

This refactor was driven by Phase A of the 2026-04-22 clustering ship.
Extracting the canonical computation out of the analytics endpoint makes
the Rule 13 pre-registered formula (MANIFESTO.md v1.10) testable in
isolation and lets future integrations call `blend()` without hitting
the endpoint.

Behavior unchanged from the in-analytics version. Identity at import
time: `_bias_cell`, `_confidence`, `RESEARCH_PRIORS`, `RESEARCH_PRIOR_DEFAULT`,
and `_adaptive_calibration` are re-exported from analytics.py so
existing call sites continue to work without edit.
"""
from __future__ import annotations

from typing import Optional

from app.db.models import Task
from app.utils.time_utils import to_local


def _confidence(n: int) -> str:
    """Confidence tier from sample size — shared by analytics + service."""
    if n >= 11:
        return "high"
    if n >= 6:
        return "medium"
    return "low"


def _bias_cell(rows: list[tuple[int, int]], min_n: int) -> Optional[dict]:
    """Build a bias-factor cell from (planned, executed) integer pairs.

    Returns None if rows < min_n. Otherwise returns:
        bias_factor       — sum(executed) / sum(planned)        (PRIMARY, weighted)
        bias_factor_mean  — mean(executed_i / planned_i)         (per-session mean)

    Sum-ratio is primary — weights longer tasks proportionally and is
    what a scheduler should consume to size the next slot. Mean-ratio
    reported alongside as sanity check — divergence reveals a bucket
    dominated by a small number of long sessions.
    """
    if len(rows) < min_n:
        return None
    sum_p = sum(p for p, _ in rows)
    sum_e = sum(e for _, e in rows)
    if sum_p <= 0:
        return None
    sum_ratio = round(sum_e / sum_p, 3)
    mean_ratio = round(sum(e / p for p, e in rows) / len(rows), 3)
    return {
        "bias_factor": sum_ratio,
        "bias_factor_mean": mean_ratio,
        "sessions": len(rows),
        "confidence": _confidence(len(rows)),
        "interpretation": (
            "on target" if 0.9 <= sum_ratio <= 1.1
            else "underestimates" if sum_ratio > 1.1
            else "overestimates"
        ),
    }


# Population-level priors per published planning-fallacy research.
# Frozen as part of MANIFESTO.md v1.10 Rule 13 pre-registration.
RESEARCH_PRIORS: dict[str, dict] = {
    "development": {"bias_factor": 1.50, "citation": "Buehler et al. 1994; Connolly & Dean 1997"},
    "work":        {"bias_factor": 1.45, "citation": "Buehler et al. 1994"},
    "study":       {"bias_factor": 1.40, "citation": "Newby-Clark et al. 2000"},
    "academic":    {"bias_factor": 1.40, "citation": "Newby-Clark et al. 2000"},
    "exercise":    {"bias_factor": 1.15, "citation": "Roy et al. 2005"},
    "fitness":     {"bias_factor": 1.15, "citation": "Roy et al. 2005"},
}
RESEARCH_PRIOR_DEFAULT = {
    "bias_factor": 1.35,
    "citation": "Kahneman & Tversky 1979 (planning fallacy mean)",
}


def _time_of_day(local_dt) -> str:
    """Bucket a local datetime into morning/afternoon/evening/night.

    Duplicated from analytics.py:16 to avoid circular imports when the
    service is consumed by the endpoint. Both definitions MUST stay in
    lockstep — changing one without the other corrupts the Rule 13 cell
    granularity.
    """
    h = local_dt.hour
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 17:
        return "afternoon"
    if 17 <= h < 21:
        return "evening"
    return "night"


def _adaptive_calibration(
    tasks: list[Task], category: str, tod: str, planned_minutes: int,
) -> dict:
    """Adaptive calibration using a signal cascade.

    Tries progressively broader slices of personal data before falling
    back to research priors. Each level is more specific but needs more
    data. The first level with >= 3 sessions wins.

    Signal cascade (most specific → broadest):
      1. category × tod × duration_bucket  (short/medium/long)
      2. category × tod                     (the original lookup)
      3. category only                      (any time of day)
      4. research prior                     (cold start only)

    Returns the winning signal with metadata about what contributed.
    """
    cat_rows_all: list[tuple[int, int]] = []
    cat_tod_rows: list[tuple[int, int]] = []
    cat_tod_dur_rows: list[tuple[int, int]] = []

    dur_bucket = "short" if planned_minutes < 30 else "long" if planned_minutes > 60 else "medium"

    for t in tasks:
        cat = t.category or "uncategorized"
        if cat != category:
            continue
        pair = (t.planned_duration_minutes, t.executed_duration_minutes)
        cat_rows_all.append(pair)

        t_tod = _time_of_day(to_local(t.planned_start_utc))
        if t_tod != tod:
            continue
        cat_tod_rows.append(pair)

        t_dur = (
            "short" if t.planned_duration_minutes < 30
            else "long" if t.planned_duration_minutes > 60
            else "medium"
        )
        if t_dur == dur_bucket:
            cat_tod_dur_rows.append(pair)

    signals = []

    # Level 1: category × tod × duration bucket (most specific)
    cell = _bias_cell(cat_tod_dur_rows, min_n=3)
    if cell is not None:
        cell["category"] = category
        cell["time_of_day"] = tod
        signals.append({
            "level": "category_tod_duration",
            "label": f"{category} / {tod} / {dur_bucket} tasks",
            "bias_factor": cell["bias_factor"],
            "sessions": cell["sessions"],
        })
        return {
            "cell": cell, "sessions": cell["sessions"], "min_sessions": 3,
            "source": "personal", "signal_level": "category_tod_duration",
            "signals": signals,
        }

    # Level 2: category × tod
    cell = _bias_cell(cat_tod_rows, min_n=3)
    if cell is not None:
        cell["category"] = category
        cell["time_of_day"] = tod
        signals.append({
            "level": "category_tod",
            "label": f"{category} / {tod}",
            "bias_factor": cell["bias_factor"],
            "sessions": cell["sessions"],
        })
        return {
            "cell": cell, "sessions": cell["sessions"], "min_sessions": 3,
            "source": "personal", "signal_level": "category_tod",
            "signals": signals,
        }

    # Level 3: category only (any time of day)
    cell = _bias_cell(cat_rows_all, min_n=3)
    if cell is not None:
        cell["category"] = category
        cell["time_of_day"] = "all"
        signals.append({
            "level": "category",
            "label": f"{category} (all times)",
            "bias_factor": cell["bias_factor"],
            "sessions": cell["sessions"],
        })
        return {
            "cell": cell, "sessions": cell["sessions"], "min_sessions": 3,
            "source": "personal", "signal_level": "category",
            "signals": signals,
        }

    # Level 4: research prior (cold start)
    prior = RESEARCH_PRIORS.get(category, RESEARCH_PRIOR_DEFAULT)
    signals.append({
        "level": "research",
        "label": prior["citation"],
        "bias_factor": prior["bias_factor"],
        "sessions": 0,
    })
    return {
        "cell": {
            "bias_factor": prior["bias_factor"],
            "bias_factor_mean": prior["bias_factor"],
            "sessions": 0,
            "confidence": "research",
            "interpretation": "underestimates",
            "category": category,
            "time_of_day": tod,
            "citation": prior["citation"],
        },
        "sessions": len(cat_rows_all),
        "min_sessions": 3,
        "source": "research",
        "signal_level": "research",
        "signals": signals,
    }
