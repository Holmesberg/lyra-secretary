"""User account endpoints (Phase 2): /me, consent, export, data-summary, hard delete."""
import hashlib
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Archetype, ArchetypeAssignment, StopwatchSession, Task, TaskState, User
from app.db.scoping import get_current_user_id, set_current_user_id
from app.schemas.archetype import ArchetypeAssignmentOut, ArchetypeSurveyIn
from app.services.archetype_service import (
    DIFFUSE_AVERAGE_ID,
    assign_archetype,
    classify_discipline,
    compute_discipline_z,
    score_bfi_c,
    score_bscs,
    score_gp,
    score_meq,
)
from app.services.calendar_sync import store_refresh_token
from app.utils.time_utils import now_utc, strip_tz

# Phase D archetype-survey eligibility gate. Users created on or after
# this timestamp see the survey during onboarding (after consent, before
# starter task). Users created before it bypass the gate and see the
# Settings retrofit banner instead. Frozen at Wave 2 ship; changing it
# retroactively reclassifies users, which is a mild UX surprise
# (banner disappears, survey appears) — not a research-integrity
# violation since the archetype-prior blend behaves identically either
# path.
ARCHETYPE_SURVEY_LAUNCH_UTC = datetime(2026, 4, 22, 0, 0, 0)

# Built-in category taxonomy mirrors frontend/lib/categories.ts.
# Source-of-truth note — the frontend file is the canonical copy for
# the UI taxonomy; this list exists to back the /users/me/categories
# endpoint (so the dropdown can render built-in + user-custom together).
# If you edit one, edit both — there is no runtime constraint making
# them match.
BUILT_IN_CATEGORIES = [
    "fitness",
    "academic",
    "study",
    "development",
    "meeting",
    "prayer",
    "planning",
    "network",
    "health",
    "work",
    "personal",
]

router = APIRouter()


def _current_user(db: Session) -> User:
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    # User table is exempt from scoping; this is a direct lookup.
    user = db.query(User).filter(User.user_id == uid).first()
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    return user


class ConsentIn(BaseModel):
    terms_accepted: bool
    research_consent: bool


@router.get("/users/me")
def get_me(db: Session = Depends(get_db)):
    user = _current_user(db)
    # Grandfathered-user backfill (2026-04-28 hotfix): re-enabling the
    # OnboardingFlow gate in C1 blocked /today for users created before
    # alembic 025 added onboarding_completed_at — that column was stamped
    # only on FIRST task creation going forward, so pre-existing accounts
    # with tasks have NULL there and now hit the onboarding screen
    # instead of their actual data ("WHERE DID THE OLD TASKS GO" report).
    # Lazy-fix: if the user has any non-voided task, treat them as
    # already onboarded — stamp onboarding_completed_at to the earliest
    # task's created_at so retention analyses still see the right
    # window. Best-effort; errors are non-blocking.
    try:
        if user.onboarding_completed_at is None:
            earliest_task = (
                db.query(func.min(Task.created_at))
                .filter(
                    Task.user_id == user.user_id,
                    Task.voided_at.is_(None),
                )
                .scalar()
            )
            if earliest_task is not None:
                # Strip tz: Supabase TIMESTAMPTZ default returns aware
                # even when SQLAlchemy says DateTime — see time_utils
                # strip_tz docstring.
                earliest_task = strip_tz(earliest_task)
                user.onboarding_completed_at = earliest_task
                # Also stamp first_task_at if alembic 037 has been
                # applied — same earliest timestamp.
                if hasattr(user, "first_task_at") and user.first_task_at is None:
                    user.first_task_at = earliest_task
                db.commit()
    except Exception as e:
        # Non-blocking but logged — silent except hid LYR-113 family
        # debugging context. See root_cause_analysis_2026_04_29.md
        # observability-shortfall pattern.
        logger.warning("/me onboarding backfill failed (non-blocking): %s", e)
        db.rollback()
    # Alpha funnel (alembic 037, 2026-04-28): d1_return_at lazy-stamp.
    # Approximates "returned next day" — first /users/me call ≥24h after
    # user.created_at when the column is still NULL. Frontend hits this
    # endpoint on every page load via the layout, so this fires reliably
    # without a dedicated event-tracking surface. Best-effort: errors
    # are non-blocking (the funnel stamp must never break sign-in).
    try:
        if (
            user.d1_return_at is None
            and (now_utc() - strip_tz(user.created_at)).total_seconds() >= 86400
        ):
            user.d1_return_at = now_utc()
            db.commit()
    except Exception as e:
        # Non-blocking but logged — see root_cause_analysis_2026_04_29.md.
        logger.warning("/me d1 stamp failed (non-blocking): %s", e)
        db.rollback()
    # Archetype-survey eligibility (Phase D, 2026-04-22 clustering ship).
    # True → post-launch user who should see the survey between consent
    # and starter-task reveal. False → pre-launch user who bypasses the
    # gate and sees the Settings retrofit banner. Existing completed or
    # skipped assignments suppress both (survey never re-fires; banner
    # hidden). See backend/app/api/v1/endpoints/users.py constant.
    latest_assignment = (
        db.query(ArchetypeAssignment)
        .filter(ArchetypeAssignment.user_id == user.user_id)
        .order_by(ArchetypeAssignment.assigned_at.desc())
        .first()
    )
    has_assignment = latest_assignment is not None
    archetype_survey_eligible = (
        user.created_at >= ARCHETYPE_SURVEY_LAUNCH_UTC
        and not has_assignment
    )
    # MANIFESTO §VT-25 / building_phases.md:167 — archetype label is
    # surfaced only after ~5 EXECUTED sessions so the survey-based label
    # is validated against actual behavior before it's named to the user.
    # Below threshold the Settings card hides the label and shows
    # "Getting to know you" copy; predictions still personalize silently.
    executed_session_count = (
        db.query(func.count(Task.task_id))
        .filter(
            Task.user_id == user.user_id,
            Task.state == TaskState.EXECUTED,
            Task.voided_at.is_(None),
        )
        .scalar()
        or 0
    )
    # Engagement signal — drives the layout's onboarding gate. A user
    # who completed onboarding but has zero non-skipped, non-voided
    # tasks is treated as never-onboarded so we re-show the brain-dump
    # surface (operator-locked 2026-04-29 after the omar/pbassem read:
    # legacy SKIPPED meta-tasks alone don't count as engagement).
    active_task_count = (
        db.query(func.count(Task.task_id))
        .filter(
            Task.user_id == user.user_id,
            Task.voided_at.is_(None),
            Task.state.notin_([TaskState.SKIPPED, TaskState.DELETED]),
        )
        .scalar()
        or 0
    )
    has_active_task_history = active_task_count > 0
    return {
        "user_id": user.user_id,
        "email": user.email,
        "google_id": user.google_id,
        "timezone": user.timezone,
        "is_operator": user.is_operator,
        "notion_enabled": user.notion_enabled,
        "archetype_id": user.archetype_id,
        "archetype_survey_eligible": archetype_survey_eligible,
        "archetype_assignment_completed": bool(
            latest_assignment and latest_assignment.completed
        ),
        "archetype_latest_assignment_at": (
            latest_assignment.assigned_at.isoformat()
            if latest_assignment
            else None
        ),
        # Total EXECUTED, non-voided sessions ever. Drives the
        # archetype-label session gate (≥5 → label revealed with
        # "may shift" caveat; <5 → calibrating state).
        "executed_session_count": int(executed_session_count),
        "archetype_retrofit_dismissed_at": (
            user.archetype_retrofit_dismissed_at.isoformat()
            if getattr(user, "archetype_retrofit_dismissed_at", None)
            else None
        ),
        "terms_accepted_at": user.terms_accepted_at.isoformat() if user.terms_accepted_at else None,
        "research_consent_at": user.research_consent_at.isoformat() if user.research_consent_at else None,
        "onboarding_completed_at": user.onboarding_completed_at.isoformat() if user.onboarding_completed_at else None,
        # Drives the onboarding gate — when False AND onboarding is
        # stamped, layout still re-shows the brain-dump (the user
        # bounced before any real engagement). Excludes voided + SKIPPED
        # rows so legacy "Plan your week" meta-tasks don't count.
        "has_active_task_history": has_active_task_history,
        # Guided tour stamps — surface so the frontend can gate the
        # TutorialOverlay render on (both null AND onboarding_completed_at
        # NOT NULL).
        "tutorial_completed_at": user.tutorial_completed_at.isoformat() if user.tutorial_completed_at else None,
        "tutorial_skipped_at": user.tutorial_skipped_at.isoformat() if user.tutorial_skipped_at else None,
        # Surface only whether calendar is connected, never the token
        # itself. Frontend uses this to decide whether to show the
        # "Connect Google Calendar" CTA vs the calendar-events UI.
        "google_calendar_connected": user.google_refresh_token is not None,
        "created_at": user.created_at.isoformat(),
    }


class StoreRefreshTokenIn(BaseModel):
    refresh_token: str


@router.post("/users/me/google-refresh-token")
def post_google_refresh_token(body: StoreRefreshTokenIn, db: Session = Depends(get_db)):
    """Persist a Google OAuth refresh token for the current user.

    Called by the Next.js server-side API route
    `/api/calendar/setup` after NextAuth captures the refresh_token on
    first sign-in with the calendar.readonly scope. The frontend
    never holds the token long enough to leak it outside the
    server-side session; the hop from Next.js API route to this
    endpoint is authenticated with the same backend JWT.

    Request body is deliberately minimal — no scope / expiry /
    id_token passthrough. Only the refresh token is persistent server
    state; everything else is derived or refetched.
    """
    user = _current_user(db)
    if not body.refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token required")
    store_refresh_token(user.user_id, body.refresh_token)
    return {"ok": True, "google_calendar_connected": True}


@router.delete("/users/me/google-refresh-token")
def delete_google_refresh_token(db: Session = Depends(get_db)):
    """Forget the user's refresh token — disconnects Google Calendar.

    Does NOT revoke the token with Google; user must also visit
    myaccount.google.com/permissions to fully revoke. This endpoint
    just clears Lyra's copy so the sync stops.
    """
    user = _current_user(db)
    user.google_refresh_token = None
    db.commit()
    return {"ok": True, "google_calendar_connected": False}


@router.post("/users/me/archetype/survey", response_model=ArchetypeAssignmentOut)
def submit_archetype_survey(
    body: ArchetypeSurveyIn, db: Session = Depends(get_db)
) -> ArchetypeAssignmentOut:
    """Score the 29-item battery and write an ArchetypeAssignment.

    Scores all four instruments, computes discipline_z via the Rule-13
    composite, classifies tertiles, assigns archetype per the pattern
    matcher (specific-first per methodology.md:85-90). Writes a new
    ArchetypeAssignment row with completed=True and preserves the raw
    29-item responses in `raw_responses` for future re-scoring under
    Gate 3/4 weight tuning.

    Idempotent by user: if the user already has an assignment, a new
    row is added and User.archetype_id updates to the latest. The
    historical row stays (enables longitudinal study of how archetype
    assignment drifts across retakes).
    """
    user = _current_user(db)

    meq_score, chronotype = score_meq(body.meq)
    bfi_c_score, _ = score_bfi_c(body.bfi_c)
    bscs_score, _ = score_bscs(body.bscs)
    gp_score, _ = score_gp(body.gp)
    discipline_z = compute_discipline_z(bfi_c_score, bscs_score, gp_score)
    discipline = classify_discipline(discipline_z)
    archetype_id = assign_archetype(chronotype, discipline)

    assignment = ArchetypeAssignment(
        user_id=user.user_id,
        archetype_id=archetype_id,
        meq_score=meq_score,
        bfi_c_score=bfi_c_score,
        bscs_score=bscs_score,
        gp_score=gp_score,
        chronotype=chronotype,
        discipline_z=round(discipline_z, 3),
        assigned_at=datetime.utcnow(),
        completed=True,
        skipped_at=None,
        raw_responses={
            "meq": body.meq,
            "bfi_c": body.bfi_c,
            "bscs": body.bscs,
            "gp": body.gp,
        },
    )
    db.add(assignment)
    user.archetype_id = archetype_id
    db.commit()

    return ArchetypeAssignmentOut(
        archetype_id=archetype_id,
        completed=True,
        chronotype=chronotype,
        discipline_z=round(discipline_z, 3),
        meq_score=meq_score,
        bfi_c_score=bfi_c_score,
        bscs_score=bscs_score,
        gp_score=gp_score,
    )


@router.post("/users/me/archetype/skip", response_model=ArchetypeAssignmentOut)
def skip_archetype_survey(db: Session = Depends(get_db)) -> ArchetypeAssignmentOut:
    """Record a skip: defaults the user to Diffuse Average.

    Writes ArchetypeAssignment(archetype_id='diffuse_average',
    completed=False, skipped_at=now()) and sets User.archetype_id.
    The completed=False flag is what retention analyses use to
    separate genuine Diffuse Average assignments (user answered and
    classified to diffuse_average) from skip-defaulted rows.
    Idempotent: re-skip is a no-op.
    """
    user = _current_user(db)

    existing = (
        db.query(ArchetypeAssignment)
        .filter(ArchetypeAssignment.user_id == user.user_id)
        .first()
    )
    if existing is not None and existing.skipped_at is not None:
        return ArchetypeAssignmentOut(
            archetype_id=existing.archetype_id,
            completed=existing.completed,
            chronotype=existing.chronotype,
            discipline_z=existing.discipline_z,
        )

    assignment = ArchetypeAssignment(
        user_id=user.user_id,
        archetype_id=DIFFUSE_AVERAGE_ID,
        chronotype=None,
        discipline_z=None,
        meq_score=None,
        bfi_c_score=None,
        bscs_score=None,
        gp_score=None,
        assigned_at=datetime.utcnow(),
        completed=False,
        skipped_at=datetime.utcnow(),
        raw_responses=None,
    )
    db.add(assignment)
    user.archetype_id = DIFFUSE_AVERAGE_ID
    db.commit()

    return ArchetypeAssignmentOut(
        archetype_id=DIFFUSE_AVERAGE_ID,
        completed=False,
    )


@router.post("/users/me/archetype/retrofit-dismiss")
def dismiss_archetype_retrofit(db: Session = Depends(get_db)) -> dict:
    """Stamp user.archetype_retrofit_dismissed_at. Idempotent — first call wins.

    Called by the Settings retrofit banner when a pre-launch user
    clicks Dismiss. The banner then disappears from their Settings.
    User remains on Diffuse Average default (no ArchetypeAssignment
    row is written) — they can still take the survey later by
    clicking the banner's Take-survey button before dismissing, or
    via a future Settings "Retake survey" affordance.
    """
    user = _current_user(db)
    if user.archetype_retrofit_dismissed_at is None:
        user.archetype_retrofit_dismissed_at = datetime.utcnow()
        db.commit()
    return {
        "ok": True,
        "archetype_retrofit_dismissed_at": (
            user.archetype_retrofit_dismissed_at.isoformat()
            if user.archetype_retrofit_dismissed_at
            else None
        ),
    }


@router.post("/users/me/tutorial/complete")
def complete_tutorial(db: Session = Depends(get_db)):
    """Stamp tutorial_completed_at. Idempotent — first call wins."""
    user = _current_user(db)
    if user.tutorial_completed_at is None:
        user.tutorial_completed_at = datetime.utcnow()
        db.commit()
    return {
        "ok": True,
        "tutorial_completed_at": user.tutorial_completed_at.isoformat(),
    }


@router.post("/users/me/tutorial/skip")
def skip_tutorial(db: Session = Depends(get_db)):
    """Stamp tutorial_skipped_at. Idempotent — first call wins.

    Recorded separately from `completed` so the 2026-05-21 retention
    analysis can distinguish "user walked through the whole tour"
    from "user dismissed immediately" from "user never saw it" — three
    different signals about onboarding fit.
    """
    user = _current_user(db)
    if user.tutorial_skipped_at is None:
        user.tutorial_skipped_at = datetime.utcnow()
        db.commit()
    return {
        "ok": True,
        "tutorial_skipped_at": user.tutorial_skipped_at.isoformat(),
    }


@router.post("/users/me/skip-onboarding")
def skip_onboarding(db: Session = Depends(get_db)):
    """Stamp onboarding_completed_at. Idempotent — first call wins.

    Re-introduced 2026-04-28 alongside the OnboardingFlow revival
    (alembic 037 magic-for-alpha). The endpoint is the structural-invariant
    bypass for users who don't want to brain-dump on signup — it stamps
    the completion timestamp without creating a task. The 2026-05-21
    retention query reads onboarding_completed_at as a binary signal,
    not as "task created", so this skip is honest.
    """
    user = _current_user(db)
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = datetime.utcnow()
        db.commit()
    return {
        "ok": True,
        "onboarding_completed_at": user.onboarding_completed_at.isoformat(),
    }


@router.get("/users/me/categories")
def get_my_categories(db: Session = Depends(get_db)):
    """Return the category dropdown source: built-in + user-custom.

    Fix for the 2026-04-21 dogfood report "categories don't persist
    after creating a new category." The frontend hardcoded list
    never grew with user-typed custom categories, so every new-task
    modal open reset the picker. This endpoint merges built-in
    taxonomy with the distinct categories the user has actually
    logged on any non-voided task. Color is assigned client-side via
    a deterministic hash (see frontend/lib/categories.ts).
    """
    user = _current_user(db)
    # Auto-scoped query — returns only this user's distinct categories.
    rows = (
        db.query(Task.category)
        .filter(Task.category.isnot(None))
        .filter(Task.voided_at.is_(None))
        .distinct()
        .all()
    )
    user_cats = {r[0] for r in rows if r[0]}
    # Report built-in separately so the frontend can render them in
    # canonical order; custom sorted alphabetically.
    custom = sorted(user_cats - set(BUILT_IN_CATEGORIES))
    return {
        "built_in": BUILT_IN_CATEGORIES,
        "custom": custom,
    }


@router.post("/users/me/consent")
def post_consent(body: ConsentIn, db: Session = Depends(get_db)):
    if not body.terms_accepted:
        raise HTTPException(status_code=400, detail="terms must be accepted")
    user = _current_user(db)
    now = datetime.utcnow()
    user.terms_accepted_at = now
    if body.research_consent:
        user.research_consent_at = now
    db.commit()
    return {"ok": True, "terms_accepted_at": now.isoformat(), "research_consent": body.research_consent}


@router.get("/users/me/export")
def export_my_data(db: Session = Depends(get_db)):
    """Full JSON dump of the requesting user's data. GDPR-style export."""
    user = _current_user(db)
    tasks = db.query(Task).all()  # auto-scoped
    sessions = db.query(StopwatchSession).all()  # auto-scoped
    assignments = (
        db.query(ArchetypeAssignment)
        .filter(ArchetypeAssignment.user_id == user.user_id)
        .all()
    )
    return {
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "timezone": user.timezone,
            "archetype_id": user.archetype_id,
            "terms_accepted_at": user.terms_accepted_at.isoformat() if user.terms_accepted_at else None,
            "research_consent_at": user.research_consent_at.isoformat() if user.research_consent_at else None,
            "created_at": user.created_at.isoformat(),
        },
        "tasks": [
            {c.name: getattr(t, c.name) for c in Task.__table__.columns}
            for t in tasks
        ],
        "stopwatch_sessions": [
            {c.name: getattr(s, c.name) for c in StopwatchSession.__table__.columns}
            for s in sessions
        ],
        "archetype_assignments": [
            {c.name: getattr(a, c.name) for c in ArchetypeAssignment.__table__.columns}
            for a in assignments
        ],
    }


@router.get("/users/me/data-summary")
def data_summary(db: Session = Depends(get_db)):
    """Counts for the delete-account comprehension stage. Cheap single-query."""
    user = _current_user(db)

    # Task counts by state (auto-scoped by user)
    state_counts = (
        db.query(Task.state, func.count())
        .group_by(Task.state)
        .all()
    )
    by_state = {state: count for state, count in state_counts}
    total_tasks = sum(by_state.values())

    # Session count
    session_count = db.query(func.count(StopwatchSession.session_id)).scalar() or 0

    # Reflections: tasks with at least one of readiness or reflection set
    reflection_count = (
        db.query(func.count(Task.task_id))
        .filter(
            (Task.pre_task_readiness.isnot(None)) | (Task.post_task_reflection.isnot(None))
        )
        .scalar() or 0
    )

    return {
        "total_tasks": total_tasks,
        "executed_count": by_state.get(TaskState.EXECUTED, 0) + by_state.get("EXECUTED", 0),
        "skipped_count": by_state.get(TaskState.SKIPPED, 0) + by_state.get("SKIPPED", 0),
        "planned_count": by_state.get(TaskState.PLANNED, 0) + by_state.get("PLANNED", 0),
        "session_count": session_count,
        "reflection_count": reflection_count,
        "notion_enabled": user.notion_enabled,
    }


class DeleteIn(BaseModel):
    confirm_email: str
    retain_for_research: bool = True


# Stable salt for one-way user-id hashing. Not secret — just prevents trivial
# reversal of small integer user_ids via rainbow table.
_HASH_SALT = "lyra-anonymized-retention-2026"


@router.delete("/users/me")
def delete_my_account(body: DeleteIn, db: Session = Depends(get_db)):
    """Delete the requesting user's account.

    If retain_for_research=true (default): anonymize task and session rows,
    preserving behavioral measurements for product research. Identifying
    fields (title, notes, notion_page_id) are cleared. User row is deleted.

    If retain_for_research=false: hard delete cascade across all tables.
    """
    user = _current_user(db)
    if user.is_operator:
        raise HTTPException(status_code=403, detail="operator account cannot self-delete")
    if body.confirm_email != user.email:
        raise HTTPException(status_code=400, detail="confirm_email does not match")

    uid = user.user_id
    now = now_utc()

    # Drop scope so the cascade DELETEs/UPDATEs can run unfiltered.
    set_current_user_id(None)
    try:
        if body.retain_for_research:
            # One-way hash for grouping this user's retained rows in research queries
            uid_hash = hashlib.sha256(f"{uid}:{_HASH_SALT}".encode()).hexdigest()

            # Anonymize tasks: clear identifying fields, keep behavioral data
            db.execute(
                text("""
                    UPDATE task SET
                        title = '[anonymized]',
                        notes = NULL,
                        notion_page_id = NULL,
                        post_deletion_retained_at = :now,
                        original_user_id_hash = :hash
                    WHERE user_id = :u
                """),
                {"now": now, "hash": uid_hash, "u": uid},
            )

            # Anonymize sessions: keep timing/behavioral data
            db.execute(
                text("""
                    UPDATE stopwatch_session SET
                        post_deletion_retained_at = :now,
                        original_user_id_hash = :hash
                    WHERE user_id = :u
                """),
                {"now": now, "hash": uid_hash, "u": uid},
            )

            # Delete non-behavioral rows. external_event_outcome rows
            # get purged alongside the user — at current n the VT-23
            # aggregate signal from deleted users is negligible; LYR-103
            # tracks the retention-anonymize follow-up for when n grows.
            # The DB-level ON DELETE CASCADE added in alembic 028 is the
            # belt-and-suspenders backstop; this explicit DELETE matches
            # the pattern used for every other user-scoped table here.
            db.execute(text("DELETE FROM external_event_outcome WHERE user_id = :u"), {"u": uid})
            db.execute(text("DELETE FROM archetype_assignment WHERE user_id = :u"), {"u": uid})
            db.execute(text('DELETE FROM "user" WHERE user_id = :u'), {"u": uid})
            db.commit()
        else:
            # Hard delete — all data permanently removed.
            db.execute(text("DELETE FROM external_event_outcome WHERE user_id = :u"), {"u": uid})
            db.execute(text("DELETE FROM stopwatch_session WHERE user_id = :u"), {"u": uid})
            db.execute(text("DELETE FROM task WHERE user_id = :u"), {"u": uid})
            db.execute(text("DELETE FROM archetype_assignment WHERE user_id = :u"), {"u": uid})
            db.execute(text('DELETE FROM "user" WHERE user_id = :u'), {"u": uid})
            db.commit()
    finally:
        set_current_user_id(uid)

    return {
        "ok": True,
        "deleted_user_id": uid,
        "data_retained_for_research": body.retain_for_research,
    }
