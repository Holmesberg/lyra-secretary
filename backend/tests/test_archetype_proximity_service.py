"""Unit tests for archetype_proximity_service.

Covers MANIFESTO Rule 17 (2026-04-27 — VT-25 dynamic-reveal data source).
"""
import math
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.models import Archetype, Task, TaskSource, TaskState, User
from app.db.scoping import set_current_user_id
from app.services.archetype_proximity_service import (
    _filter_qualifying_tasks,
    _logsumexp,
    _normal_log_pdf,
    compute_proximity,
    compute_proximity_in_range,
    compute_proximity_trend,
)


# Archetype priors per MANIFESTO Rule 13 (frozen, alembic 015)
ARCHETYPE_PRIORS = [
    ("disciplined_lark", "Disciplined Lark", 0.95, 0.15),
    ("disciplined_owl", "Disciplined Owl", 1.05, 0.20),
    ("diffuse_average", "Diffuse Average", 1.30, 0.30),
    ("procrastinator", "Procrastinator", 1.80, 0.40),
    ("lark_low_discipline", "Lark, Low Discipline", 1.50, 0.35),
]


@pytest.fixture(autouse=True)
def _clean_slate(db):
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM \"user\""))
    db.execute(text("DELETE FROM archetype"))
    db.commit()
    yield
    set_current_user_id(None)
    db.rollback()
    db.execute(text("DELETE FROM task"))
    db.execute(text("DELETE FROM \"user\""))
    db.execute(text("DELETE FROM archetype"))
    db.commit()


@pytest.fixture
def archetypes_seeded(db):
    """Seed the 5 archetype rows that alembic 015 normally provides."""
    for aid, name, bf, sigma in ARCHETYPE_PRIORS:
        db.add(Archetype(
            archetype_id=aid, name=name,
            prior_bias_factor=bf, prior_sigma=sigma,
        ))
    db.commit()


def _make_user(db, user_id: int = 77, email: str = "px@example.com") -> User:
    u = User(
        user_id=user_id, email=email,
        is_operator=False, notion_enabled=False,
        timezone="Africa/Cairo", created_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_task(
    db,
    user_id: int,
    planned: int,
    executed: int,
    category: str = "study",
    days_ago: int = 1,
    state: TaskState = TaskState.EXECUTED,
    voided: bool = False,
    initiation_status: str = "live",
) -> Task:
    """Seed an EXECUTED task with the given planned/executed durations."""
    base = datetime.utcnow() - timedelta(days=days_ago)
    t = Task(
        task_id=str(uuid4()),
        title="t",
        category=category,
        planned_start_utc=base,
        planned_end_utc=base + timedelta(minutes=planned),
        planned_duration_minutes=planned,
        executed_start_utc=base,
        executed_end_utc=base + timedelta(minutes=executed),
        executed_duration_minutes=executed,
        state=state,
        source=TaskSource.MANUAL,
        user_id=user_id,
        initiation_status=initiation_status,
        voided_at=datetime.utcnow() if voided else None,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


# ── Math primitives ──────────────────────────────────────────────


def test_normal_log_pdf_at_mean_matches_closed_form():
    """log-pdf at x=mu equals -log(sigma * sqrt(2*pi))."""
    sigma = 0.5
    expected = -math.log(sigma) - 0.5 * math.log(2 * math.pi)
    assert abs(_normal_log_pdf(1.0, 1.0, sigma) - expected) < 1e-12


def test_normal_log_pdf_two_sigma_offset():
    """At x = mu + 2*sigma, the z-term is 2 → -2."""
    mu, sigma = 1.0, 0.5
    val = _normal_log_pdf(mu + 2 * sigma, mu, sigma)
    expected = -math.log(sigma) - 0.5 * math.log(2 * math.pi) - 2.0
    assert abs(val - expected) < 1e-12


def test_normal_log_pdf_rejects_zero_sigma():
    with pytest.raises(ValueError):
        _normal_log_pdf(1.0, 1.0, 0.0)


def test_logsumexp_basic():
    """logsumexp([1,2,3]) = log(e + e^2 + e^3)."""
    assert abs(_logsumexp([1.0, 2.0, 3.0]) - math.log(math.e + math.e**2 + math.e**3)) < 1e-12


def test_logsumexp_handles_extreme_values():
    """logsumexp([-1000, -1001]) shouldn't underflow (the trick: subtract max)."""
    val = _logsumexp([-1000.0, -1001.0])
    expected = -1000.0 + math.log(1.0 + math.exp(-1.0))
    assert abs(val - expected) < 1e-12


def test_logsumexp_empty_returns_neg_inf():
    assert _logsumexp([]) == float("-inf")


# ── Cold start (no tasks) ────────────────────────────────────────


def test_cold_start_returns_uniform_posterior(db, archetypes_seeded):
    """User with zero qualifying tasks gets uniform 1/5 across archetypes."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    out = compute_proximity(db, user.user_id, lookback_days=14)
    assert len(out) == 5
    for row in out:
        assert abs(row["score"] - 0.20) < 1e-9
        assert row["n_tasks"] == 0


# ── Single task — closest-to-1.0 archetype wins ──────────────────


def test_observed_bf_one_favors_disciplined_lark(db, archetypes_seeded):
    """A single task with executed=planned (bf=1.0) gives the highest score
    to the archetype whose archetype_prior_for_cell is closest to 1.0.

    For category='study' (RESEARCH_PRIORS bf=1.40):
      disciplined_lark:    1.40 * 0.95/1.30 = 1.023
      disciplined_owl:     1.40 * 1.05/1.30 = 1.130
      diffuse_average:     1.40 * 1.30/1.30 = 1.400
      procrastinator:      1.40 * 1.80/1.30 = 1.938
      lark_low_discipline: 1.40 * 1.50/1.30 = 1.615

    Closest to observed_bf=1.0 is disciplined_lark (1.023).
    """
    user = _make_user(db)
    set_current_user_id(user.user_id)
    _make_task(db, user.user_id, planned=60, executed=60, category="study")

    out = compute_proximity(db, user.user_id, lookback_days=14)
    assert out[0]["archetype_id"] == "disciplined_lark"
    assert out[0]["rank"] == 1
    # Disciplined_lark has prior closest to observed → highest posterior
    # (likely well above uniform 0.2)
    assert out[0]["score"] > 0.20


# ── Many tasks matching procrastinator ───────────────────────────


def test_consistent_high_overrun_favors_procrastinator(db, archetypes_seeded):
    """10 tasks with executed = 2.0 * planned → procrastinator dominates.

    For category='work' (RESEARCH_PRIORS bf=1.45):
      procrastinator (1.80, σ=0.40):       prior_for_cell = 2.008
      lark_low_discipline (1.50, σ=0.35):  prior_for_cell = 1.673
      diffuse_average (1.30, σ=0.30):      prior_for_cell = 1.450

    At observed_bf=2.0, procrastinator's mean (2.008) is closest, so
    despite its larger σ it wins on log-likelihood. (At bf=1.8 the
    tighter-σ lark_low_discipline at 1.673 wins instead — that was the
    original test math error before this fix.)
    """
    user = _make_user(db)
    set_current_user_id(user.user_id)
    for i in range(10):
        _make_task(
            db, user.user_id, planned=30, executed=60,  # bf=2.0
            category="work", days_ago=i + 1,
        )

    out = compute_proximity(db, user.user_id, lookback_days=14)
    assert out[0]["archetype_id"] == "procrastinator"
    # 10 consistent observations → very confident
    assert out[0]["score"] > 0.50
    assert out[0]["n_tasks"] == 10


# ── voided / non-EXECUTED / planned-too-short exclusions ────────


def test_voided_tasks_excluded(db, archetypes_seeded):
    """Voided tasks don't contribute to the posterior."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    # 1 valid task pulling toward procrastinator (bf=2.0 — see math note
    # in test_consistent_high_overrun_favors_procrastinator)
    _make_task(db, user.user_id, planned=30, executed=60, category="work")
    # 5 voided tasks pulling toward disciplined_lark — should be ignored
    for _ in range(5):
        _make_task(
            db, user.user_id, planned=30, executed=30,
            category="work", voided=True,
        )

    out = compute_proximity(db, user.user_id, lookback_days=14)
    # Procrastinator wins since voided tasks were excluded
    assert out[0]["archetype_id"] == "procrastinator"
    assert out[0]["n_tasks"] == 1


def test_skipped_tasks_excluded(db, archetypes_seeded):
    """Only EXECUTED state contributes."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    _make_task(
        db, user.user_id, planned=30, executed=30,
        state=TaskState.SKIPPED,
    )
    out = compute_proximity(db, user.user_id, lookback_days=14)
    # Cold-start uniform since no EXECUTED tasks
    assert all(abs(row["score"] - 0.20) < 1e-9 for row in out)


def test_short_planned_tasks_excluded(db, archetypes_seeded):
    """Planned < 5 minutes excluded per Rule 13 floor."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    _make_task(db, user.user_id, planned=3, executed=3)  # below floor
    _make_task(db, user.user_id, planned=4, executed=4)  # below floor
    out = compute_proximity(db, user.user_id, lookback_days=14)
    # Cold start — no qualifying tasks
    assert all(row["n_tasks"] == 0 for row in out)


def test_system_error_initiation_excluded(db, archetypes_seeded):
    """initiation_status='system_error' excluded."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    _make_task(
        db, user.user_id, planned=30, executed=30,
        initiation_status="system_error",
    )
    out = compute_proximity(db, user.user_id, lookback_days=14)
    assert all(row["n_tasks"] == 0 for row in out)


# ── Category fallback ────────────────────────────────────────────


def test_category_not_in_research_priors_uses_default(db, archetypes_seeded):
    """Category like 'personal' uses RESEARCH_PRIOR_DEFAULT (1.35)."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    # observed_bf=1.0 → diffuse_average (1.30) is closest to default-anchored prior
    _make_task(db, user.user_id, planned=60, executed=60, category="personal")
    out = compute_proximity(db, user.user_id, lookback_days=14)
    # Just verify it didn't crash and produced a non-uniform posterior
    assert out[0]["score"] > 0.20
    assert out[0]["n_tasks"] == 1


def test_null_category_uses_default(db, archetypes_seeded):
    """Null category falls through to default safely."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    t = _make_task(db, user.user_id, planned=60, executed=60, category="study")
    t.category = None
    db.commit()
    # Should not crash
    out = compute_proximity(db, user.user_id, lookback_days=14)
    assert out[0]["n_tasks"] == 1


# ── Cross-user isolation ─────────────────────────────────────────


def test_cross_user_isolation(db, archetypes_seeded):
    """User A's tasks don't influence user B's posterior."""
    user_a = _make_user(db, user_id=77, email="a@x")
    user_b = _make_user(db, user_id=88, email="b@x")
    # User A: 5 tasks pulling procrastinator
    set_current_user_id(user_a.user_id)
    for i in range(5):
        _make_task(
            db, user_a.user_id, planned=30, executed=54,
            category="work", days_ago=i + 1,
        )
    # User B: 0 tasks
    set_current_user_id(user_b.user_id)
    out_b = compute_proximity(db, user_b.user_id, lookback_days=14)
    # User B is cold-start (uniform)
    assert all(abs(row["score"] - 0.20) < 1e-9 for row in out_b)
    assert all(row["n_tasks"] == 0 for row in out_b)


# ── Posterior properties ────────────────────────────────────────


def test_posterior_sums_to_one(db, archetypes_seeded):
    """Posteriors must sum to 1.0 ± floating-point epsilon."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    for i in range(8):
        _make_task(db, user.user_id, planned=30, executed=42, days_ago=i + 1)

    out = compute_proximity(db, user.user_id, lookback_days=14)
    total = sum(row["score"] for row in out)
    # Rounded to 4 decimals — tolerance reflects rounding
    assert abs(total - 1.0) < 1e-3


def test_log_stability_with_100_tasks(db, archetypes_seeded):
    """100 tasks shouldn't underflow the posterior to NaN.

    Without log-space accumulation, 100 likelihoods of e^{-5} multiply to
    e^{-500} ≈ 7e-218 — within Python float range but vulnerable to
    catastrophic precision loss. Log-space + logsumexp keeps it stable.
    """
    user = _make_user(db)
    set_current_user_id(user.user_id)
    for i in range(100):
        # Tasks 30 days back so we need a wider lookback
        _make_task(
            db, user.user_id, planned=30, executed=42,
            days_ago=i % 60 + 1,  # spread across 60 days so days_ago<=60
        )

    out = compute_proximity(db, user.user_id, lookback_days=90)
    # Every score should be a valid probability
    for row in out:
        assert 0.0 <= row["score"] <= 1.0
        assert not math.isnan(row["score"])
    # Total still ~ 1.0
    assert abs(sum(row["score"] for row in out) - 1.0) < 1e-3


# ── Trend computation ───────────────────────────────────────────


def test_trend_returns_current_prior_and_delta(db, archetypes_seeded):
    """compute_proximity_trend returns shape {current, prior, delta_per_archetype}."""
    user = _make_user(db)
    set_current_user_id(user.user_id)
    # Recent (last 7 days): tasks pulling procrastinator
    for i in range(5):
        _make_task(
            db, user.user_id, planned=30, executed=54,
            category="work", days_ago=i + 1,
        )
    # Prior window (8-21 days ago): tasks pulling disciplined_lark
    for i in range(5):
        _make_task(
            db, user.user_id, planned=30, executed=30,
            category="study", days_ago=i + 8,
        )

    out = compute_proximity_trend(
        db, user.user_id, current_days=7, prior_days=14,
    )
    assert "current" in out
    assert "prior" in out
    assert "delta_per_archetype" in out
    # Procrastinator should be HIGHER in current than in prior
    assert out["delta_per_archetype"]["procrastinator"] > 0
