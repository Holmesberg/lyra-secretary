"""JWT decoding for the multi-user web frontend.

The Next.js frontend (next-auth) mints an HS256 JWT at login time using
the shared JWT_SECRET. This module decodes that token, validates it,
and resolves it to a `User` row — auto-provisioning the row on first
sight (signup-by-first-login, gated only by Google having vouched for
the email).
"""
from datetime import datetime
from typing import Optional

import jwt
from fastapi import HTTPException

from app.core.config import settings
from app.db.models import User
from app.db.session import SessionLocal


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"invalid token: {e}")


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
        elif google_id and user.google_id is None:
            # Backfill google_id on the operator's existing row at first login
            user.google_id = google_id
            db.commit()
            db.refresh(user)
        return user
    finally:
        db.close()
