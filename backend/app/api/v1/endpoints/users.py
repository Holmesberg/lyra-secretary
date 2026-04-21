"""User account endpoints (Phase 2): /me, consent, export, data-summary, hard delete."""
import hashlib
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import ArchetypeAssignment, StopwatchSession, Task, TaskState, User
from app.db.scoping import get_current_user_id, set_current_user_id
from app.utils.time_utils import now_utc

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
    return {
        "user_id": user.user_id,
        "email": user.email,
        "google_id": user.google_id,
        "timezone": user.timezone,
        "is_operator": user.is_operator,
        "notion_enabled": user.notion_enabled,
        "archetype_id": user.archetype_id,
        "terms_accepted_at": user.terms_accepted_at.isoformat() if user.terms_accepted_at else None,
        "research_consent_at": user.research_consent_at.isoformat() if user.research_consent_at else None,
        "onboarding_completed_at": user.onboarding_completed_at.isoformat() if user.onboarding_completed_at else None,
        "created_at": user.created_at.isoformat(),
    }


@router.post("/users/me/skip-onboarding")
def skip_onboarding(db: Session = Depends(get_db)):
    """Stamp onboarding_completed_at for a user who declined the ritual.

    Path B makes the onboarding planning task a structural measurement
    moment but not a hard gate (see docs/design_patterns/rules_vs_agency.md).
    The operator can always skip — we still record the exit so the
    retention analysis can tell "completed planning ritual" from
    "skipped and proceeded" from "bounced without signal."
    """
    user = _current_user(db)
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = datetime.utcnow()
        db.commit()
    return {
        "ok": True,
        "onboarding_completed_at": user.onboarding_completed_at.isoformat(),
        "skipped": True,
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

            # Delete non-behavioral rows
            db.execute(text("DELETE FROM archetype_assignment WHERE user_id = :u"), {"u": uid})
            db.execute(text("DELETE FROM user WHERE user_id = :u"), {"u": uid})
            db.commit()
        else:
            # Hard delete cascade — all data permanently removed
            db.execute(text("DELETE FROM stopwatch_session WHERE user_id = :u"), {"u": uid})
            db.execute(text("DELETE FROM task WHERE user_id = :u"), {"u": uid})
            db.execute(text("DELETE FROM archetype_assignment WHERE user_id = :u"), {"u": uid})
            db.execute(text("DELETE FROM user WHERE user_id = :u"), {"u": uid})
            db.commit()
    finally:
        set_current_user_id(uid)

    return {
        "ok": True,
        "deleted_user_id": uid,
        "data_retained_for_research": body.retain_for_research,
    }
