"""User account endpoints (Phase 2): /me, consent, export, hard delete."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import ArchetypeAssignment, StopwatchSession, Task, User
from app.db.scoping import get_current_user_id, set_current_user_id

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
        "created_at": user.created_at.isoformat(),
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


class DeleteIn(BaseModel):
    confirm_email: str


@router.delete("/users/me")
def delete_my_account(body: DeleteIn, db: Session = Depends(get_db)):
    """Hard delete the requesting user and all owned rows. Cascade by hand
    because SQLite FKs aren't enforced uniformly across the legacy tables."""
    user = _current_user(db)
    if user.is_operator:
        raise HTTPException(status_code=403, detail="operator account cannot self-delete")
    if body.confirm_email != user.email:
        raise HTTPException(status_code=400, detail="confirm_email does not match")

    uid = user.user_id
    # Drop scope so the cascade DELETEs can run unfiltered (we are
    # explicitly targeting this user_id and only this user_id).
    set_current_user_id(None)
    try:
        db.execute(text("DELETE FROM stopwatch_session WHERE user_id = :u"), {"u": uid})
        db.execute(text("DELETE FROM task WHERE user_id = :u"), {"u": uid})
        db.execute(text("DELETE FROM archetype_assignment WHERE user_id = :u"), {"u": uid})
        db.execute(text("DELETE FROM user WHERE user_id = :u"), {"u": uid})
        db.commit()
    finally:
        set_current_user_id(uid)
    return {"ok": True, "deleted_user_id": uid}
