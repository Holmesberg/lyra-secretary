"""Scenario registry for LyraSim."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from scripts.lyrasim.generators import baseet_resource_open_idle_45m
from scripts.lyrasim.generators import task_started_never_stopped
from scripts.lyrasim.models import ScenarioData


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    generator: Callable[[int], ScenarioData]
    scorer_names: tuple[str, ...]


SCENARIOS: dict[str, ScenarioDefinition] = {
    baseet_resource_open_idle_45m.SCENARIO_ID: ScenarioDefinition(
        scenario_id=baseet_resource_open_idle_45m.SCENARIO_ID,
        generator=baseet_resource_open_idle_45m.generate,
        scorer_names=("score_scenario",),
    ),
    task_started_never_stopped.SCENARIO_ID: ScenarioDefinition(
        scenario_id=task_started_never_stopped.SCENARIO_ID,
        generator=task_started_never_stopped.generate,
        scorer_names=("score_scenario",),
    ),
}


def get_scenario_definition(scenario_id: str) -> ScenarioDefinition:
    try:
        return SCENARIOS[scenario_id]
    except KeyError as exc:
        known = ", ".join(sorted(SCENARIOS))
        raise ValueError(f"unknown_scenario:{scenario_id}; known={known}") from exc


def generate_scenario(scenario_id: str, seed: int) -> ScenarioData:
    definition = get_scenario_definition(scenario_id)
    if not definition.scorer_names:
        raise ValueError(f"scenario_has_no_scorer:{scenario_id}")
    return definition.generator(seed)
