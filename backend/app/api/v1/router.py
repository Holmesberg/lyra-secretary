"""V1 API Router."""
from fastapi import APIRouter
from app.api.v1.endpoints import health, parse, tasks, stopwatch, query, undo, notifications, analytics, skill_check, users, pause_predictions, reflection_view, calendar, integrations, admin, deadlines, feedback, brain_dump, moodle, jarvis, exposures, academic

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(skill_check.router, tags=["skill"])
api_router.include_router(parse.router, tags=["parse"])
api_router.include_router(query.router, tags=["query"])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(stopwatch.router, prefix="/stopwatch", tags=["stopwatch"])
api_router.include_router(undo.router, tags=["undo"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(analytics.router, tags=["analytics"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(pause_predictions.router, tags=["pause_predictions"])
api_router.include_router(reflection_view.router, tags=["reflection_view"])
api_router.include_router(calendar.router, tags=["calendar"])
api_router.include_router(integrations.router, tags=["integrations"])
api_router.include_router(admin.router, tags=["admin"])
# Loop 11 — deadline mechanism CRUD (Phase F, 2026-04-26).
api_router.include_router(deadlines.router, tags=["deadlines"])
# Alpha feedback widget (alembic 040, 2026-04-28).
api_router.include_router(feedback.router, tags=["feedback"])
# Onboarding brain-dump multi-parse (2026-04-28 evening, post-tutorial-removal).
api_router.include_router(brain_dump.router, tags=["brain_dump"])
# Moodle LMS .ics subscription import (alembic 041, 2026-04-29 — the LMS wedge).
api_router.include_router(moodle.router, tags=["moodle"])
# JARVIS chat assistant (NVIDIA NIM-powered, 2026-04-30, operator-only).
# Endpoints return 403 to non-operators. See docs/jarvis_architecture.md
# (TODO add) for the privacy-boundary discussion + tool registry.
api_router.include_router(jarvis.router, tags=["jarvis"])
api_router.include_router(exposures.router, tags=["exposures"])
api_router.include_router(academic.router, tags=["academic"])
