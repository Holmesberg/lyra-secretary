from __future__ import annotations

import pytest

from scripts.lyrasim.trace.hypotheses import (
    TraceHypothesis,
    collapse_competing_hypotheses,
)


def test_competing_hypotheses_collapse_to_unique_highest_score():
    result = collapse_competing_hypotheses(
        (
            TraceHypothesis("tab_abandoned", 0.82),
            TraceHypothesis("deep_reading", 0.41),
            TraceHypothesis("offline_notes", 0.36),
        )
    )

    assert result.collapsed is True
    assert result.selected_hypothesis_id == "tab_abandoned"
    assert result.selected_score == 0.82
    assert result.reason == "unique_highest_score"


def test_competing_hypotheses_tie_remains_unresolved():
    result = collapse_competing_hypotheses(
        (
            TraceHypothesis("interruption", 0.7),
            TraceHypothesis("deep_reading", 0.7),
        )
    )

    assert result.collapsed is False
    assert result.selected_hypothesis_id is None
    assert result.reason == "top_score_tie"


def test_competing_hypotheses_can_require_scenario_thresholds():
    result = collapse_competing_hypotheses(
        (
            TraceHypothesis("interruption", 0.56),
            TraceHypothesis("deep_reading", 0.52),
        ),
        min_score=0.7,
        min_margin=0.1,
    )

    assert result.collapsed is False
    assert result.reason == "top_score_below_min_score"

    close_margin = collapse_competing_hypotheses(
        (
            TraceHypothesis("interruption", 0.76),
            TraceHypothesis("deep_reading", 0.72),
        ),
        min_score=0.7,
        min_margin=0.1,
    )

    assert close_margin.collapsed is False
    assert close_margin.reason == "top_score_margin_below_min_margin"


def test_competing_hypotheses_reject_invalid_scores():
    with pytest.raises(ValueError, match="hypothesis_score_out_of_range"):
        collapse_competing_hypotheses(
            (
                TraceHypothesis("impossible", 1.2),
            )
        )
