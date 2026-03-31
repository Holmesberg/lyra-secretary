# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Docker (primary dev workflow)
```bash
docker-compose up -d --build
docker-compose exec backend alembic upgrade head
docker-compose exec backend python app/db/seed.py
curl http://localhost:8000/v1/health
```

### Local development
```bash
cd backend/
pip install -r requirements.txt pytest
export PYTHONPATH=.
pytest tests/
pytest tests/test_timezone_contract.py   # run a single test file
```

### Diagram regeneration
```bash
pip install matplotlib
python docs/diagrams/generate_diagrams.py
```

## Architecture

Lyra Secretary is a single-user adaptive task scheduler. It records **planned vs. executed duration** per task to learn behavioral patterns. The `duration_delta_minutes` field (planned − executed) is the core metric.

### Layers

```
Client (Telegram / OpenClaw agent)
  ↓ HTTP
API (FastAPI) — backend/app/api/v1/endpoints/
  ↓ DI via get_db() / get_redis()
Services — backend/app/services/
  ↓
SQLite (SQLAlchemy + Alembic) + Redis + Notion API
```

Background jobs (APScheduler) run inside the FastAPI process: reminders every 1 min, Notion sync retries every 5 min, timer overflow alerts every 2 min.

### Single Mutation Authority

**All task writes go through `TaskManager` (`services/task_manager.py`).** Endpoints never modify tasks directly. This enforces the state machine, conflict detection, Notion sync, and the undo cache in one place.

### Task State Machine

```
PLANNED → EXECUTING → EXECUTED (immutable)
        ↘ SKIPPED  (immutable)
PLANNED → DELETED   (soft delete, immutable)
```

Transitions are enforced by `services/state_machine.py`. Completed/skipped/deleted tasks cannot be mutated.

### Redis responsibilities
- Active stopwatch session (survives restart — rehydrated from SQLite)
- Undo cache (30-second TTL per action)
- Idempotency keys (30-second TTL, via `X-Idempotency-Key` header)
- Notion failed-sync queue (retried by APScheduler)

### Key service files
| File | Responsibility |
|------|---------------|
| `services/task_manager.py` | All task CRUD, the one place that calls everything else |
| `services/state_machine.py` | Validates and applies state transitions |
| `services/conflict_detector.py` | Half-open interval `[start, end)` overlap detection |
| `services/stopwatch_manager.py` | Timer lifecycle; early-stop gate at <50% planned duration |
| `services/parser.py` | NLP (dateparser) → structured task fields |
| `services/notion_client.py` | Notion API sync; failures enqueued in Redis |
| `workers/scheduler.py` | APScheduler setup wired into FastAPI lifespan |

### Database schema (3 tables)
- **task** — core entity with planned/executed time pairs, state, Notion page ID
- **stopwatch_session** — one-to-many with task; tracks individual timer runs
- **category_mapping** — static keyword→category lookup seeded at init (not learned)

### OpenClaw integration
OpenClaw runs in a separate Docker Compose stack. Connect the two via Docker network bridge (see `DOCKER.md`). The agent skill definition lives at `openclaw/skills/lyra-secretary/SKILL.md` and must be copied to `~/.openclaw/skills/lyra-secretary/`. The backend pushes notifications to `http://openclaw-gateway:18789/api/notify`; the agent polls `GET /v1/notifications/pending` every 30 s.

## Configuration

Copy `.env.example` to `.env`. Required vars: `DATABASE_URL`, `REDIS_URL`, `NOTION_API_KEY`, `NOTION_DATABASE_ID`, `USER_TIMEZONE` (IANA, e.g. `Africa/Cairo`). `SECRET_KEY` must be ≥ 32 chars. All times are stored as UTC internally; `USER_TIMEZONE` controls display conversion via `utils/time_utils.py`.

## Known issues

See `LYRA_BUGS.md` for active bugs. See `lyra_final_spec.md` for the full product spec.
