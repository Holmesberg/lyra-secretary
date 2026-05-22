"""Small, explicit data models for LyraSim V0."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class TraceEvent:
    event_type: str
    occurred_at_minute: int
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HiddenState:
    user_activity: str
    intended_activity: str
    notes: str

    def to_summary(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioData:
    scenario_id: str
    scenario_version: str
    scenario_origin: str
    seed: int
    synthetic_user_id: str
    hidden_state: HiddenState
    observable_trace: tuple[TraceEvent, ...]
    generator_assumptions: tuple[str, ...]
    coverage_limitations: tuple[str, ...]
    simulated_self_reports: tuple["SimulatedSelfReport", ...] = ()

    def trace_dicts(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.observable_trace]


@dataclass(frozen=True)
class CleanDataAdmission:
    profile: str
    admitted: bool
    reason: str


@dataclass(frozen=True)
class SimulatedSelfReport:
    hypothesis_id: str
    selected_option: str
    confirms_hypothesis: bool
    provenance: str
    calibration_use: str
    clean_data_eligible: bool
    notes: str

    def to_summary(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HypothesisCheckPrompt:
    hypothesis_id: str
    question_text: str
    options: tuple[str, ...]
    self_report_provenance: str
    calibration_use: str
    clean_data_eligible: bool


@dataclass(frozen=True)
class LyraOutput:
    stubbed: bool
    product_seams_exercised: tuple[str, ...]
    authority_rung: str
    text_outputs: tuple[str, ...]
    clean_data_admissions: tuple[CleanDataAdmission, ...]
    mutations_attempted: tuple[str, ...] = ()
    published_claim_tags: tuple[str, ...] = ()
    safe_actions: tuple[str, ...] = ()
    hypothesis_checks: tuple[HypothesisCheckPrompt, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["product_seams_exercised"] = list(self.product_seams_exercised)
        data["text_outputs"] = list(self.text_outputs)
        data["mutations_attempted"] = list(self.mutations_attempted)
        data["published_claim_tags"] = list(self.published_claim_tags)
        data["safe_actions"] = list(self.safe_actions)
        data["hypothesis_checks"] = [
            asdict(check)
            for check in self.hypothesis_checks
        ]
        return data


@dataclass(frozen=True)
class MetricValue:
    name: str
    numerator: int
    denominator: int
    value: Optional[float]
    status: str
    formula: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScoreResult:
    metrics: dict[str, MetricValue]
    failed_invariants: tuple[str, ...]

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "metrics": {
                name: metric.to_dict()
                for name, metric in sorted(self.metrics.items())
            },
            "failed_invariants": list(self.failed_invariants),
        }
