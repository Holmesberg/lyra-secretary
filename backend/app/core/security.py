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
from sqlalchemy.exc import IntegrityError
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

    Scheduling policy (2026-04-22, revised): the task MUST land on
    today so it shows up on /today's feed the moment the user lands,
    not tomorrow where it's hidden. Three tiers by sign-up time:

      - sign-up before 9 am local → today 9 am (morning anchor)
      - sign-up between 9 am and 23:29 → next :30 or :00 mark from now
        (always strictly future; always stays on today)
      - sign-up at or after 23:29 → tomorrow 9 am (less than 30 min
        remaining today — not enough for a meaningful slot)

    Window end clamps to 23:59 today so we never cross midnight — a
    starter spanning today→tomorrow appears on tomorrow's /today
    feed, which defeats the fix. Planned duration follows the actual
    window length so duration_delta measurement stays consistent
    (a 23:00 sign-up gets a 29-min planned slot, not 30).

    Previous shape (2026-04-21 → 2026-04-22): tomorrow 9 am fixed.
    Operator dogfood observation 2026-04-22: mom (u4) and others
    likely saw an empty /today on signup day and didn't come back.

    Also stamps onboarding_completed_at so the 2026-05-21
    kill-criterion query has a reliable "user has received their
    starter" timestamp.
    """
    now = datetime.utcnow()
    # Pre-multi-timezone refactor: we store naked Cairo-local datetimes
    # in "_utc" columns (project convention, see MANIFESTO.md timezone
    # contract). That's why this uses datetime.utcnow() then treats it
    # as wall-clock — the backend renders these without offset shift.
    today_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=0, microsecond=0)
    # Last point where the next :30 or :00 mark still lands on today.
    # At 23:29 the next half-hour is 23:30 (still today); at 23:30 it
    # would be 00:00 tomorrow. Anything ≥ 23:29 falls to tomorrow 9 am.
    late_cutoff = now.replace(hour=23, minute=29, second=0, microsecond=0)

    if now < today_9am:
        start = today_9am
    elif now < late_cutoff:
        # Round up to the next :30 or :00 mark. Always strictly future
        # so the starter never opens with the "start is in the past"
        # inline hint we added for the new-task modal 2026-04-22.
        bump = 1 if (now.second or now.microsecond) else 0
        next_minute = now.minute + bump
        if next_minute <= 30:
            start = now.replace(minute=30, second=0, microsecond=0)
            # If next_minute == 30 exactly (0 seconds), start == now —
            # advance to the following half-hour so it's strictly ahead.
            if start <= now:
                start = start + timedelta(minutes=30)
        else:
            start = (now + timedelta(hours=1)).replace(
                minute=0, second=0, microsecond=0
            )
    else:
        # Less than ~30 min left in the day — no meaningful today-slot
        # possible. Land on tomorrow 9 am instead.
        start = today_9am + timedelta(days=1)

    desired_end = start + timedelta(minutes=30)
    if start.date() != now.date():
        # Tomorrow-9am branch — clean 30-min slot on the next day.
        end = desired_end
    elif desired_end > end_of_day:
        # Clamp to 23:59 if the window would cross midnight. Happens
        # only at the edge (e.g. start 23:30 → end 24:00 → clamp 23:59).
        end = end_of_day
    else:
        end = desired_end

    duration = max(1, int((end - start).total_seconds() / 60))
    task = Task(
        title="Plan your week — brain dump and triage",
        category="planning",
        planned_start_utc=start,
        planned_end_utc=end,
        planned_duration_minutes=duration,
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
    """Decode the JWT and return the matching User, creating it on first login.

    Apr 26 fixes:
      1. **Race-safe provisioning.** When a new user signs in, the frontend
         fan-out fires 5+ concurrent requests; without protection they ALL
         see user=None and all try to INSERT, hitting the email unique
         constraint. Wrap the insert in try/except IntegrityError + re-query;
         whichever request wins, the others adopt the existing row.
      2. **Killed `_seed_starter_task` callsites.** Per Apr 25 strategic
         decision (`docs/strategic_decisions_april_24.md` + `memory/
         project_relief_instrument_reframe.md`): the seeded "Plan your week
         — brain dump and triage" task poisoned every signup's activation
         funnel (u12, u14 each got it, both abandoned it). The right fix is
         to ship Family F1 chaos capture instead of a placeholder task.
         Removing the calls also cuts ~1 commit + 1 round-trip from signup.
    """
    payload = decode_token(token)
    email = payload.get("email")
    google_id = payload.get("sub") or payload.get("google_id")
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
                    timezone="Africa/Cairo",
                    is_operator=False,
                    notion_enabled=False,
                    created_at=datetime.utcnow(),
                )
                db.add(user)
                db.commit()
                db.refresh(user)
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
            if google_id and user.google_id is None:
                # Backfill google_id on the operator's existing row at first login
                user.google_id = google_id
                db.commit()
                db.refresh(user)
        return user
    finally:
        db.close()
