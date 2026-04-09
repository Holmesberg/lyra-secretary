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
    async def dispatch(self, request, call_next):
        raw = request.headers.get("X-User-Id")
        try:
            user_id = int(raw) if raw is not None else 1
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
