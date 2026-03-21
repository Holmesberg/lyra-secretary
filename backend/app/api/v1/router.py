"""V1 API Router."""
from fastapi import APIRouter
from app.api.v1.endpoints import health, parse, tasks, stopwatch

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(parse.router, tags=["parse"])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(stopwatch.router, tags=["stopwatch"])
