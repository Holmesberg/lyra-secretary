"""Operator-only product health dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, operator_user_from_scope
from app.db.models import User
from app.services.operator_dashboard_snapshot import operator_dashboard_snapshot
from app.utils.redis_client import RedisClient

router = APIRouter()


def _require_operator(db: Session, request: Request) -> User:
    return operator_user_from_scope(db, request=request)


@router.get("/operator/dashboard")
def operator_dashboard_v12(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Decision-grade cohort readiness snapshot.

    Operator-only. Read-only. Content-minimized. This endpoint answers whether
    the current product loop is ready for more trusted users.
    """
    _require_operator(db, request)
    return operator_dashboard_snapshot(
        db,
        redis_client_factory=RedisClient,
    )
