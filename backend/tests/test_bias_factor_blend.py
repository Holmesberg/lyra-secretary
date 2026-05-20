"""Tests for the Rule-13 archetype-prior shrinkage blend.

Covers the three acceptance criteria from the 2026-04-22 Phase C plan:

  * n=0  personal sessions → bias_factor_final == archetype_prior_for_cell
         (personal_weight = 0, prior_weight = 1)
  * n=30 personal sessions → bias_factor_final ≈ personal_value
         (personal_weight = 1, prior_weight = 0)
  * n=15 personal sessions → personal_weight = 0.5 (midpoint blend)

Plus:
  - Diffuse Average default when user has no archetype_id
  - Correct archetype lookup when user.archetype_id is set
  - Archetype scaling math (disciplined_lark scales research prior DOWN;
    procrastinator scales UP)
"""
from datetime import datetime, timedelta

import pytest

from app.db.models import Archetype, Task, TaskState, User
from app.services.bias_factor_service import (
    RESEARCH_PRIOR_DEFAULT,
    RESEARCH_PRIORS,
    _archetype_prior_for_cell,
    blend,
)
from tests.conftest import TestingSession


def _make_user(
    db, email: str, archetype_id: str | None = None
) -> User:
    u = User(
        email=email,
        google_id=None,
        timezone="Africa/Cairo",
        is_operator=False,
        notion_enabled=False,
        archetype_id=archetype_id,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _seed_archetypes(db) -> None:
    """Seed the 5 archetypes if not already present (test DB).

    In prod DB these are created by alembic 015; in the SQLite test
    DB (rebuilt per session) we need to insert them.
    """
    existing = db.query(Archetype).count()
    if existing >= 5:
        return
    rows = [
        ("disciplined_lark", "Disciplined Lark", 0.95, 0.15),
        ("disciplined_owl", "Disciplined Owl", 1.05, 0.20),
        ("diffuse_average", "Diffuse Average", 1.30, 0.30),
        ("procrastinator", "Procrastinator", 1.80, 0.40),
        ("lark_low_discipline", "Lark, Low Discipline", 1.50, 0.35),
    ]
    for aid, name, prior, sigma in rows:
        db.add(
            Archetype(
                archetype_id=aid,
                name=name,
                prior_bias_factor=prior,
                prior_sigma=sigma,
            )
        )
    db.commit()


def _make_tasks(
    db, user_id: int, count: int, category: str = "development",
    hour: int = 10,
    planned: int = 60, executed: int = 90,
) -> list[Task]:
    """Create N executed tasks for the user in a specific (cat, tod) cell.

    Default: development / morning (hour=10 → morning bucket),
    planned 60 min, executed 90 min. personal_sum_ratio = 90/60 = 1.5.
    """
    base = datetime(2026, 4, 1, hour, 0)
    created = []
    for i in range(count):
        start = base + timedelta(days=i)
        t = Task(
            task_id=f"test-task-{user_id}-{i}-{category}",
            title=f"task {i}",
            category=category,
            planned_start_utc=start,
            planned_end_utc=start + timedelta(minutes=planned),
            planned_duration_minutes=planned,
            created_at=start,
            executed_start_utc=start,
            executed_end_utc=start + timedelta(minutes=executed),
            executed_duration_minutes=executed,
            state=TaskState.EXECUTED,
            user_id=user_id,
            initiation_status="initiated",
        )
        db.add(t)
        created.append(t)
    db.commit()
    return created


# ---------------------------------------------------------------------------
# Archetype-prior-for-cell computation (composite scaling rule)
# ---------------------------------------------------------------------------

class TestArchetypePriorForCell:
    def test_diffuse_average_for_development_matches_research_prior(self):
        db = TestingSession()
        try:
            _seed_archetypes(db)
            archetype = (
                db.query(Archetype)
                .filter_by(archetype_id="diffuse_average")
                .first()
            )
            prior, _ = _archetype_prior_for_cell(archetype, "development")
            # Diffuse Average scaling = 1.30 / 1.30 = 1.0.
            # research_prior development = 1.50.
            # Therefore archetype_prior_for_cell = 1.50.
            assert abs(prior - 1.50) < 1e-9
        finally:
            db.close()

    def test_procrastinator_inflates_development_prior(self):
        db = TestingSession()
        try:
            _seed_archetypes(db)
            archetype = (
                db.query(Archetype)
                .filter_by(archetype_id="procrastinator")
                .first()
            )
            prior, _ = _archetype_prior_for_cell(archetype, "development")
            # Procrastinator scaling = 1.80 / 1.30 ≈ 1.3846
            # × 1.50 (development) ≈ 2.077
            assert 2.05 < prior < 2.10
        finally:
            db.close()

    def test_disciplined_lark_deflates_development_prior(self):
        db = TestingSession()
        try:
            _seed_archetypes(db)
            archetype = (
                db.query(Archetype)
                .filter_by(archetype_id="disciplined_lark")
                .first()
            )
            prior, _ = _archetype_prior_for_cell(archetype, "development")
            # Disciplined Lark scaling = 0.95 / 1.30 ≈ 0.7308
            # × 1.50 (development) ≈ 1.096
            assert 1.08 < prior < 1.12
        finally:
            db.close()

    def test_unknown_category_uses_default(self):
        db = TestingSession()
        try:
            _seed_archetypes(db)
            archetype = (
                db.query(Archetype)
                .filter_by(archetype_id="diffuse_average")
                .first()
            )
            prior, citation = _archetype_prior_for_cell(
                archetype, "uncategorized"
            )
            # Default = 1.35, diffuse scaling = 1.0, so 1.35.
            assert abs(prior - 1.35) < 1e-9
            assert "Kahneman" in citation
        finally:
            db.close()


# ---------------------------------------------------------------------------
# blend() — core Rule 13 fixtures
# ---------------------------------------------------------------------------

class TestBlendShrinkage:
    def test_n_zero_returns_archetype_prior_exactly(self):
        """No personal data → bias_factor_final == archetype_prior_for_cell."""
        db = TestingSession()
        try:
            _seed_archetypes(db)
            u = _make_user(db, "blend-n0@test.com")
            tasks: list[Task] = []
            result = blend(db, u.user_id, tasks, "development", "morning", 60)
            assert result["personal_weight"] == 0.0
            assert result["prior_weight"] == 1.0
            # Diffuse Average default → scaling 1.0 → 1.50 for development.
            assert abs(result["bias_factor_final"] - 1.50) < 1e-3
            assert result["archetype_id"] == "diffuse_average"
        finally:
            db.close()

    def test_n_thirty_returns_personal_exactly(self):
        """30+ personal sessions → personal_weight = 1.0, archetype prior ignored."""
        db = TestingSession()
        try:
            _seed_archetypes(db)
            u = _make_user(db, "blend-n30@test.com")
            # 30 tasks at development/morning, planned 60, executed 90
            # → personal_sum_ratio = 30×90 / 30×60 = 1.5
            _make_tasks(db, u.user_id, 30)
            tasks = db.query(Task).filter(Task.user_id == u.user_id).all()
            result = blend(db, u.user_id, tasks, "development", "morning", 60)
            assert result["personal_weight"] == 1.0
            assert result["prior_weight"] == 0.0
            # Personal sum-ratio = 1.5. Even though diffuse_average
            # prior for development is also 1.50, this test verifies
            # the mechanics — personal_weight=1.0 means the blend
            # takes the personal value regardless.
            assert abs(result["bias_factor_final"] - 1.5) < 1e-3
        finally:
            db.close()

    def test_n_fifteen_midpoint_blend(self):
        """15 personal sessions → personal_weight = 0.5 (linear-to-30 rule)."""
        db = TestingSession()
        try:
            _seed_archetypes(db)
            u = _make_user(db, "blend-n15@test.com")
            _make_tasks(db, u.user_id, 15)
            tasks = db.query(Task).filter(Task.user_id == u.user_id).all()
            result = blend(db, u.user_id, tasks, "development", "morning", 60)
            assert result["personal_weight"] == 0.5
            assert result["prior_weight"] == 0.5
            # personal = 1.5, archetype (diffuse) = 1.50 → blend = 1.5.
            # Construct explicit 50/50 check below with a different archetype.
        finally:
            db.close()

    def test_blend_mechanics_procrastinator_at_n15(self):
        """Archetype prior pulls high for procrastinator; personal pulls low."""
        db = TestingSession()
        try:
            _seed_archetypes(db)
            u = _make_user(db, "blend-proc@test.com", archetype_id="procrastinator")
            # Personal sum-ratio = 1.0 (perfect planner).
            _make_tasks(db, u.user_id, 15, planned=60, executed=60)
            tasks = db.query(Task).filter(Task.user_id == u.user_id).all()
            result = blend(db, u.user_id, tasks, "development", "morning", 60)
            # archetype_prior_for_cell = 1.50 × (1.80/1.30) ≈ 2.077
            # personal = 1.0
            # blend at w=0.5: 0.5 × 2.077 + 0.5 × 1.0 ≈ 1.538
            assert abs(result["bias_factor_final"] - 1.538) < 0.01
            assert result["personal_weight"] == 0.5
            assert result["archetype_id"] == "procrastinator"
        finally:
            db.close()


class TestBlendArchetypeFallback:
    def test_no_archetype_assigned_uses_diffuse_average(self):
        db = TestingSession()
        try:
            _seed_archetypes(db)
            u = _make_user(db, "blend-noarch@test.com", archetype_id=None)
            result = blend(db, u.user_id, [], "development", "morning", 60)
            assert result["archetype_id"] == "diffuse_average"
            assert abs(result["archetype_prior_bias_factor"] - 1.30) < 1e-9

        finally:
            db.close()

    def test_disciplined_lark_pulls_prior_below_research(self):
        db = TestingSession()
        try:
            _seed_archetypes(db)
            u = _make_user(db, "blend-lark@test.com", archetype_id="disciplined_lark")
            result = blend(db, u.user_id, [], "development", "morning", 60)
            # archetype_prior_for_cell should be ≈ 1.096 (below the
            # research prior 1.50 because Lark is disciplined).
            assert 1.08 < result["archetype_prior_for_cell"] < 1.12
            # With no personal data, bias_factor_final equals that.
            assert 1.08 < result["bias_factor_final"] < 1.12

        finally:
            db.close()


class TestBlendMetadataShape:
    def test_returns_all_rule_13_fields(self):
        db = TestingSession()
        try:
            _seed_archetypes(db)
            u = _make_user(db, "blend-shape@test.com")
            result = blend(db, u.user_id, [], "development", "morning", 60)
            # Rule 13 canonical fields:
            for key in (
                "bias_factor_final",
                "personal_weight",
                "prior_weight",
                "archetype_id",
                "archetype_prior_bias_factor",
                "archetype_prior_for_cell",
                "archetype_scaling",
                "archetype_prior_citation",
            ):
                assert key in result, f"missing Rule-13 field: {key}"
            # Cascade metadata (from _adaptive_calibration) preserved:
            for key in ("cell", "sessions", "signal_level", "signals", "source"):
                assert key in result, f"missing cascade field: {key}"
        finally:
            db.close()
