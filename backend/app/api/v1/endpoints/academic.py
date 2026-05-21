"""Academic execution-intelligence endpoints.

V1 exposes a read-only pressure map from existing Lyra primitives. It
does not create tasks, mutate calendars, or persist academic content.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.scoping import get_current_user_id
from app.schemas.academic import AcademicPressureMapResponse
from app.services.academic_pressure import build_pressure_map
from app.services.output_surfaces import emit_surface_render

router = APIRouter()


def _count_by(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _pressure_map_exposure_snapshot(
    payload: AcademicPressureMapResponse,
) -> dict:
    """Return a redacted render snapshot for the exposure ledger.

    The public pressure map may show assignment titles and recovery copy. The
    long-lived exposure render only stores structural counts and authority
    context, so provider-derived titles/details do not become durable exhaust.
    """
    source_summary = payload.source_summary
    return {
        "schema_version": "academic_pressure_map_exposure_snapshot_v1",
        "surface_id": "academic.pressure_map",
        "truth_class": "interpretation",
        "surface_role": "diagnostic_planning_surface",
        "horizon_days": payload.horizon_days,
        "item_count": len(payload.items),
        "pressure_levels": _count_by(
            [item.pressure_level for item in payload.items]
        ),
        "trust_states": _count_by([item.trust_state for item in payload.items]),
        "complexity_tiers": _count_by(
            [item.complexity_tier for item in payload.items]
        ),
        "compression_kinds": _count_by(
            [point.kind for point in payload.compression_points]
        ),
        "recovery_actions": [
            option.action for option in payload.recovery_options
        ],
        "coverage_question_count": len(payload.coverage_questions),
        "estimated_low_minutes": payload.estimated_low_minutes,
        "estimated_high_minutes": payload.estimated_high_minutes,
        "source_summary": {
            "deadlines_total": source_summary.deadlines_total,
            "external_obligation_count": source_summary.moodle_deadlines,
            "native_obligation_count": source_summary.native_deadlines,
            "academic_task_count": source_summary.academic_task_count,
            "study_task_count": source_summary.study_task_count,
            "academic_task_minutes": source_summary.academic_task_minutes,
            "study_task_minutes": source_summary.study_task_minutes,
            "google_calendar_connected": (
                source_summary.google_calendar_connected
            ),
            "calendar_busy_minutes": source_summary.calendar_busy_minutes,
            "planned_lyra_minutes": source_summary.planned_lyra_minutes,
        },
    }


@router.get("/academic/pressure-map", response_model=AcademicPressureMapResponse)
def get_academic_pressure_map(
    horizon_days: int = Query(14, ge=1, le=30),
    db: Session = Depends(get_db),
) -> AcademicPressureMapResponse:
    """Return a low-authority academic pressure snapshot.

    The response is intentionally assumption-heavy: ranges, source
    summary, trust states, and warnings. It is a planning aid, not a
    clean behavioral observation or adaptive scheduling claim.
    """
    try:
        payload = build_pressure_map(db, horizon_days=horizon_days)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))

    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")

    try:
        emitted = emit_surface_render(
            db,
            surface_id="academic.pressure_map",
            user_id=uid,
            content_snapshot=_pressure_map_exposure_snapshot(payload),
            content_template_id="academic_pressure_map",
            initiative="system",
            trigger_source="academic.pressure_map",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="academic_pressure_exposure_logging_unavailable",
        )

    return payload.model_copy(
        update={
            "surface_id": emitted["surface_id"],
            "truth_class": emitted["truth_class"],
            "signal_targets": emitted["signal_targets"],
            "clean_profile": emitted["clean_profile"],
            "fallback_mode": emitted["fallback_mode"],
            "exposure_id": emitted["exposure_id"],
            "render_id": emitted["render_id"],
        }
    )
