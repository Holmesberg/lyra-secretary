"""FastAPI dependencies."""
from fastapi import Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.scoping import get_current_user_id, set_current_user_id
from app.db.session import SessionLocal
from app.db.models import User


def get_db(request: Request):
    """Yield a session AND set the per-request user scope.

    UserScopeMiddleware is authoritative for normal HTTP requests. If
    this dependency is reached without a resolved bearer or explicit
    X-User-Id scope, fail closed instead of silently reading/writing as
    the operator.
    """
    existing_scope = get_current_user_id()
    scope_set_here = False

    # UserScopeMiddleware is the request-scoped source of truth. Only
    # synthesize a scope here when the dependency is used outside the
    # normal HTTP middleware path.
    if existing_scope is None:
        raw = request.headers.get("X-User-Id")
        if raw is None:
            raise HTTPException(status_code=401, detail="not authenticated")
        try:
            user_id = int(raw)
        except ValueError:
            raise HTTPException(status_code=401, detail="invalid X-User-Id header")
        set_current_user_id(user_id)
        scope_set_here = True

    db = SessionLocal()
    try:
        yield db
    finally:
        if scope_set_here:
            set_current_user_id(None)
        db.close()


def get_current_user(
    request: Request,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> User:
    """Resolve the request to a user.

    Trust the scope already resolved by UserScopeMiddleware. X-User-Id
    remains available for operator tooling and tests, but missing
    identity is no longer allowed to fall back to user_id=1.

    Sets the user_id into the scoping ContextVar so the before_compile
    hook auto-filters every subsequent query in this request.
    """
    existing_scope = get_current_user_id()
    if existing_scope is not None:
        user_id = existing_scope
    elif x_user_id is not None:
        try:
            user_id = int(x_user_id)
        except ValueError:
            raise HTTPException(status_code=401, detail="invalid X-User-Id header")
    else:
        raise HTTPException(status_code=401, detail="not authenticated")

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
