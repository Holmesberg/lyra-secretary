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
| `services/parser.py` | NLP (dateparser) → structured task fields. `parse_chained(text)` handles "then"-separated compound requests. |
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

## SKILL.md Editing Rules

- Keep `openclaw/skills/lyra-secretary/SKILL.md` **under 150 lines total**.
- Verification preamble must stay first (before Hard Rules).
- Hard Rules must stay at the top, numbered, unchanged structure.
- Every endpoint: method, path, required fields (*), key response fields only — one line.
- Never add prose explanations, curl examples, or markdown tables — bullet points only.
- After any edit, run `wc -l` and reject if over 150.
- Always copy the updated file to `/mnt/c/Users/alina/openclaw/skills/lyra-secretary/SKILL.md` and restart the gateway.

## Pending endpoints

- `POST /v1/stopwatch/retroactive` — log completed sessions after the fact with full timestamp control.
  Body: `title`, `start_time`, `end_time`, `pre_task_readiness` (optional), `post_task_reflection` (optional).
  Creates task in EXECUTED state with correct delta, skips live timer.
  Use case: end-of-day retroactive logging for untracked sessions.

## Endpoint deprecations

- `POST /v1/parse` — scheduled for deprecation. LLMs should call `/v1/create` directly with structured fields extracted from user input. Use `/v1/parse` only as a last resort for genuinely ambiguous time expressions (e.g. "later", "this evening"). The endpoint now returns `{ tasks: [...], compound: bool }` and supports "then"-chained compound requests via `TaskParser.parse_chained()`.

## Known issues

See `LYRA_BUGS.md` for active bugs. See `lyra_final_spec.md` for the full product spec.
