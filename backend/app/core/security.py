"""JWT decoding for the multi-user web frontend.

The Next.js frontend (next-auth) mints an HS256 JWT at login time using
the shared JWT_SECRET. This module decodes that token, validates it,
and resolves it to a `User` row — auto-provisioning the row on first
sight (signup-by-first-login, gated only by Google having vouched for
the email).

2026-04-21: on first-sign-in provisioning this module now also seeds a
starter planning task for the user (see `_seed_starter_task` below).
Replaces the full-screen onboarding surface that shipped earlier the
same day — per operator strategic pivot (docs/strategic_decisions_april_21.md
§5), the onboarding modal is commented out and the starter task lives
directly on /today so the user sees something real the moment they
land, without a forced UI flow.
"""
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Task, TaskSource, TaskState, User
from app.db.session import SessionLocal


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"invalid token: {e}")


def _seed_starter_task(db: Session, user: User) -> None:
    """Create a single PLANNED "plan your week" task for a fresh user.

    Called once, atomically with user provisioning (or on next sign-in
    for pre-Apr-21 users with zero tasks and a null onboarding flag).
    Direct ORM insert, bypassing TaskManager — new user has no existing
    tasks, so there are no conflicts, no Notion sync (notion_enabled is
    False for non-operator accounts), and no substitution linkage to
    compute. Keeps the seed cheap and isolated from the full-create
    machinery.

    Scheduling: tomorrow 9 am local (Africa/Cairo single-timezone
    alpha). User can reschedule, start immediately, or delete — the
    seed is a prompt, not a commitment. Also stamps
    onboarding_completed_at so the 2026-05-21 kill-criterion query has
    a reliable "user has received their starter" timestamp.
    """
    now = datetime.utcnow()
    # Tomorrow 9 am in local tz. Pre-multi-timezone refactor: we store
    # naked Cairo-local datetimes in "_utc" columns (project convention,
    # see MANIFESTO.md timezone contract). That's why this uses
    # datetime.utcnow() then shifts — the backend treats these wall-clock.
    start = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    end = start + timedelta(minutes=30)
    task = Task(
        title="Plan your week — brain dump and triage",
        category="planning",
        planned_start_utc=start,
        planned_end_utc=end,
        planned_duration_minutes=30,
        state=TaskState.PLANNED,
        source=TaskSource.WEB,
        description="Lyra started this for you. Edit the time, fire the timer to plan, or delete and build your own setup.",
        created_at=now,
        last_modified_at=now,
        session_index_in_day=0,
        user_id=user.user_id,
    )
    db.add(task)
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = now
    db.commit()


def resolve_user_from_token(token: str) -> User:
    """Decode the JWT and return the matching User, creating it on first login."""
    payload = decode_token(token)
    email = payload.get("email")
    google_id = payload.get("sub") or payload.get("google_id")
    if not email:
        raise HTTPException(status_code=401, detail="token missing email claim")

    db = SessionLocal()
    try:
        user: Optional[User] = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                email=email,
                google_id=google_id,
                timezone="Africa/Cairo",
                is_operator=False,
                notion_enabled=False,
                created_at=datetime.utcnow(),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            # Fresh signup — seed the starter task so /today isn't empty.
            _seed_starter_task(db, user)
            db.refresh(user)
        else:
            if google_id and user.google_id is None:
                # Backfill google_id on the operator's existing row at first login
                user.google_id = google_id
                db.commit()
                db.refresh(user)
            # Pre-Apr-21 signups who never got past the (now-removed)
            # onboarding surface — if they have zero tasks and a null
            # flag, seed them on this sign-in. Users with any prior task
            # have the flag stamped (via the 2026-04-21 backfill) and
            # skip this branch.
            if user.onboarding_completed_at is None:
                task_count = db.query(Task).filter(Task.user_id == user.user_id).count()
                if task_count == 0:
                    _seed_starter_task(db, user)
                    db.refresh(user)
        return user
    finally:
        db.close()
