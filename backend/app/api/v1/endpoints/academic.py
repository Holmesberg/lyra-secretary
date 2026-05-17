"""Academic execution-intelligence endpoints.

V1 exposes a read-only pressure map from existing Lyra primitives. It
does not create tasks, mutate calendars, or persist academic content.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.academic import AcademicPressureMapResponse
from app.services.academic_pressure import build_pressure_map

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
        return build_pressure_map(db, horizon_days=horizon_days)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
