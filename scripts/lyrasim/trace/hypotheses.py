"""Simulator-only hypothesis scoring and collapse helpers.

This module is not product inference. It lets LyraSim model whether ambiguous
trace explanations remain unresolved or collapse to the highest scored
candidate for scoring/replay purposes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class TraceHypothesis:
    hypothesis_id: str
    score: float
    evidence: tuple[str, ...] = ()
    falsifiers: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class HypothesisCollapseResult:
    collapsed: bool
    selected_hypothesis_id: Optional[str]
    selected_score: Optional[float]
    runner_up_score: Optional[float]
    margin: Optional[float]
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def collapse_competing_hypotheses(
    hypotheses: tuple[TraceHypothesis, ...],
    *,
    min_score: float = 0.0,
    min_margin: float = 0.0,
) -> HypothesisCollapseResult:
    """Collapse to the unique highest-scoring hypothesis when supported.

    Ties remain unresolved. Optional score and margin thresholds let later
    scenarios demand more evidence, but the base collapse condition is a unique
    highest score.
    """

    if not hypotheses:
        return HypothesisCollapseResult(
            collapsed=False,
            selected_hypothesis_id=None,
            selected_score=None,
            runner_up_score=None,
            margin=None,
            reason="no_hypotheses",
        )

    for hypothesis in hypotheses:
        if not 0.0 <= hypothesis.score <= 1.0:
            raise ValueError(
                f"hypothesis_score_out_of_range:{hypothesis.hypothesis_id}"
            )

    ordered = sorted(
        hypotheses,
        key=lambda hypothesis: (-hypothesis.score, hypothesis.hypothesis_id),
    )
    top = ordered[0]
    runner_up = ordered[1] if len(ordered) > 1 else None
    runner_up_score = runner_up.score if runner_up is not None else None
    margin = top.score - runner_up.score if runner_up is not None else top.score

    tied_top = (
        runner_up is not None
        and runner_up.score == top.score
    )
    if tied_top:
        return HypothesisCollapseResult(
            collapsed=False,
            selected_hypothesis_id=None,
            selected_score=top.score,
            runner_up_score=runner_up_score,
            margin=0.0,
            reason="top_score_tie",
        )

    if top.score < min_score:
        return HypothesisCollapseResult(
            collapsed=False,
            selected_hypothesis_id=None,
            selected_score=top.score,
            runner_up_score=runner_up_score,
            margin=margin,
            reason="top_score_below_min_score",
        )

    if margin < min_margin:
        return HypothesisCollapseResult(
            collapsed=False,
            selected_hypothesis_id=None,
            selected_score=top.score,
            runner_up_score=runner_up_score,
            margin=margin,
            reason="top_score_margin_below_min_margin",
        )

    return HypothesisCollapseResult(
        collapsed=True,
        selected_hypothesis_id=top.hypothesis_id,
        selected_score=top.score,
        runner_up_score=runner_up_score,
        margin=margin,
        reason="unique_highest_score",
    )
