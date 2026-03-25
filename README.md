# Lyra Secretary v1.1

> Adaptive scheduling backend for a personal cognitive operating system

## What Is This?

Lyra Secretary is a FastAPI backend that manages your daily schedule by tracking **planned vs. executed task duration** — the **delta** — to learn behavioral patterns over time. Every task records how long you *said* it would take and how long it *actually* took, building a quantitative profile of your time usage.

The long-term vision: integrate with **LYRA BCI** (EEG-based cognitive state detection) to close the loop — the scheduler adapts not just to what you *did*, but to how you *felt* while doing it.

## Architecture

```
Telegram → OpenClaw (AI agent) → FastAPI backend → SQLite + Redis → Notion
```

- **Telegram** — user-facing chat interface
- **OpenClaw** — AI agent that interprets natural language and calls the backend API
- **FastAPI backend** — stateless REST API handling task CRUD, stopwatch, conflict detection, state machine
- **SQLite** — persistent task storage with Alembic migrations
- **Redis** — stopwatch sessions, undo cache, sync queues
- **Notion** — calendar sync (two-way page create/update)

## Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| API         | Python 3.11, FastAPI, Uvicorn       |
| ORM         | SQLAlchemy 2.0, Alembic             |
| Cache       | Redis 7                             |
| Database    | SQLite                              |
| Sync        | Notion API                          |
| AI Agent    | OpenClaw                            |
| Container   | Docker, Docker Compose              |

## Prerequisites

- **Docker Desktop** (with Compose V2)
- **OpenClaw** installed separately — [github.com/openclaw/openclaw](https://github.com/openclaw/openclaw)

## Setup

### 1. Clone

```bash
git clone https://github.com/your-username/lyra-secretary.git
cd lyra-secretary
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in the required keys in `.env`:

| Key                  | Required | Where to get it                                          |
|----------------------|----------|----------------------------------------------------------|
| `NOTION_API_KEY`     | Yes      | [notion.so/my-integrations](https://notion.so/my-integrations) |
| `NOTION_DATABASE_ID` | Yes      | Copy from Notion database URL                            |
| `ANTHROPIC_API_KEY`  | Yes      | [console.anthropic.com](https://console.anthropic.com)   |
| `USER_TIMEZONE`      | Yes      | IANA timezone, e.g. `Africa/Cairo`                       |

### 3. Start services

```bash
docker-compose up -d --build
```

### 4. Run database migrations

```bash
docker-compose exec backend alembic upgrade head
```

### 5. Seed initial data (optional)

```bash
docker-compose exec backend python app/db/seed.py
```

### 6. Verify

```bash
curl http://localhost:8000/v1/health
# → {"status":"ok","service":"lyra-secretary"}
```

### 7. Explore the API

Open **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)

## OpenClaw Integration

OpenClaw runs as a **separate Docker stack**. To connect it to the Lyra backend:

1. **Connect to the Lyra network:**
   ```bash
   docker network connect lyrasecretaryv01_default <openclaw-container-name>
   ```
   Or add `lyrasecretaryv01_default` as an external network in OpenClaw's `docker-compose.yml`. See [DOCKER.md](DOCKER.md) for details.

2. **Install the skill:**
   Copy `openclaw/skills/lyra-secretary/SKILL.md` into your OpenClaw skills directory:
   ```bash
   cp -r openclaw/skills/lyra-secretary ~/.openclaw/skills/
   ```

3. **Verify connectivity:**
   ```bash
   docker exec <openclaw-container> curl -s http://backend:8000/v1/health
   # → {"status":"ok","service":"lyra-secretary"}
   ```

4. OpenClaw reaches the FastAPI backend at `http://backend:8000` (Docker service DNS).

## API Endpoints

All endpoints are under `/v1/`.

| Method | Endpoint       | Description                              |
|--------|----------------|------------------------------------------|
| POST   | `/v1/parse`    | Parse natural language → structured task |
| POST   | `/v1/create`   | Create a task                            |
| POST   | `/v1/reschedule` | Reschedule an existing task            |
| POST   | `/v1/delete`   | Soft-delete a task                       |
| POST   | `/v1/start`    | Start stopwatch for a task               |
| POST   | `/v1/stop`     | Stop active stopwatch                    |
| GET    | `/v1/status`   | Get stopwatch status                     |
| GET    | `/v1/health`   | Health check                             |

Full request/response schemas are documented in [`openclaw/skills/lyra-secretary/SKILL.md`](openclaw/skills/lyra-secretary/SKILL.md) and in Swagger UI at `/docs`.

## Current Status

- ✅ Parse natural language → structured task data
- ✅ Create / reschedule / delete tasks
- ✅ Query endpoint (search tasks by timeframe, category, state)
- ✅ Undo support (30-second TTL via Redis)
- ✅ Stopwatch with planned vs. actual duration delta
- ✅ Notion calendar sync (create + update pages)
- ✅ Conflict detection
- ✅ State machine (planned → executing → executed/skipped/deleted)
- ✅ OpenClaw integration via Docker network bridge

## Roadmap

- [ ] OpenClaw tool schema (structured tool definitions)
- [ ] BCI cognitive session logging (EEG state during tasks)
- [ ] Weekly/monthly analytics and pattern reports

## License

MIT
