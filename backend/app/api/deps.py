"""FastAPI dependencies."""
from fastapi import Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.scoping import set_current_user_id
from app.db.session import SessionLocal
from app.db.models import User


def get_db(request: Request):
    """Yield a session AND set the per-request user scope.

    Phase 1: trust X-User-Id header. Defaults to operator (user_id=1)
    when missing so existing operator clients (OpenClaw) keep working
    without modification. Phase 2 replaces this with JWT validation.
    """
    user_id = 1
    raw = request.headers.get("X-User-Id")
    if raw is not None:
        try:
            user_id = int(raw)
        except ValueError:
            user_id = 1
    # Scope is also set in UserScopeMiddleware (which runs in the
    # event loop context); the duplicate set here is a safety net for
    # callers that import get_db without going through middleware
    # (e.g. background scripts).
    set_current_user_id(user_id)
    db = SessionLocal()
    try:
        yield db
    finally:
        set_current_user_id(None)
        db.close()


def get_current_user(
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> User:
    """Resolve the request to a user.

    Phase 1: trust X-User-Id header (operator + tests only).
    Phase 2: replaced by JWT validation from next-auth.

    Sets the user_id into the scoping ContextVar so the before_compile
    hook auto-filters every subsequent query in this request.
    """
    if x_user_id is None:
        # Default to operator (user_id=1) for unauthenticated requests
        # during the Phase 1 transition. Removed in Phase 2.
        user_id = 1
    else:
        try:
            user_id = int(x_user_id)
        except ValueError:
            raise HTTPException(status_code=401, detail="invalid X-User-Id header")

    # Set scoping BEFORE loading the user — but the user query itself
    # must run unscoped (User has no user_id column, so it's exempt).
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user is None:
            raise HTTPException(status_code=401, detail="unknown user")
    finally:
        db.close()

    set_current_user_id(user_id)
    return user
