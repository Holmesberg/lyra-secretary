import logging

logging.basicConfig(level=logging.INFO)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.workers.scheduler import start_scheduler, shutdown_scheduler
from app.core.config import settings
from app.db.base import Base
from app.db import models  # noqa: F401 — register mappers before scoping install
from app.db.scoping import install_scoping

install_scoping(Base)

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import run_in_threadpool
from app.db.scoping import set_current_user_id


class UserScopeMiddleware(BaseHTTPMiddleware):
    """Resolve identity per request and set the scoping ContextVar.

    Resolution order:
      1. Authorization: Bearer <jwt>  — frontend (next-auth, Phase 2+)
      2. X-User-Id: <int>             — operator's OpenClaw + backend tests

    The bearer path also auto-provisions a User row on first login.

    Apr 26 perf fix: resolve_user_from_token is synchronous (Postgres
    query + commit). Calling it directly from this `async def dispatch`
    method blocks the entire ASGI event loop — every concurrent request
    serializes through the same JWT decode + DB lookup. With the /today
    fan-out (5+ parallel requests on mount) and Cairo→Supabase RTT of
    100-200ms, the practical effect was that the operator's sister
    couldn't sign in: 5 concurrent requests × ~1s each, all queued.
    Wrapping in run_in_threadpool releases the event loop so concurrent
    requests can dispatch in parallel via the FastAPI default threadpool.
    """

    async def dispatch(self, request, call_next):
        from app.core.security import resolve_user_from_token

        from fastapi.responses import JSONResponse
        from fastapi import HTTPException

        # Preserve an explicitly pre-set scope for in-process callers
        # (tests and internal tools). Real anonymous HTTP requests enter
        # with no ContextVar scope, so they still fail closed in get_db.
        from app.db.scoping import get_current_user_id

        user_id = get_current_user_id()
        resolved = False
        auth = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(None, 1)[1].strip()
            try:
                # Offload the sync DB work so other concurrent requests can
                # progress. This single change is the dominant signup-latency
                # fix.
                user = await run_in_threadpool(resolve_user_from_token, token)
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
                if not bool(getattr(request.app.state, "allow_test_identity_header", False)):
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "X-User-Id is test-only"},
                    )
                try:
                    user_id = int(raw)
                except ValueError:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "invalid X-User-Id header"},
                    )

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


# Per-request backend timing log. Added 2026-04-17 during P0 pause-
# latency investigation (operator reported 13 s pause; uvicorn access
# log doesn't record timing). Cost is microseconds per request —
# cheap enough to leave in place as a standing latency probe.
@app.middleware("http")
async def log_request_timing(request, call_next):
    import time
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    logging.getLogger("lyra.perf").info(
        f"{request.method} {request.url.path} {elapsed_ms:.0f}ms status={response.status_code}"
    )
    return response

# Middleware ordering: Starlette applies middleware in REVERSE of
# add_middleware order — the last-added wrapper becomes the outermost.
#
# CORS must be the OUTER layer so that short-circuit 401 responses
# from UserScopeMiddleware (e.g. on expired JWTs) still carry
# Access-Control-Allow-Origin headers. Otherwise the browser sees a
# bare 401 from the cross-origin request and reports it as a CORS
# policy failure, masking the real auth error. CORS also handles the
# preflight OPTIONS path itself without ever calling the inner layer.
app.add_middleware(UserScopeMiddleware)  # inner — added first
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "X-User-Id"],
    expose_headers=["*"],
)  # outer — added last, runs first
app.include_router(api_router, prefix="/v1")

@app.get("/")
def root():
    return {"message": "Lyra Secretary API is running"}
