import logging

logging.basicConfig(level=logging.INFO)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.v1.router import api_router
from app.workers.scheduler import start_scheduler, shutdown_scheduler

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

app.include_router(api_router, prefix="/v1")

@app.get("/")
def root():
    return {"message": "Lyra Secretary API is running"}
