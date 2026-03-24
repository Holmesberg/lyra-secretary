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

### 1. Parse Intent (stateless)

Parses natural language into structured task data. Does NOT create anything.

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
    "start": "2026-03-24T09:00:00",
    "end": "2026-03-24T10:00:00",
    "category": "health",
    "force": false
  }'
```

**Request body:**

| Field              | Type     | Required | Default     | Notes                        |
|--------------------|----------|----------|-------------|------------------------------|
| `title`            | string   | yes      |             | 1–255 chars                  |
| `start`            | datetime | yes      |             | ISO 8601                     |
| `end`              | datetime | yes      |             | Must be after start          |
| `category`         | string   | no       | null        | e.g. "work", "health"        |
| `state`            | string   | no       | `"planned"` | planned/executing/executed   |
| `source`           | string   | no       | `"manual"`  | manual/voice/ai              |
| `confidence_score` | float    | no       | null        | 0.0–1.0                      |
| `force`            | bool     | no       | false       | true = ignore time conflicts |

**Response:** `{ task_id, created: bool, conflicts[], can_proceed }`

If `created: false` → conflicts exist. Set `force: true` to override.

---

### 3. Reschedule Task

```bash
curl -s -X POST http://backend:8000/v1/reschedule \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "<uuid>",
    "new_start": "2026-03-24T14:00:00",
    "new_end": "2026-03-24T15:00:00"
  }'
```

**Request body:**

| Field       | Type     | Required | Notes                                   |
|-------------|----------|----------|-----------------------------------------|
| `task_id`   | string   | yes      | 36-char UUID                            |
| `new_start` | datetime | yes      | ISO 8601                                |
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

## Workflow

1. When the user says something like "schedule gym at 9am tomorrow":
   - Call **parse** first to extract structured data
   - Review the parsed result (check confidence)
   - Call **create** with the parsed fields
   - If conflicts returned, inform the user and ask whether to force

2. When the user says "start timer for \<task\>":
   - Call **start** with the task_id or title

3. When the user says "stop" or "done":
   - Call **stop** (no body needed)

4. Always confirm actions to the user with the response data.
