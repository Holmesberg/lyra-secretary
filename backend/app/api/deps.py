"""FastAPI dependencies."""
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.scoping import get_current_user_id, set_current_user_id
from app.db.session import SessionLocal
from app.db.models import User


def _test_identity_header_enabled(request: Request) -> bool:
    """Return true only when the test harness explicitly installed header auth."""
    return bool(getattr(request.app.state, "allow_test_identity_header", False))


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
        if not _test_identity_header_enabled(request):
            raise HTTPException(status_code=401, detail="X-User-Id is test-only")
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


def require_current_user_scope() -> int:
    """Return the resolved request user id or fail closed.

    Bearer/JWT resolution happens in ``UserScopeMiddleware``. Test-only
    ``X-User-Id`` may also have populated the ContextVar, but only when the
    harness explicitly enabled it. This helper never invents an identity.
    """
    uid = get_current_user_id()
    if uid is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return uid


def authenticated_user_from_scope(db: Session) -> User:
    """Resolve the current scoped user from the database."""
    uid = require_current_user_scope()
    user = db.query(User).filter(User.user_id == uid).first()
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    return user


def operator_user_from_scope(db: Session, request: Request | None = None) -> User:
    """Resolve the current user and require the trusted-alpha operator role."""
    try:
        user = authenticated_user_from_scope(db)
    except HTTPException as exc:
        if request is not None and exc.status_code == 401:
            from app.services.security_audit import write_security_audit_event

            write_security_audit_event(
                db=db,
                event_type="auth_required_denied",
                surface=request.url.path,
                status="denied",
                request=request,
                redacted_metadata={"reason": exc.detail},
            )
        raise

    if not user.is_operator:
        if request is not None:
            from app.services.security_audit import write_security_audit_event

            write_security_audit_event(
                db=db,
                actor_user_id=user.user_id,
                user_id=user.user_id,
                event_type="operator_access_denied",
                surface=request.url.path,
                status="denied",
                request=request,
                redacted_metadata={"role": "user"},
            )
        raise HTTPException(status_code=403, detail="operator only")
    return user


def require_authenticated_user(db: Session = Depends(get_db)) -> User:
    """FastAPI dependency for endpoints that need a concrete user row."""
    return authenticated_user_from_scope(db)


def require_operator_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency for operator and diagnostic endpoints."""
    return operator_user_from_scope(db, request=request)


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
        if not _test_identity_header_enabled(request):
            raise HTTPException(status_code=401, detail="X-User-Id is test-only")
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
