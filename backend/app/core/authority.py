"""Authority ladder for user-facing and behavior-shaping surfaces.

Output surfaces already declare truth, usage, exposure, and clean-data metadata.
This module derives the smaller authority contract used by APIs, tests, and
frontend payloads without bloating the registry JSON.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Protocol


AUTHORITY_RUNGS: Final[tuple[str, ...]] = (
    "observed_trace",
    "derived_metric",
    "interpretation",
    "suggestion",
    "intervention",
    "adaptation",
    "mutation",
    "operator_only_action",
)


class SurfaceLike(Protocol):
    surface_id: str
    truth_class: str
    usage_class: str
    exposure_category: str
    operator_only: bool


@dataclass(frozen=True)
class SurfaceAuthority:
    authority_rung: str
    mutation_permission: str
    public_translator: str

    def as_dict(self) -> dict[str, str]:
        return {
            "authority_rung": self.authority_rung,
            "mutation_permission": self.mutation_permission,
            "public_translator": self.public_translator,
        }


def authority_for_surface(spec: SurfaceLike) -> SurfaceAuthority:
    if spec.operator_only:
        return SurfaceAuthority(
            authority_rung="operator_only_action",
            mutation_permission="operator_only",
            public_translator="operator_only",
        )

    if spec.truth_class == "trace":
        rung = "observed_trace"
    elif spec.truth_class == "metric":
        rung = "derived_metric"
    elif spec.truth_class == "intervention":
        rung = "intervention"
    elif spec.exposure_category == "scheduling_suggestion":
        rung = "suggestion"
    else:
        rung = "interpretation"

    mutation_permission = (
        "explicit_user_confirmation_required"
        if rung in {"suggestion", "intervention", "adaptation"}
        else "none"
    )
    return SurfaceAuthority(
        authority_rung=rung,
        mutation_permission=mutation_permission,
        public_translator="registered_surface_translator",
    )
