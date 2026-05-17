"""Exposure acknowledgement endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.scoping import get_current_user_id
from app.services.output_surfaces import acknowledge_surface_render
from app.services.security_audit import write_security_audit_event

router = APIRouter()


class RenderAckRequest(BaseModel):
    acked_at: Optional[datetime] = None
    client_event_id: Optional[str] = Field(default=None, max_length=120)


class RenderAckResponse(BaseModel):
    ack_id: str
    exposure_id: str
    event_type: str
    user_id: int
    acked_at: datetime
    created: bool


@router.post(
    "/exposures/{exposure_id}/ack/render",
    response_model=RenderAckResponse,
)
def acknowledge_render(
    exposure_id: str,
    request: Request,
    body: RenderAckRequest | None = None,
    db: Session = Depends(get_db),
) -> RenderAckResponse:
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")

    body = body or RenderAckRequest()
    try:
        ack, created = acknowledge_surface_render(
            db,
            exposure_id=exposure_id,
            user_id=uid,
            acked_at=body.acked_at,
            client_event_id=body.client_event_id,
        )
        db.commit()
    except LookupError:
        db.rollback()
        write_security_audit_event(
            db=db,
            actor_user_id=uid,
            user_id=uid,
            event_type="cross_user_access_blocked",
            surface="/exposures/{exposure_id}/ack/render",
            target_type="exposure",
            target_id=exposure_id,
            status="denied",
            request=request,
            redacted_metadata={"reason": "not_found_or_out_of_scope"},
        )
        raise HTTPException(status_code=404, detail="exposure not found")
    except PermissionError:
        db.rollback()
        write_security_audit_event(
            db=db,
            actor_user_id=uid,
            user_id=uid,
            event_type="cross_user_access_blocked",
            surface="/exposures/{exposure_id}/ack/render",
            target_type="exposure",
            target_id=exposure_id,
            status="denied",
            request=request,
        )
        raise HTTPException(status_code=403, detail="exposure does not belong to user")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))

    return RenderAckResponse(
        ack_id=ack.ack_id,
        exposure_id=ack.exposure_id,
        event_type=ack.event_type,
        user_id=ack.user_id,
        acked_at=ack.acked_at,
        created=created,
    )
