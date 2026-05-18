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
            content_snapshot=payload.model_dump(mode="json"),
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
