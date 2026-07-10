"""JWT decoding for the multi-user web frontend.

The Next.js frontend (next-auth) mints an HS256 JWT at login time using
the shared JWT_SECRET. This module decodes that token, validates it,
and resolves it to a `User` row — auto-provisioning the row on first
sight (signup-by-first-login, gated only by Google having vouched for
the email).

History note (2026-04-27 cleanup): an earlier shape of this module also
seeded a "plan your week" starter task for fresh users (`_seed_starter_task`).
Per Apr 25 strategic decision (`docs/strategic_decisions_april_24.md` +
`memory/project_relief_instrument_reframe.md`), the seeded task poisoned the
activation funnel — u12 and u14 both abandoned the placeholder rather than
engaging. The call sites were stripped Apr 26 (commit `51aa69c`); the function
definition + its dedicated test file (`test_starter_task_schedule.py`) were
removed Apr 27 to delete the dead path entirely. Real activation is the
job of Family F1 chaos capture, not a placeholder seeded task.

Performance note (2026-04-26 / commit `51aa69c`):
`resolve_user_from_token` is synchronous (Postgres query). The middleware
in `app/main.py` MUST wrap calls in `run_in_threadpool` so the ASGI event
loop is not blocked during signup fan-out. There should be exactly ONE
call site of this function (the middleware). If you find yourself calling
it elsewhere, wrap that path in `run_in_threadpool` too — otherwise you'll
re-introduce the latency the prior commit fixed.
"""
import os
from datetime import datetime
from typing import Optional

import jwt
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.models import User
from app.db.session import SessionLocal


DEFAULT_JWT_SECRET = "dev-only-replace-me-with-32-byte-urlsafe-secret"
MIN_RUNTIME_JWT_SECRET_LENGTH = 32
PRODUCTION_ENVIRONMENTS = {"production", "prod"}
JWT_DECODE_CLOCK_SKEW_SECONDS = 10
LEGACY_PLACEHOLDER_GOOGLE_IDS = {"simulated-google-sub"}


def runtime_requires_strong_jwt_secret() -> bool:
    """True when weak JWT secrets would be a production security risk.

    Local/dev/test environments keep the historical default so lightweight
    tests can mint tokens without secrets. Public or production topology must
    fail closed before accepting bearer identity.
    """
    env = (settings.ENVIRONMENT or "").strip().lower()
    frontend_url = (settings.FRONTEND_URL or "").strip().rstrip("/").lower()
    return env in PRODUCTION_ENVIRONMENTS or frontend_url in {
        "https://lyraos.org",
        "https://lyraos.org",
    }


def is_weak_jwt_secret(secret: Optional[str]) -> bool:
    value = (secret or "").strip()
    return (
        not value
        or value == DEFAULT_JWT_SECRET
        or len(value) < MIN_RUNTIME_JWT_SECRET_LENGTH
    )


def validate_runtime_jwt_secret() -> None:
    """Reject public/prod runtime when bearer identity can be forged.

    The frontend signs backend bearer tokens with NEXTAUTH_SECRET while the
    backend verifies with JWT_SECRET. In production/public topology those
    values must be strong and, when both are visible to the backend process,
    identical.
    """
    if not runtime_requires_strong_jwt_secret():
        return
    if is_weak_jwt_secret(settings.JWT_SECRET):
        raise RuntimeError(
            "JWT_SECRET must be configured to a non-default value of at least "
            f"{MIN_RUNTIME_JWT_SECRET_LENGTH} characters in public runtime"
        )
    nextauth_secret = os.environ.get("NEXTAUTH_SECRET")
    if nextauth_secret is not None and nextauth_secret != settings.JWT_SECRET:
        raise RuntimeError(
            "NEXTAUTH_SECRET and JWT_SECRET must match in public runtime"
        )


def decode_token(token: str) -> dict:
    validate_runtime_jwt_secret()
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            leeway=JWT_DECODE_CLOCK_SKEW_SECONDS,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"invalid token: {e}")


def _clean_profile_name(value: object, *, max_length: int) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None
    return cleaned[:max_length]


def _first_name_from_display_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    first = value.split()[0].strip(".,;:()[]{}")
    return first[:80] if first else None


def resolve_user_from_token(token: str) -> User:
    """Decode the JWT and return the matching User, creating it on first login.

    Race-safe provisioning: when a new user signs in, the frontend fan-out
    fires 5+ concurrent requests; without protection they ALL see user=None
    and all try to INSERT, hitting the email unique constraint. We wrap the
    insert in try/except IntegrityError + re-query; whichever request wins,
    the others adopt the existing row.

    Synchronous on purpose — call sites MUST wrap in `run_in_threadpool`
    (see module docstring). The single canonical caller is the
    `UserScopeMiddleware` in `app/main.py`.
    """
    payload = decode_token(token)
    email = payload.get("email")
    google_id = payload.get("sub") or payload.get("google_id")
    google_display_name = _clean_profile_name(payload.get("name"), max_length=120)
    google_first_name = _clean_profile_name(
        payload.get("given_name"), max_length=80
    ) or _first_name_from_display_name(google_display_name)
    if not email:
        raise HTTPException(status_code=401, detail="token missing email claim")

    db = SessionLocal()
    try:
        user: Optional[User] = db.query(User).filter(User.email == email).first()
        if user is None:
            try:
                user = User(
                    email=email,
                    google_id=google_id,
                    google_display_name=google_display_name,
                    google_first_name=google_first_name,
                    timezone="Africa/Cairo",
                    is_operator=False,
                    notion_enabled=False,
                    created_at=datetime.utcnow(),
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                from app.services.security_audit import write_security_audit_event

                write_security_audit_event(
                    event_type="user_provisioned",
                    surface="auth.jwt",
                    status="success",
                    actor_user_id=user.user_id,
                    user_id=user.user_id,
                    target_type="user",
                    target_id=f"user:{user.user_id}",
                    redacted_metadata={"identity_provider": "google"},
                )
                from app.services.user_mailer import (
                    record_activation_email_result,
                    send_activation_email,
                )

                mail_result = send_activation_email(user)
                record_activation_email_result(user.user_id, mail_result)
            except IntegrityError:
                # Concurrent signup race: another request beat us to the
                # INSERT and committed first. Roll back our failed transaction
                # and re-query; the other request's row is the canonical one.
                db.rollback()
                user = (
                    db.query(User).filter(User.email == email).first()
                )
                if user is None:
                    # Truly unexpected — IntegrityError without a winning
                    # row. Surface as 500 so the failure is loud.
                    raise HTTPException(
                        status_code=500,
                        detail="user provisioning failed (race-recovery)",
                    )
        else:
            changed = False
            if (
                google_id
                and google_id != user.google_id
                and (
                    user.google_id is None
                    or user.google_id in LEGACY_PLACEHOLDER_GOOGLE_IDS
                )
            ):
                # Backfill google_id on pre-OAuth rows or known legacy fixtures.
                user.google_id = google_id
                changed = True
            if google_display_name and user.google_display_name != google_display_name:
                user.google_display_name = google_display_name
                changed = True
            if google_first_name and user.google_first_name != google_first_name:
                user.google_first_name = google_first_name
                changed = True
            if changed:
                db.commit()
                db.refresh(user)
                try:
                    from app.utils.me_cache import invalidate_me

                    invalidate_me(user.user_id)
                except Exception:
                    pass
        return user
    finally:
        db.close()
