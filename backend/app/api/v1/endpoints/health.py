"""Health + environment-invariant probe endpoints.

The /health route is the standard liveness probe.

The /health/env-invariants route is a Lyra-specific probe that
catches recurring environment-assumption regressions before they
surface as user-visible bugs. Operator-locked 2026-04-29 after the
LYR-113 OAuth IPv4 incident (third recurrence) and the H0 tz hotfix
family — both were "the assumption held last week and silently broke
this week" failures.

Each invariant is a binary check; the response surfaces every
failure (not just first) so a single call tells you which assumptions
have drifted. Add new invariants here as new convention assumptions
are codified.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Request

from app.utils.time_utils import now_utc

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
def health_check():
    """Service health check."""
    return {"status": "ok", "service": "lyra-secretary"}


@router.get("/health/topology")
def topology_check(request: Request) -> dict[str, Any]:
    """Report the backend's runtime topology contract state."""
    from app.services.runtime_topology import backend_topology_report

    return backend_topology_report(request)


@router.get("/health/env-invariants")
def env_invariants() -> dict[str, Any]:
    """Probe Lyra's environment assumptions and report any drift.

    Each invariant returns ok=True/False with a brief detail string.
    Top-level `all_ok` is True iff every invariant holds.

    Add a new invariant when:
      - a recurring bug traces to an environment assumption that
        wasn't checked anywhere
      - a fix patches the symptom rather than the assumption
      - the operator's `feedback_*` memory codifies a convention
    """
    results: dict[str, dict[str, Any]] = {}

    # --- Invariant 1: now_utc() returns naive datetime
    # Why: Lyra's internal convention is naive-UTC. Subtractions
    # against aware datetimes raise TypeError. If now_utc() ever
    # starts returning aware (someone forgets the .replace(tzinfo=
    # None) at the end), every comparison site breaks at once.
    n = now_utc()
    results["now_utc_is_naive"] = {
        "ok": isinstance(n, datetime) and n.tzinfo is None,
        "detail": f"now_utc().tzinfo = {n.tzinfo!r}",
    }

    # --- Invariant 2: container clock vs Postgres now() agree within 60s
    # Why: tasks scheduled "now+30min" can land in the past if the
    # container clock drifts vs the DB. Catches systemic clock-drift
    # before it surfaces as start_in_past rejections.
    try:
        from sqlalchemy import text
        from app.db.session import SessionLocal
        from app.db.scoping import set_current_user_id

        original_uid = None
        try:
            from app.db.scoping import get_current_user_id

            original_uid = get_current_user_id()
        except Exception:
            pass
        set_current_user_id(None)
        db = SessionLocal()
        try:
            db_now = db.execute(text("SELECT now() AT TIME ZONE 'UTC'")).scalar()
            if db_now is not None and db_now.tzinfo is not None:
                db_now = db_now.replace(tzinfo=None)
            drift_seconds = abs((now_utc() - db_now).total_seconds()) if db_now else None
        finally:
            db.close()
        set_current_user_id(original_uid)
        results["clock_drift_under_60s"] = {
            "ok": drift_seconds is not None and drift_seconds < 60,
            "detail": f"|container_now - db_now| = {drift_seconds:.2f}s"
            if drift_seconds is not None
            else "db now() unavailable",
        }
    except Exception as e:
        results["clock_drift_under_60s"] = {
            "ok": False,
            "detail": f"clock probe raised: {e}",
        }

    # --- Invariant 3: pause-state Redis ISO roundtrip preserves naive
    # Why: H0 hotfix family. If Redis JSON encoding ever serialises
    # an aware datetime (instead of the naive convention), every
    # downstream `datetime.fromisoformat(pause_state["paused_at"])`
    # call returns aware and breaks subtraction.
    try:
        sample = now_utc()
        roundtripped = datetime.fromisoformat(sample.isoformat())
        results["redis_iso_roundtrip_preserves_naive"] = {
            "ok": roundtripped.tzinfo is None
            and abs((roundtripped - sample).total_seconds()) < 1,
            "detail": f"sample.tz={sample.tzinfo}, "
            f"roundtripped.tz={roundtripped.tzinfo}",
        }
    except Exception as e:
        results["redis_iso_roundtrip_preserves_naive"] = {
            "ok": False,
            "detail": f"roundtrip probe raised: {e}",
        }

    # --- Invariant 4: USER_TIMEZONE matches a real IANA zone
    # Why: settings.USER_TIMEZONE is read in to_utc / to_local. A
    # typo here (e.g. "Africa/Cario") fails silently for hours
    # because ZoneInfo raises only at first conversion attempt.
    try:
        from zoneinfo import ZoneInfo

        from app.core.config import settings

        ZoneInfo(settings.USER_TIMEZONE)
        results["user_timezone_valid"] = {
            "ok": True,
            "detail": f"USER_TIMEZONE={settings.USER_TIMEZONE!r}",
        }
    except Exception as e:
        results["user_timezone_valid"] = {
            "ok": False,
            "detail": f"USER_TIMEZONE invalid: {e}",
        }

    # --- Invariant 5: critical timestamp columns are TIMESTAMP (naive)
    # not TIMESTAMPTZ. The H0 hotfix attribution claimed Supabase
    # silently used TIMESTAMPTZ; the live DB shows otherwise. If a
    # future migration accidentally creates a TIMESTAMPTZ column,
    # SQLAlchemy will start returning aware datetimes for that
    # column and surface naive/aware errors at every read site.
    try:
        from sqlalchemy import text
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            tztz = db.execute(text("""
                SELECT table_name || '.' || column_name AS col
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND data_type = 'timestamp with time zone'
                ORDER BY table_name, column_name
                LIMIT 25
            """)).scalars().all()
        finally:
            db.close()
        results["all_timestamp_columns_naive"] = {
            "ok": not tztz,
            "detail": f"TIMESTAMPTZ columns found: {tztz}" if tztz else "all naive ✓",
        }
    except Exception as e:
        results["all_timestamp_columns_naive"] = {
            "ok": False,
            "detail": f"schema probe raised: {e}",
        }

    # --- Invariant 6: public runtime uses a strong shared JWT secret
    # Why: bearer/JWT is the runtime identity authority. In production
    # topology the backend must never accept tokens signed with a blank or
    # repository-default secret.
    try:
        from app.core.security import (
            is_weak_jwt_secret,
            runtime_requires_strong_jwt_secret,
        )
        from app.core.config import settings

        requires_strong = runtime_requires_strong_jwt_secret()
        weak = is_weak_jwt_secret(settings.JWT_SECRET)
        results["jwt_secret_strong_for_public_runtime"] = {
            "ok": (not requires_strong) or (not weak),
            "detail": (
                "public runtime requires strong JWT_SECRET"
                if requires_strong
                else "development runtime does not enforce public JWT secret strength"
            ),
        }
    except Exception as e:
        results["jwt_secret_strong_for_public_runtime"] = {
            "ok": False,
            "detail": f"jwt secret probe raised: {type(e).__name__}",
        }

    all_ok = all(v["ok"] for v in results.values())
    return {"all_ok": all_ok, "invariants": results}
