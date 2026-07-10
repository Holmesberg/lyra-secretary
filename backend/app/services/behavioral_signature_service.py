"""Operator behavioral signature service boundary."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.behavioral_signature_aggregate import (
    analyze_behavioral_signature_aggregate,
)


def analyze_behavioral_signature(
    db: Session,
    user_id: int,
    args: dict,
) -> dict:
    """Return the operator-only behavioral signature aggregate."""
    return analyze_behavioral_signature_aggregate(db, user_id, args)
