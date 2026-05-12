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

from sqlalchemy.orm import Session

from app.db.models import Archetype, Task, User
from app.services.archetype_service import DIFFUSE_AVERAGE_ID
from app.services.exposure_ledger import baseline_clean_task_ids
from app.utils.time_utils import to_local

# Normalization anchor for the composite scaling rule (Rule 13). The
# `diffuse_average` archetype's prior of 1.30 matches the population
# midpoint in RESEARCH_PRIORS (Roy 2005 meta-analytic mean), so
# `archetype_scaling = archetype.prior_bias_factor / 1.30` maps each
# archetype onto a proportional shift of the per-category research
# prior. Frozen at launch.
_ARCHETYPE_SCALING_ANCHOR = 1.30


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


# ---------------------------------------------------------------------------
# Phase C (2026-04-22): archetype-prior shrinkage blend.
#
# blend() is the canonical `bias_factor_final` computation per MANIFESTO
# v1.10 Rule 13. Every user-facing surface that consumes bias_factor
# (calibration_nudge, insights, future scheduler auto-sizing) MUST call
# blend() — not `_adaptive_calibration` directly, which returns only the
# personal-cascade portion of the formula.
#
# The canonical formula:
#   personal_weight          = min(1.0, n_sessions_in_cell / 30)
#   archetype_scaling        = archetype.prior_bias_factor / 1.30
#   archetype_prior_for_cell = RESEARCH_PRIORS[category].bias_factor
#                            × archetype_scaling
#   bias_factor_final        = (1 − personal_weight) × archetype_prior_for_cell
#                            + personal_weight × personal_sum_ratio_for_cell
#
# Anything that deviates from this formula without a Rule-13 amendment
# is a pre-registration protocol violation.
# ---------------------------------------------------------------------------


def _archetype_prior_for_cell(
    archetype: Archetype, category: str
) -> tuple[float, str]:
    """Compute archetype_prior_for_cell via the composite scaling rule.

    Returns (prior_value, citation_label). citation_label is the
    RESEARCH_PRIORS citation string with the archetype appended so the
    diagnostic panel can display both sources in one line.
    """
    research_prior_entry = RESEARCH_PRIORS.get(category, RESEARCH_PRIOR_DEFAULT)
    research_prior = research_prior_entry["bias_factor"]
    archetype_scaling = archetype.prior_bias_factor / _ARCHETYPE_SCALING_ANCHOR
    prior_value = research_prior * archetype_scaling
    return prior_value, research_prior_entry["citation"]


def blend(
    db: Session,
    user_id: int,
    tasks: list[Task],
    category: str,
    tod: str,
    planned_minutes: int,
) -> dict:
    """Canonical `bias_factor_final` computation per MANIFESTO Rule 13.

    Layered on top of `_adaptive_calibration` — preserves the full
    personal-cascade metadata (signal_level, signals array, confidence
    tier) and adds the shrinkage-blend fields the frontend consumes.

    Contract:
      - Returns the same shape as _adaptive_calibration, PLUS:
          bias_factor_final          — the blended scalar (canonical)
          personal_weight            — min(1.0, n/30)
          prior_weight               — 1 - personal_weight
          archetype_id               — which archetype was blended in
          archetype_prior_for_cell   — the scaled research prior
          archetype_scaling          — the composite scaling multiplier
          archetype_prior_citation   — research-prior source label

    When the user has no ArchetypeAssignment, archetype_id resolves to
    `diffuse_average` (population midpoint) per Rule 13. When the user
    has a completed=False skip-defaulted assignment, archetype_id on
    User.archetype_id was also set to diffuse_average; same behavior.
    """
    clean_ids = baseline_clean_task_ids(
        db,
        tasks=tasks,
        signal_targets=["planning_estimate", "duration_behavior"],
    )
    clean_tasks = [t for t in tasks if t.task_id in clean_ids]

    personal = _adaptive_calibration(clean_tasks, category, tod, planned_minutes)

    # Personal cell magnitude — use the cascade's winning bias_factor,
    # regardless of whether it was personal or research fallback. This
    # is the `personal_sum_ratio_for_cell` term in the Rule 13 formula.
    # For cold-start users (cascade returns research prior), the blend
    # still works — personal_weight is 0, so the archetype_prior term
    # fully dominates. The "double research prior" concern does not
    # apply because the research prior IS part of the archetype prior
    # via the composite scaling rule; the personal branch at weight 0
    # contributes nothing.
    personal_value = personal["cell"]["bias_factor"]
    n = personal["cell"]["sessions"]

    personal_weight = min(1.0, n / 30.0)
    prior_weight = 1.0 - personal_weight

    # Look up archetype. User.archetype_id is nullable; default to
    # Diffuse Average per Rule 13 skip-path semantics.
    user = db.query(User).filter(User.user_id == user_id).first()
    archetype_id = (user.archetype_id if user else None) or DIFFUSE_AVERAGE_ID
    archetype = (
        db.query(Archetype)
        .filter(Archetype.archetype_id == archetype_id)
        .first()
    )
    # Defensive: if the archetype_id on the user doesn't match any row
    # (shouldn't happen — FK enforced — but belt-and-suspenders), fall
    # back to Diffuse Average.
    if archetype is None:
        archetype = (
            db.query(Archetype)
            .filter(Archetype.archetype_id == DIFFUSE_AVERAGE_ID)
            .first()
        )

    archetype_prior_for_cell, citation = _archetype_prior_for_cell(
        archetype, category
    )
    archetype_scaling = archetype.prior_bias_factor / _ARCHETYPE_SCALING_ANCHOR

    bias_factor_final = (
        prior_weight * archetype_prior_for_cell
        + personal_weight * personal_value
    )

    return {
        **personal,
        "bias_factor_final": round(bias_factor_final, 3),
        "personal_weight": round(personal_weight, 3),
        "prior_weight": round(prior_weight, 3),
        "archetype_id": archetype.archetype_id,
        "archetype_prior_bias_factor": round(archetype.prior_bias_factor, 3),
        "archetype_prior_for_cell": round(archetype_prior_for_cell, 3),
        "archetype_scaling": round(archetype_scaling, 3),
        "archetype_prior_citation": citation,
    }
