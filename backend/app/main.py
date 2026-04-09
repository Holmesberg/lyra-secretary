import logging

logging.basicConfig(level=logging.INFO)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.v1.router import api_router
from app.workers.scheduler import start_scheduler, shutdown_scheduler
from app.db.base import Base
from app.db import models  # noqa: F401 — register mappers before scoping install
from app.db.scoping import install_scoping

install_scoping(Base)

from starlette.middleware.base import BaseHTTPMiddleware
from app.db.scoping import set_current_user_id


class UserScopeMiddleware(BaseHTTPMiddleware):
    """Resolve identity per request and set the scoping ContextVar.

    Resolution order:
      1. Authorization: Bearer <jwt>  — frontend (next-auth, Phase 2+)
      2. X-User-Id: <int>             — operator's OpenClaw + backend tests
      3. Default: user_id=1 (operator) — preserves single-user clients

    The bearer path also auto-provisions a User row on first login.
    """

    async def dispatch(self, request, call_next):
        from app.core.security import resolve_user_from_token

        from fastapi.responses import JSONResponse
        from fastapi import HTTPException

        user_id = 1
        resolved = False
        auth = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(None, 1)[1].strip()
            try:
                user = resolve_user_from_token(token)
                user_id = user.user_id
                resolved = True
            except HTTPException as e:
                # Malformed / expired / unknown-user Bearer must NOT
                # silently fall through to user_id=1. That's a footgun
                # even with the scoping hook in place — explicit 401.
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail},
                )
            except Exception as e:
                return JSONResponse(
                    status_code=401,
                    content={"detail": f"bearer auth failed: {e}"},
                )

        if not resolved:
            raw = request.headers.get("X-User-Id")
            if raw is not None:
                try:
                    user_id = int(raw)
                except ValueError:
                    user_id = 1

        set_current_user_id(user_id)
        try:
            return await call_next(request)
        finally:
            set_current_user_id(None)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()

app = FastAPI(
    title="Lyra Secretary API",
    version="1.1",
    description="Adaptive scheduler and personal cognitive operating system",
    lifespan=lifespan
)

app.add_middleware(UserScopeMiddleware)
app.include_router(api_router, prefix="/v1")

@app.get("/")
def root():
    return {"message": "Lyra Secretary API is running"}
