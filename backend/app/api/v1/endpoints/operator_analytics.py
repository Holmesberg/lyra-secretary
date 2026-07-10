"""Operator-only analytics diagnostics routes.

These routes keep operator read-side diagnostics out of the mixed
user-facing analytics endpoint module. They preserve the existing public API
paths and remain read-only.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db, operator_user_from_scope
from app.db.models import User

router = APIRouter()


def _require_operator_analytics(db: Session, request: Request | None = None) -> User:
    return operator_user_from_scope(db, request=request)


@router.get("/analytics/behavioral_signature")
def get_behavioral_signature(
    request: Request,
    window_days: int = Query(14, ge=1, le=90, description="Look-back window in days"),
    db: Session = Depends(get_db),
) -> dict:
    """Operator-only aggregated fingerprint for dashboards and tooling."""
    op = _require_operator_analytics(db, request)
    from app.services.inference_engine import behavioral_signature_for_operator

    return behavioral_signature_for_operator(
        db, op.user_id, window_days=window_days
    )


@router.get("/analytics/cortex/diagnostics")
def get_cortex_diagnostics(
    request: Request,
    window_days: int = Query(30, ge=1, le=365, description="Look-back window in days"),
    db: Session = Depends(get_db),
) -> dict:
    """Operator-only Cortex Core v0 contract diagnostics."""
    op = _require_operator_analytics(db, request)
    from app.services.cortex import cortex_diagnostics
    from app.services.runtime_topology import backend_topology_report

    payload = cortex_diagnostics(db, user_id=op.user_id, window_days=window_days)
    payload["topology"] = backend_topology_report(request)
    return payload


@router.get("/analytics/output_surfaces/diagnostics")
def get_output_surface_diagnostics(
    request: Request,
    window_days: int = Query(30, ge=1, le=365, description="Look-back window in days"),
    db: Session = Depends(get_db),
) -> dict:
    """Operator-only output-surface enforcement diagnostics."""
    op = _require_operator_analytics(db, request)
    from app.services.output_surface_diagnostics import output_surface_diagnostics
    from app.services.runtime_topology import backend_topology_report

    payload = output_surface_diagnostics(db, user_id=op.user_id, window_days=window_days)
    payload["topology"] = backend_topology_report(request)
    return payload
