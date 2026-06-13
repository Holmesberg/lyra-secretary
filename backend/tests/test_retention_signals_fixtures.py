"""
Fixture correctness tests for retention signals surfaced by LYR-098.

Validates the computation of:
  - micro_mirror          (stopwatch_manager._compute_micro_mirror)
  - calibration_nudge     (stopwatch_manager._compute_calibration_nudge)
  - bias_factor cell      (analytics._bias_cell)

Precondition for any UI surfacing per `docs/building_phases.md` §Phase 4.5
Tier 1 "Fixture tests for retention signals" and `MANIFESTO.md` §Shipping
Philosophy — Scope of the retention-before-polish principle: insight
correctness does not defer to retention polish (Li 2010, Epstein 2015).
"""
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.endpoints.analytics import _bias_cell
from app.db.models import Task, TaskState
from app.services.stopwatch_manager import (
    _compute_calibration_nudge,
    _compute_micro_mirror,
)
from app.utils.time_utils import now_utc


@pytest.fixture(autouse=True)
def _clean_tasks(db):
    """Wipe the `task` table before each test — the conftest in-memory
    engine is a shared singleton across the suite, so rows leak."""
    db.execute(text("DELETE FROM task"))
    db.commit()
    yield


# ---------------------------------------------------------------------------
# micro_mirror — pure function over task field values
# ---------------------------------------------------------------------------

def _mm(delay=None, delta=None, duration=0, pauses=0, planned=None):
    t = MagicMock(spec=Task)
    t.initiation_delay_minutes = delay
    t.duration_delta_minutes = delta
    t.executed_duration_minutes = duration
    t.pause_count = pauses
    t.planned_duration_minutes = planned
    return t


def test_mm_initiation_late_fires_above_10():
    assert _compute_micro_mirror(_mm(delay=15)) == "Started 15 min late."
    assert _compute_micro_mirror(_mm(delay=11)) == "Started 11 min late."


def test_mm_initiation_boundary_at_10_does_not_fire_late():
    # delay == 10 is NOT > 10 → falls through
    assert _compute_micro_mirror(_mm(delay=10, delta=None, duration=0, pauses=0)) is None


def test_mm_initiation_on_time_at_zero_and_negative():
    assert _compute_micro_mirror(_mm(delay=0)) == "Started on time."
    assert _compute_micro_mirror(_mm(delay=-7)) == "Started on time."


def test_mm_initiation_mid_range_falls_through():
    # delay in (0, 10] — neither late branch nor on-time branch fires
    t = _mm(delay=5, delta=None, duration=0, pauses=0)
    assert _compute_micro_mirror(t) is None


def test_mm_delta_overrun():
    assert _compute_micro_mirror(_mm(delta=-25)) == "Ran 25 min over plan."


def test_mm_delta_early():
    assert _compute_micro_mirror(_mm(delta=30)) == "Finished 30 min early."


def test_mm_delta_boundary_at_20_does_not_fire():
    # delta == -20 is NOT < -20; delta == 20 is NOT > 20
    assert _compute_micro_mirror(_mm(delta=-20)) is None
    assert _compute_micro_mirror(_mm(delta=20)) is None


def test_mm_zero_pauses_long_session():
    # Neutralized text per notification_patterns.md §No guilt.
    assert _compute_micro_mirror(_mm(pauses=0, duration=45)) == "0 pauses this session."


def test_mm_zero_pauses_short_session_does_not_fire():
    # duration == 30 is NOT > 30 → falls through
    assert _compute_micro_mirror(_mm(pauses=0, duration=30)) is None
    assert _compute_micro_mirror(_mm(pauses=0, duration=15)) is None


def test_mm_many_pauses():
    # Neutralized text — no "fragmented" framing.
    assert _compute_micro_mirror(_mm(pauses=3)) == "3 pauses this session."
    assert _compute_micro_mirror(_mm(pauses=7)) == "7 pauses this session."


def test_mm_all_null_returns_none():
    t = _mm(delay=None, delta=None, duration=None, pauses=None, planned=None)
    assert _compute_micro_mirror(t) is None


def test_mm_fallback_overrun_shows_ratio():
    t = _mm(delay=5, delta=-10, duration=68, pauses=1, planned=45)
    assert _compute_micro_mirror(t) == "Planned 45 min, took 68 — 1.51× your estimate."


def test_mm_fallback_on_target():
    t = _mm(delay=5, delta=-3, duration=30, pauses=1, planned=30)
    assert _compute_micro_mirror(t) == "Planned 30 min, took 30 — right on target."


def test_mm_fallback_finished_early():
    t = _mm(delay=5, delta=10, duration=20, pauses=0, planned=30)
    assert _compute_micro_mirror(t) == "Planned 30 min, finished in 20."


def test_mm_priority_initiation_late_beats_delta():
    # delay > 10 AND delta < -20 → initiation branch wins
    assert _compute_micro_mirror(_mm(delay=20, delta=-40)) == "Started 20 min late."


def test_mm_priority_initiation_on_time_beats_delta():
    # delay <= 0 AND delta < -20 → initiation branch wins
    assert _compute_micro_mirror(_mm(delay=0, delta=-40)) == "Started on time."


def test_mm_priority_delta_beats_pauses():
    # delta < -20 AND pauses >= 3 → delta branch wins
    assert _compute_micro_mirror(_mm(delta=-30, pauses=5)) == "Ran 30 min over plan."


def test_mm_priority_zero_pauses_long_session_beats_many_pauses_branch():
    # pauses==0 and duration>30 fires BEFORE the pauses>=3 check
    # (both branches can't fire simultaneously but confirms ordering)
    assert _compute_micro_mirror(_mm(pauses=0, duration=60)) == "0 pauses this session."


def test_mm_pause_overhead_dominates_day_footprint():
    metrics = MagicMock()
    metrics.execution_time_minutes = 62
    metrics.session_span_minutes = 190
    metrics.pause_overhead_minutes = 128

    assert _compute_micro_mirror(_mm(delta=-5, duration=62, pauses=2), metrics) == (
        "Active work: 62 min. Session span: 3h 10m. Pause overhead: 2h 08m."
    )


# ---------------------------------------------------------------------------
# calibration_nudge — reads same-category history from DB
# ---------------------------------------------------------------------------

_TEST_USER_ID = 901  # isolated namespace — avoids collisions with other tests


def _seed(
    db: Session,
    *,
    delta=0,
    category="dev",
    state=TaskState.EXECUTED,
    initiation_status="on_time",
    voided_at=None,
    null_delta=False,
) -> Task:
    """
    Seed a Task where `duration_delta_minutes` (a computed @property) equals
    the requested `delta`. The property returns `planned - executed`, so we
    hold planned=60 and compute executed = planned - delta. If `null_delta`
    is True, we leave `executed_duration_minutes=None` so the property
    returns None.

    `initiation_status` defaults to "on_time" because the helper's SQL
    filter `Task.initiation_status != "system_error"` silently drops NULL
    rows in SQL trinary logic — production rows carry a real value.
    """
    start = now_utc()
    planned = 60
    executed = None if null_delta else planned - delta
    task = Task(
        title="t",
        planned_start_utc=start,
        planned_end_utc=start,
        planned_duration_minutes=planned,
        executed_duration_minutes=executed,
        state=state,
        category=category,
        initiation_status=initiation_status,
        voided_at=voided_at,
        user_id=_TEST_USER_ID,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def test_cn_below_n3_returns_none(db):
    current = _seed(db, delta=-15)
    _seed(db, delta=-10)
    _seed(db, delta=-5)
    assert _compute_calibration_nudge(current, db) is None


def test_cn_fires_at_n3_exact_format(db):
    current = _seed(db, delta=-15)
    # 3 history rows, avg = (-5 + -10 + -15) / 3 = -10 exactly
    for d in [-5, -10, -15]:
        _seed(db, delta=d)
    nudge = _compute_calibration_nudge(current, db)
    assert nudge == (
        "t ran 15 min over plan. "
        "Your 'dev' category avg: -10 min across 3 sessions. "
        "Prior 'dev' sessions ran over plan 3/3 times."
    )


def test_cn_direction_under_when_delta_positive(db):
    # delta > 0 means user finished early → direction "under"
    current = _seed(db, delta=20)
    for d in [-5, -10, -15]:
        _seed(db, delta=d)
    nudge = _compute_calibration_nudge(current, db)
    assert nudge is not None
    assert "ran 20 min under plan." in nudge


def test_cn_excludes_voided(db):
    current = _seed(db, delta=-15)
    for d in [-10, -5, -8]:
        _seed(db, delta=d, voided_at=now_utc())
    assert _compute_calibration_nudge(current, db) is None


def test_cn_excludes_system_error_initiation(db):
    current = _seed(db, delta=-15)
    for d in [-10, -5, -8]:
        _seed(db, delta=d, initiation_status="system_error")
    assert _compute_calibration_nudge(current, db) is None


def test_cn_excludes_non_executed_states(db):
    current = _seed(db, delta=-15)
    for d in [-10, -5, -8]:
        _seed(db, delta=d, state=TaskState.SKIPPED)
    assert _compute_calibration_nudge(current, db) is None


def test_cn_excludes_current_task(db):
    current = _seed(db, delta=-15)
    # Only 2 sibling rows — if current leaked in, n=3 and we'd get a string
    for d in [-10, -5]:
        _seed(db, delta=d)
    assert _compute_calibration_nudge(current, db) is None


def test_cn_isolates_by_category(db):
    current = _seed(db, category="dev", delta=-15)
    # 3 dev rows (should count) + 3 meetings rows (should not)
    for d in [-5, -10, -15]:
        _seed(db, category="dev", delta=d)
    for d in [40, 50, 60]:
        _seed(db, category="meetings", delta=d)
    nudge = _compute_calibration_nudge(current, db)
    assert nudge is not None
    assert "Your 'dev' category avg: -10 min across 3 sessions." in nudge
    assert "meetings" not in nudge


def test_cn_underestimate_count_mixed(db):
    current = _seed(db, delta=-15)
    # 5 history rows — 3 negative (underestimated), 2 positive (overestimated)
    for d in [-10, -5, -8, 5, 10]:
        _seed(db, delta=d)
    nudge = _compute_calibration_nudge(current, db)
    assert nudge is not None
    assert "Prior 'dev' sessions ran over plan 3/5 times." in nudge


def test_cn_no_category_returns_none(db):
    current = _seed(db, category=None, delta=-15)
    for d in [-10, -5, -8]:
        _seed(db, category=None, delta=d)
    assert _compute_calibration_nudge(current, db) is None


def test_cn_null_delta_on_current_returns_none(db):
    current = _seed(db, null_delta=True)
    for d in [-10, -5, -8]:
        _seed(db, delta=d)
    assert _compute_calibration_nudge(current, db) is None


def test_cn_filter_excludes_history_rows_with_null_executed_duration(db):
    """Regression: the SQL filter must exclude history rows where
    executed_duration_minutes is NULL. Before the filter fix (Commit 2a),
    the filter `Task.duration_delta_minutes != None` was a no-op on a
    Python @property — leaked rows would then crash `sum(...)` on None.
    After fix: filter uses the real column `executed_duration_minutes`.
    """
    current = _seed(db, delta=-15)
    # Two valid history rows — below threshold by themselves
    for d in [-10, -5]:
        _seed(db, delta=d)
    # One leaky row: state=EXECUTED but no executed_duration → delta None.
    # With the fix, it's filtered out → n=2 → None returned.
    # Without the fix, it would leak in → n=3 → crash in sum().
    _seed(db, null_delta=True)
    assert _compute_calibration_nudge(current, db) is None


# ---------------------------------------------------------------------------
# bias_factor — pure function over (planned, executed) pair lists
# ---------------------------------------------------------------------------

def test_bias_cell_below_min_n_returns_none():
    assert _bias_cell([(60, 70), (30, 35)], min_n=3) is None


def test_bias_cell_at_min_n_returns_cell():
    rows = [(60, 60), (30, 30), (45, 45)]
    cell = _bias_cell(rows, min_n=3)
    assert cell is not None
    assert cell["sessions"] == 3


def test_bias_cell_underestimates():
    # sum planned=180, sum executed=270 → 1.5
    rows = [(60, 90), (60, 90), (60, 90)]
    cell = _bias_cell(rows, min_n=3)
    assert cell["bias_factor"] == 1.5
    assert cell["bias_factor_mean"] == 1.5
    assert cell["interpretation"] == "underestimates"


def test_bias_cell_on_target():
    rows = [(60, 60), (30, 30), (45, 45)]
    cell = _bias_cell(rows, min_n=3)
    assert cell["bias_factor"] == 1.0
    assert cell["interpretation"] == "on target"


def test_bias_cell_on_target_boundaries():
    # 0.9 and 1.1 are inclusive "on target"
    rows_low = [(100, 90), (100, 90), (100, 90)]
    rows_high = [(100, 110), (100, 110), (100, 110)]
    assert _bias_cell(rows_low, min_n=3)["interpretation"] == "on target"
    assert _bias_cell(rows_high, min_n=3)["interpretation"] == "on target"


def test_bias_cell_overestimates():
    # sum planned=180, sum executed=90 → 0.5
    rows = [(60, 30), (60, 30), (60, 30)]
    cell = _bias_cell(rows, min_n=3)
    assert cell["bias_factor"] == 0.5
    assert cell["interpretation"] == "overestimates"


def test_bias_cell_weighted_vs_mean_diverge_on_long_session():
    """
    Two short 1:1 sessions + one long 2:1 session.
    sum_ratio = (10 + 10 + 200) / (10 + 10 + 100) = 220/120 ≈ 1.833
    mean_ratio = (1.0 + 1.0 + 2.0) / 3 ≈ 1.333
    """
    rows = [(10, 10), (10, 10), (100, 200)]
    cell = _bias_cell(rows, min_n=3)
    assert cell["bias_factor"] == 1.833
    assert cell["bias_factor_mean"] == 1.333


def test_bias_cell_zero_planned_returns_none():
    rows = [(0, 0), (0, 0), (0, 0)]
    assert _bias_cell(rows, min_n=3) is None


def test_bias_cell_reports_session_count():
    rows = [(60, 60)] * 5
    cell = _bias_cell(rows, min_n=3)
    assert cell["sessions"] == 5
