"""Academic pressure-map product seam adapter for LyraSim."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping

from scripts.lyrasim.models import CleanDataAdmission, LyraOutput, ScenarioData


def seed_baseet_deadlines_from_scenario(
    db,
    scenario: ScenarioData,
    *,
    user_id: int,
    base_time: datetime | None = None,
) -> list[Any]:
    """Create synthetic Baseet-like Deadline rows from a LyraSim scenario.

    This is a test-only product seam. Hidden state is deliberately ignored.
    The product receives only observable provider-deadline events.
    """
    from app.db.models import Deadline

    base_time = base_time or datetime.utcnow()
    rows: list[Any] = []
    for event in scenario.observable_trace:
        if event.event_type != "provider_deadline_observed":
            continue
        payload = event.payload
        row = Deadline(
            user_id=user_id,
            title=str(payload["title"]),
            due_at_utc=base_time + timedelta(days=int(payload["due_in_days"])),
            category_hint=str(payload.get("category_hint") or "academic"),
            state=str(payload.get("state") or "planned"),
            external_source=str(payload.get("external_source") or "baseet_mock"),
            external_id=str(payload["external_id_hash"]),
            imported_at=base_time,
        )
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def lyra_output_from_pressure_map_response(
    response: Mapping[str, Any],
    *,
    verified_rendered_exposure_id: str | None = None,
) -> LyraOutput:
    """Convert actual pressure-map output into LyraSim scorer input.

    The caller may claim the exposure-ledger seam only after independently
    reading browser-acknowledged render evidence from the product database.
    Delivery metadata in the response is intentionally insufficient.
    """
    recovery_actions = tuple(
        str(option.get("action"))
        for option in response.get("recovery_options", [])
        if option.get("action")
    )
    text_outputs = tuple(
        str(value)
        for value in (
            response.get("headline"),
            response.get("pressure_summary"),
            *(response.get("warnings") or ()),
        )
        if value
    )
    seams = ["academic_pressure.pressure_map"]
    exposure_id = response.get("exposure_id")
    if exposure_id and str(exposure_id) == verified_rendered_exposure_id:
        seams.append("output_surfaces.exposure_ledger")

    safe_action_type = (
        "confirm_coverage"
        if any(action == "confirm_coverage" for action in recovery_actions)
        else "none"
    )
    safe_actions = (
        ("confirm_coverage",)
        if safe_action_type == "confirm_coverage"
        else ()
    )

    return LyraOutput(
        stubbed=False,
        product_seams_exercised=tuple(seams),
        authority_rung=str(response.get("authority_rung") or "interpretation"),
        text_outputs=text_outputs,
        clean_data_admissions=(
            CleanDataAdmission(
                profile="planning_calibration",
                admitted=False,
                reason="academic_pressure_external_obligation",
            ),
            CleanDataAdmission(
                profile="measured_execution",
                admitted=False,
                reason="academic_pressure_external_obligation",
            ),
        ),
        published_claim_tags=(
            "external_obligation",
            "pressure_map",
            "trust_state",
        ),
        safe_actions=safe_actions,
        safe_action_type=safe_action_type,
        resolution_rung=(
            "clarify"
            if response.get("coverage_questions")
            else "suppress"
        ),
    )
