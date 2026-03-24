---
name: lyra-secretary
description: Manage tasks and schedule via the Lyra Secretary backend API running at http://backend:8000
---

# Lyra Secretary – Task Management Skill

Lyra Secretary is a FastAPI backend for adaptive scheduling. All times are in **Africa/Cairo** timezone.
Use the `exec` tool with `curl` to call these endpoints.

---

## Endpoints

Base URL: `http://backend:8000/v1`

### 1. Parse Intent (stateless, fallback only)

Parses natural language into structured task data. Does NOT create anything.
**Use this only when time extraction is ambiguous** (e.g. "later today", "this evening", relative references).

```bash
curl -s -X POST http://backend:8000/v1/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "Gym at 9am tomorrow"}'
```

**Request body:**

| Field  | Type   | Required | Notes       |
|--------|--------|----------|-------------|
| `text` | string | yes      | 1–500 chars |

**Response:** `{ title, start, end, duration_minutes, category, confidence, ambiguities[] }`

---

### 2. Create Task

```bash
curl -s -X POST http://backend:8000/v1/create \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Gym",
    "start": "2026-03-24T07:00:00",
    "end": "2026-03-24T08:00:00",
    "category": "health",
    "force": false
  }'
```

**Request body:**

| Field              | Type     | Required | Default     | Notes                        |
|--------------------|----------|----------|-------------|------------------------------|
| `title`            | string   | yes      |             | 1–255 chars                  |
| `start`            | datetime | yes      |             | ISO 8601, **UTC**            |
| `end`              | datetime | yes      |             | Must be after start, **UTC** |
| `category`         | string   | no       | null        | e.g. "work", "health"        |
| `state`            | string   | no       | `"planned"` | planned/executing/executed   |
| `source`           | string   | no       | `"manual"`  | manual/voice/ai              |
| `confidence_score` | float    | no       | null        | 0.0–1.0                      |
| `force`            | bool     | no       | false       | true = ignore time conflicts |

**Response:** `{ task_id, created: bool, notion_synced: bool, conflicts[], can_proceed }`

If `created: false` → conflicts exist. Set `force: true` to override.
If `notion_synced: false` → task was created but Notion sync failed. Inform the user.

---

### 3. Reschedule Task

```bash
curl -s -X POST http://backend:8000/v1/reschedule \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "<uuid>",
    "new_start": "2026-03-24T12:00:00",
    "new_end": "2026-03-24T13:00:00"
  }'
```

**Request body:**

| Field       | Type     | Required | Notes                                   |
|-------------|----------|----------|-----------------------------------------|
| `task_id`   | string   | yes      | 36-char UUID                            |
| `new_start` | datetime | yes      | ISO 8601, **UTC**                       |
| `new_end`   | datetime | no       | If omitted, preserves original duration |

**Response:** `{ task_id, rescheduled: bool, new_start, new_end, conflicts[] }`

---

### 4. Delete Task (soft delete)

```bash
curl -s -X POST http://backend:8000/v1/delete \
  -H "Content-Type: application/json" \
  -d '{"task_id": "<uuid>"}'
```

**Request body:**

| Field     | Type   | Required | Notes        |
|-----------|--------|----------|--------------|
| `task_id` | string | yes      | 36-char UUID |

**Response:** `{ task_id, deleted: bool }`

---

### 5. Start Stopwatch

Starts a live timer. Links to an existing task, or creates an unplanned one if only `title` is given.

> **IMPORTANT:** Before starting a stopwatch, always call `GET http://backend:8000/v1/status` first. If `active=true`, inform the user a timer is already running and show `elapsed_minutes`.

```bash
curl -s -X POST http://backend:8000/v1/start \
  -H "Content-Type: application/json" \
  -d '{"task_id": "<uuid>"}'
```

Or for an unplanned task:

```bash
curl -s -X POST http://backend:8000/v1/start \
  -H "Content-Type: application/json" \
  -d '{"title": "Quick errand"}'
```

**Request body:**

| Field     | Type   | Required | Notes                          |
|-----------|--------|----------|--------------------------------|
| `task_id` | string | no       | 36-char UUID of existing task  |
| `title`   | string | no       | Required if task_id is omitted |

**Response:** `{ session_id, task_id, start_time }`

---

### 6. Stop Stopwatch

Stops the currently active stopwatch. No request body needed.

```bash
curl -s -X POST http://backend:8000/v1/stop \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response:** `{ task_id, session_id, duration_minutes, planned_duration_minutes, delta_minutes, executed_at }`

---

### 7. Stopwatch Status (read-only)

```bash
curl -s http://backend:8000/v1/status
```

**Response:** `{ active: bool, session_id, task_id, task_title, start_time, elapsed_minutes }`

---

### 8. Query Tasks

To check what tasks exist before creating, rescheduling, or deleting.

```bash
curl -s "http://backend:8000/v1/tasks/query?date=2026-03-24"
```

**Query parameters:**

| Param      | Type   | Required | Default     | Notes                    |
|------------|--------|----------|-------------|--------------------------|
| `date`     | string | no       |             | YYYY-MM-DD format        |
| `category` | string | no       |             | Filter by category       |
| `state`    | string | no       | `"planned"` | planned/executing/executed/skipped/deleted |

**Response:** `{ tasks: [{ task_id, title, start, end, state, category }], total: int }`

---

## Workflow

> **CRITICAL: Timezone Rule**
> Always convert times to ISO 8601 with **no timezone suffix**. Africa/Cairo is UTC+2 in winter, UTC+3 in summer (EET/EEST). If user says "9am", pass `07:00:00` (winter) or `06:00:00` (summer) as UTC. When in doubt, call `/v1/parse` and use the `start` value it returns.

1. When the user says something like "schedule gym at 9am tomorrow":
   - Extract the title, start, and end times yourself
   - Convert local time to UTC (subtract 2h in winter / 3h in summer)
   - Call **create** directly with the extracted fields
   - If time is ambiguous (e.g. "later", "this evening"), call **parse** first as a fallback
   - If conflicts returned, inform the user and ask whether to force
   - If `notion_synced: false`, tell the user "Task created but Notion sync failed"

2. When the user says "start timer for \<task\>":
   - First call **status** (`GET /v1/status`) to check if a stopwatch is already running
   - If `active=true`, tell the user: "A timer is already running for {task_title} ({elapsed_minutes} min). Stop it first."
   - If `active=false`, call **start** with the task_id or title

3. When the user says "stop" or "done":
   - Call **stop** (no body needed)

4. To check what tasks exist:
   - Call **query** (`GET /v1/tasks/query?date=YYYY-MM-DD`)
   - Always query before asserting a task exists or doesn't exist

5. Always confirm actions to the user with the response data.
