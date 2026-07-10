"""Operator behavioral signature service boundary.

This is a temporary strangler seam around the historical Jarvis aggregate
implementation. Non-Jarvis callers should depend on this module rather than
importing ``jarvis_tools`` directly. The implementation can move here in a
later R4 extraction without changing endpoint call sites.
"""

from __future__ import annotations

from sqlalchemy.orm import Session


def analyze_behavioral_signature(
    db: Session,
    user_id: int,
    args: dict,
) -> dict:
    """Return the operator-only behavioral signature aggregate."""
    from app.services.jarvis_tools import _exec_analyze_behavioral_signature

    return _exec_analyze_behavioral_signature(db, user_id, args)
