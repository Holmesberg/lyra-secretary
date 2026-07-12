"""Pure count-once demand and linked-coverage projection primitives."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


def _require_minutes(name: str, value: int) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer minute value")


@dataclass(frozen=True)
class MinuteEnvelope:
    low: int
    high: int

    def __post_init__(self) -> None:
        _require_minutes("low", self.low)
        _require_minutes("high", self.high)
        if self.low > self.high:
            raise ValueError("minute envelope low cannot exceed high")


@dataclass(frozen=True)
class DemandCoverageScenario:
    """One admissible joint scenario, with no independent endpoint mixing."""

    scenario_id: str
    total_estimate_minutes: int
    completed_scope_credit_minutes: int
    feasible_future_coverage_minutes: int

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("scenario_id must be non-empty")
        _require_minutes("total_estimate_minutes", self.total_estimate_minutes)
        _require_minutes(
            "completed_scope_credit_minutes",
            self.completed_scope_credit_minutes,
        )
        _require_minutes(
            "feasible_future_coverage_minutes",
            self.feasible_future_coverage_minutes,
        )


@dataclass(frozen=True)
class DemandCoverageScenarioResult:
    scenario_id: str
    total_estimate_minutes: int
    completed_scope_credit_minutes: int
    feasible_future_coverage_minutes: int
    remaining_demand_minutes: int
    applied_coverage_minutes: int
    unscheduled_demand_minutes: int
    overcoverage_minutes: int
    estimate_inconsistent: bool

    @property
    def identities_hold(self) -> bool:
        return (
            self.remaining_demand_minutes
            == self.applied_coverage_minutes + self.unscheduled_demand_minutes
            and self.feasible_future_coverage_minutes
            == self.applied_coverage_minutes + self.overcoverage_minutes
        )


@dataclass(frozen=True)
class DemandCoverageProjection:
    total_estimate: MinuteEnvelope
    completed_scope_credit: MinuteEnvelope
    feasible_future_coverage: MinuteEnvelope
    remaining_demand: MinuteEnvelope
    applied_coverage: MinuteEnvelope
    unscheduled_demand: MinuteEnvelope
    overcoverage: MinuteEnvelope
    scenario_results: tuple[DemandCoverageScenarioResult, ...]
    inconsistent_scenario_ids: tuple[str, ...]

    @property
    def scenario_count(self) -> int:
        return len(self.scenario_results)


def _project_scenario(
    scenario: DemandCoverageScenario,
) -> DemandCoverageScenarioResult:
    remaining = max(
        0,
        scenario.total_estimate_minutes
        - scenario.completed_scope_credit_minutes,
    )
    applied = min(remaining, scenario.feasible_future_coverage_minutes)
    unscheduled = max(0, remaining - scenario.feasible_future_coverage_minutes)
    overcoverage = max(
        0,
        scenario.feasible_future_coverage_minutes - remaining,
    )
    result = DemandCoverageScenarioResult(
        scenario_id=scenario.scenario_id,
        total_estimate_minutes=scenario.total_estimate_minutes,
        completed_scope_credit_minutes=scenario.completed_scope_credit_minutes,
        feasible_future_coverage_minutes=scenario.feasible_future_coverage_minutes,
        remaining_demand_minutes=remaining,
        applied_coverage_minutes=applied,
        unscheduled_demand_minutes=unscheduled,
        overcoverage_minutes=overcoverage,
        estimate_inconsistent=(
            scenario.completed_scope_credit_minutes
            > scenario.total_estimate_minutes
        ),
    )
    if not result.identities_hold:
        raise AssertionError("count-once demand and coverage identities failed")
    return result


def project_demand_coverage(
    scenarios: Iterable[DemandCoverageScenario],
) -> DemandCoverageProjection:
    """Project envelopes from complete admissible scenarios.

    Callers enumerate joint scenarios so this helper never fabricates an
    impossible combination by independently adding or subtracting endpoints.
    """

    scenario_list = tuple(scenarios)
    if not scenario_list:
        raise ValueError("at least one demand-coverage scenario is required")

    scenario_ids = [scenario.scenario_id for scenario in scenario_list]
    if len(set(scenario_ids)) != len(scenario_ids):
        raise ValueError("scenario_id values must be unique")

    results = tuple(_project_scenario(scenario) for scenario in scenario_list)

    def envelope(field: str) -> MinuteEnvelope:
        values = [int(getattr(result, field)) for result in results]
        return MinuteEnvelope(low=min(values), high=max(values))

    return DemandCoverageProjection(
        total_estimate=envelope("total_estimate_minutes"),
        completed_scope_credit=envelope("completed_scope_credit_minutes"),
        feasible_future_coverage=envelope("feasible_future_coverage_minutes"),
        remaining_demand=envelope("remaining_demand_minutes"),
        applied_coverage=envelope("applied_coverage_minutes"),
        unscheduled_demand=envelope("unscheduled_demand_minutes"),
        overcoverage=envelope("overcoverage_minutes"),
        scenario_results=results,
        inconsistent_scenario_ids=tuple(
            result.scenario_id
            for result in results
            if result.estimate_inconsistent
        ),
    )
