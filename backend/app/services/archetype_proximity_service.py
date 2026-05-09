"""Compute Bayesian posterior over the 5 archetypes from a user's recent task history.

Pre-registered MANIFESTO Rule 17 (2026-04-27 — VT-25 archetype-reveal no-RCT
measurement design). Replaces the static "Profile: Procrastinator" reveal
with a dynamic posterior view: "your last 14 days look most like
Procrastinator (78%), with shades of Sprinter (45%); a month ago you were
65/70 — pattern is consolidating toward Procrastinator."

Math (Rule 17 v1.15, April 27, 2026 — effective-sample-size correction):

    prior P(A_i) = 1/5  (uniform; population frequency unknown)

    For each EXECUTED task t in the user's lookback window where:
        t.state = EXECUTED
        t.voided_at IS NULL
        t.initiation_status != 'system_error'
        t.planned_duration_minutes >= 5     (Rule 13 floor)
        t.executed_duration_minutes IS NOT NULL

        observed_bf = executed_duration / planned_duration
        archetype_prior_for_cell_i =
            RESEARCH_PRIORS.get(category, RESEARCH_PRIOR_DEFAULT)["bias_factor"]
            × A_i.prior_bias_factor / 1.30
        likelihood_i = pdf( Normal(archetype_prior_for_cell_i, A_i.prior_sigma) )
                       evaluated at observed_bf

    log_posterior_i = log(prior_i) + ( Σ log(likelihood_i) ) / sqrt(N)
    posterior_i = softmax(log_posteriors)

The sqrt(N) damping is the Rule 17 v1.15 amendment. Tasks within a
single user's window are not iid (same user, week, project, measurement
protocol → strong within-cluster correlation). Treating them as
independent compounds evidence linearly across N tasks and rounds
saturated archetypes to 1.0000 after ~15–25 overrun-heavy samples —
which reads as identity rather than pattern. Kish-style ESS correction
treats the cluster as sqrt(N) effective independent observations,
honest about the iid violation while preserving evidence direction.
v1.13/v1.14 analyses were produced under the un-damped formula; future
analyses are tagged with their math version.

Numerical stability: log-space accumulation + logsumexp for normalization.
A 100-task input set won't underflow even when likelihoods are e^{-50}.

Reused infrastructure (do NOT duplicate):
    - RESEARCH_PRIORS dict from `bias_factor_service.py:84`
    - RESEARCH_PRIOR_DEFAULT from `bias_factor_service.py:92`
    - Archetype model rows seeded by alembic 015 (5 rows; queried at
      runtime so the values stay in lockstep with the DB and never drift
      from an inline copy).

Pure Python — no scipy dependency. Normal log-pdf and logsumexp
implemented inline below; both have well-known closed forms.
"""
import math
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Archetype, Task, TaskState
from app.services.bias_factor_service import RESEARCH_PRIORS, RESEARCH_PRIOR_DEFAULT
from app.services.exposure_ledger import baseline_clean_task


_LOG_2PI = math.log(2.0 * math.pi)

# Rule 17 v1.15 outlier winsorization. The archetype Normal-pdf priors
# span roughly bf ∈ [0.5, 2.5] — disciplined_lark μ=0.95 σ=0.15,
# procrastinator μ=1.80 σ=0.40. Observations far outside any archetype's
# mean ± a few σ are not informative about archetype identity; they're
# informative about something else the model can't read (scope inflation
# per VT-22, mid-task scope shifts, forgot-to-stop-timer artifacts).
# Treating them as iid Normal samples drives tight-σ archetypes to
# log-likelihood -∞, saturating the posterior on the only archetype
# wide enough to swallow the outlier (procrastinator at σ=0.40). Cap at
# [0.30, 3.0] so a single 9.2× overrun can't dominate the likelihood
# computation; the downstream analysis layer is responsible for handling
# scope-inflation-shaped events separately per the existing VT-22 path.
_BIAS_FACTOR_CAP_LOW = 0.30
_BIAS_FACTOR_CAP_HIGH = 3.0


def _normal_log_pdf(x: float, mu: float, sigma: float) -> float:
    """log of Normal(mu, sigma) pdf at x. Pure Python."""
    if sigma <= 0:
        # Defensive — shouldn't happen with the seeded archetype priors,
        # but guard against bad data so we don't crash a /me request.
        raise ValueError(f"sigma must be > 0, got {sigma}")
    z = (x - mu) / sigma
    return -0.5 * _LOG_2PI - math.log(sigma) - 0.5 * z * z


def _logsumexp(xs: list[float]) -> float:
    """Numerically-stable log(sum(exp(x) for x in xs)). Standard trick."""
    if not xs:
        return float("-inf")
    m = max(xs)
    if m == float("-inf"):
        return float("-inf")
    return m + math.log(sum(math.exp(x - m) for x in xs))


def _filter_qualifying_tasks(
    db: Session,
    user_id: int,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> list[Task]:
    """Return user's EXECUTED, non-voided tasks meeting Rule 13 cell filters.

    If start/end are None, no time filter applied (used by full-history
    cold-start callers). Both inclusive when provided.
    """
    q = db.query(Task).filter(
        Task.user_id == user_id,
        Task.state == TaskState.EXECUTED,
        Task.voided_at.is_(None),
        Task.initiation_status != "system_error",
        Task.planned_duration_minutes >= 5,
        Task.executed_duration_minutes.is_not(None),
    )
    if start is not None:
        q = q.filter(Task.executed_end_utc >= start)
    if end is not None:
        q = q.filter(Task.executed_end_utc < end)
    return [
        task
        for task in q.all()
        if baseline_clean_task(
            db,
            task=task,
            signal_targets=["planning_estimate", "duration_behavior"],
        )
    ]


def _compute_log_posteriors(
    tasks: list[Task],
    archetypes: list[Archetype],
) -> list[float]:
    """Core math: log-posterior per archetype given the task list.

    Returns a list aligned with `archetypes` (same order). Uniform prior
    (log(1/N)). Likelihood is Normal(archetype_prior_for_cell, sigma) evaluated
    at observed bias_factor (executed/planned). Per-archetype log-likelihoods
    are accumulated across tasks, then divided by sqrt(N_tasks) before the
    log-prior is added.

    The sqrt(N) damping is the Rule 17 v1.15 amendment (April 27, 2026):
    tasks within a single user's window are not iid. Same user, same week,
    same project, same measurement protocol → strong within-cluster
    correlation. Treating N=28 tasks as 28 independent observations made
    the posterior round to 1.0000 / 0.0000 at four decimals after ~15-25
    overrun-heavy tasks, which read as identity rather than pattern.
    Effective sample size correction (Kish 1965) treats the cluster as
    sqrt(N) effective independent samples — honest about the iid
    violation while preserving the directionality of the evidence.
    """
    n_archetypes = len(archetypes)
    log_prior = math.log(1.0 / n_archetypes) if n_archetypes else float("-inf")
    log_likelihoods = [0.0] * n_archetypes

    n_used = 0
    for t in tasks:
        # Defensive — should be filtered upstream, but guard so a single
        # bad row doesn't crash the whole posterior computation.
        if not t.planned_duration_minutes or not t.executed_duration_minutes:
            continue
        raw_bf = t.executed_duration_minutes / t.planned_duration_minutes
        # Winsorize per Rule 17 v1.15 — see _BIAS_FACTOR_CAP_* above.
        observed_bf = max(_BIAS_FACTOR_CAP_LOW, min(_BIAS_FACTOR_CAP_HIGH, raw_bf))
        cat_key = (t.category or "").lower()
        cat_prior_bf = RESEARCH_PRIORS.get(cat_key, RESEARCH_PRIOR_DEFAULT)["bias_factor"]
        for i, a in enumerate(archetypes):
            archetype_prior_for_cell = cat_prior_bf * a.prior_bias_factor / 1.30
            log_likelihoods[i] += _normal_log_pdf(
                observed_bf, archetype_prior_for_cell, a.prior_sigma
            )
        n_used += 1

    # Effective-sample-size damping — sqrt(N_used). When n_used == 0 the
    # likelihood sum is zero anyway; defensively divide by 1.
    scale = math.sqrt(n_used) if n_used > 0 else 1.0
    return [log_prior + (ll / scale) for ll in log_likelihoods]


def _normalize_posteriors(log_posteriors: list[float]) -> list[float]:
    """log-posteriors → normalized posteriors (sum to 1.0)."""
    if not log_posteriors:
        return []
    log_norm = _logsumexp(log_posteriors)
    return [math.exp(lp - log_norm) for lp in log_posteriors]


def _format_proximity(
    archetypes: list[Archetype], posteriors: list[float], n_tasks: int
) -> list[dict]:
    """Pack into the response dict shape. Sort by score desc, assign rank."""
    out = [
        {
            "archetype_id": a.archetype_id,
            "label": a.name,
            "score": round(p, 4),
            "n_tasks": n_tasks,
        }
        for a, p in zip(archetypes, posteriors)
    ]
    out.sort(key=lambda x: -x["score"])
    for i, row in enumerate(out):
        row["rank"] = i + 1
    return out


def compute_proximity(
    db: Session, user_id: int, lookback_days: int = 14
) -> list[dict]:
    """Return per-archetype posterior scores sorted by score desc.

    Cold start (no qualifying tasks in the window): returns uniform 1/N
    distribution so the frontend can render placeholders without
    special-casing nulls.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    tasks = _filter_qualifying_tasks(db, user_id, start=cutoff)
    archetypes = db.query(Archetype).order_by(Archetype.archetype_id).all()

    if not archetypes:
        return []

    if not tasks:
        # No data in window — uniform posterior with rank by archetype_id
        # alphabetical (deterministic; consumers can re-sort).
        n = len(archetypes)
        return [
            {
                "archetype_id": a.archetype_id,
                "label": a.name,
                "score": round(1.0 / n, 4),
                "rank": i + 1,
                "n_tasks": 0,
            }
            for i, a in enumerate(archetypes)
        ]

    log_posteriors = _compute_log_posteriors(tasks, archetypes)
    posteriors = _normalize_posteriors(log_posteriors)
    return _format_proximity(archetypes, posteriors, len(tasks))


def compute_proximity_in_range(
    db: Session, user_id: int, start: datetime, end: datetime
) -> list[dict]:
    """Same as compute_proximity but for an arbitrary (start, end) window.

    Used by `compute_proximity_trend` to compute the "prior window"
    posterior for the trend comparison.
    """
    tasks = _filter_qualifying_tasks(db, user_id, start=start, end=end)
    archetypes = db.query(Archetype).order_by(Archetype.archetype_id).all()

    if not archetypes:
        return []

    if not tasks:
        n = len(archetypes)
        return [
            {
                "archetype_id": a.archetype_id,
                "label": a.name,
                "score": round(1.0 / n, 4),
                "rank": i + 1,
                "n_tasks": 0,
            }
            for i, a in enumerate(archetypes)
        ]

    log_posteriors = _compute_log_posteriors(tasks, archetypes)
    posteriors = _normalize_posteriors(log_posteriors)
    return _format_proximity(archetypes, posteriors, len(tasks))


def compute_proximity_trend(
    db: Session,
    user_id: int,
    current_days: int = 14,
    prior_days: int = 14,
) -> dict:
    """Compute proximity for current window AND immediately-prior window.

    Returns both + delta per archetype. Powers the frontend "a month ago you
    were X — pattern is consolidating toward Y" copy.

    Time math:
        current window = [now - current_days, now]
        prior window   = [now - current_days - prior_days, now - current_days]
    """
    now = datetime.utcnow()
    cur_start = now - timedelta(days=current_days)
    pri_end = cur_start
    pri_start = pri_end - timedelta(days=prior_days)

    current = compute_proximity_in_range(db, user_id, start=cur_start, end=now)
    prior = compute_proximity_in_range(db, user_id, start=pri_start, end=pri_end)

    # Build delta map keyed by archetype_id (lists may have different
    # ordering since each is sorted by score desc).
    cur_by_id = {row["archetype_id"]: row["score"] for row in current}
    pri_by_id = {row["archetype_id"]: row["score"] for row in prior}
    delta_per_archetype = {
        aid: round(cur_by_id.get(aid, 0.0) - pri_by_id.get(aid, 0.0), 4)
        for aid in (set(cur_by_id) | set(pri_by_id))
    }

    return {
        "current": current,
        "prior": prior,
        "delta_per_archetype": delta_per_archetype,
        "current_window_days": current_days,
        "prior_window_days": prior_days,
    }
