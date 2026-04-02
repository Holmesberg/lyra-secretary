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

> **Note**: The backend scheduler sends notifications to OpenClaw at `POST http://openclaw-gateway:18789/api/notify`.
> This endpoint must be enabled in `openclaw.json` under `agents.webhooks` or `gateway.hooks` configuration.
> If not available, notifications log to backend only.

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
| `title`            | string   | yes      |             | 1–255 chars                         |
| `start`            | datetime | yes      |             | ISO 8601, **Cairo local**           |
| `end`              | datetime | yes      |             | Must be after start, **Cairo local** |
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
| `new_start` | datetime | yes      | ISO 8601, **Cairo local**               |
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

> **IMPORTANT:** Before starting a stopwatch, always call `GET http://backend:8000/v1/stopwatch/status` first. If `active=true`, inform the user a timer is already running and show `elapsed_minutes`.

```bash
curl -s -X POST http://backend:8000/v1/stopwatch/start \
  -H "Content-Type: application/json" \
  -d '{"task_id": "<uuid>", "pre_task_readiness": 4}'
```

Or for an unplanned task:

```bash
curl -s -X POST http://backend:8000/v1/stopwatch/start \
  -H "Content-Type: application/json" \
  -d '{"title": "Quick errand", "pre_task_readiness": 3}'
```

**Request body:**

| Field                | Type    | Required | Notes                                          |
|----------------------|---------|----------|------------------------------------------------|
| `task_id`            | string  | no       | 36-char UUID of existing task                  |
| `title`              | string  | no       | Required if task_id is omitted                 |
| `pre_task_readiness` | integer | no       | 1–5 self-rated sharpness before task starts    |

**Response:** `{ session_id, task_id, start_time, pre_task_readiness, initiation_delay_minutes }`

---

### 6. Stop Stopwatch

Stops the currently active stopwatch. Optional body to pass reflection score.

```bash
curl -s -X POST http://backend:8000/v1/stopwatch/stop \
  -H "Content-Type: application/json" \
  -d '{"post_task_reflection": 3}'
```

To update reflection on an already-completed task (within last 10 min):

```bash
curl -s -X POST http://backend:8000/v1/stopwatch/stop \
  -H "Content-Type: application/json" \
  -d '{"post_task_reflection": 2}'
```

**Request body:**

| Field                  | Type    | Required | Notes                                        |
|------------------------|---------|----------|----------------------------------------------|
| `post_task_reflection` | integer | no       | 1–5 self-rated focus quality after task ends |

**Response:** `{ task_id, session_id, duration_minutes, planned_duration_minutes, delta_minutes, executed_at, post_task_reflection, discrepancy_score }`

---

### 7. Discrepancy Analytics

```bash
curl -s http://backend:8000/v1/analytics/discrepancy
```

**Response:** `{ sessions: [...], summary: { total_sessions, initiated_count, abandoned_count, avg_discrepancy, avg_delta_minutes, avg_initiation_delay_minutes } }`

Each session includes: `task_id, title, date, planned_duration_minutes, executed_duration_minutes, delta_minutes, pre_task_readiness, post_task_reflection, discrepancy_score, initiation_status, initiation_delay_minutes, category, time_of_day, session_index_in_day`

---

### 8. Stopwatch Status (read-only)

```bash
curl -s http://backend:8000/v1/stopwatch/status
```

**Response:** `{ active: bool, session_id, task_id, task_title, start_time, elapsed_minutes }`

---

### 9. Query Tasks

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

### 10. Get Single Task
```bash
curl -s http://backend:8000/v1/tasks/<uuid>
```

**Response:** full task detail including state, category, times, delta.

---

## Workflow

> **CRITICAL: Timezone Rule**
> All times must be sent as **Africa/Cairo local time** in ISO 8601 format with **no timezone suffix**. The backend converts to UTC internally. If the user says "9am", send `09:00:00`. Do NOT subtract hours or convert to UTC yourself. When in doubt, call `/v1/parse` and use the `start` value it returns.

1. When the user says something like "schedule gym at 9am tomorrow":
   - Extract the title, start, and end times yourself
   - Send times as **Cairo local** — if user says "9am", send `09:00:00`
   - Call **create** directly with the extracted fields
   - If time is ambiguous (e.g. "later", "this evening"), call **parse** first as a fallback
   - If conflicts returned, inform the user and ask whether to force
   - If `notion_synced: false`, tell the user "Task created but Notion sync failed"

2. When the user says "start timer for \<task\>":
   - First call **status** (`GET /v1/stopwatch/status`) to check if a stopwatch is already running
   - If `active=true`, tell the user: "A timer is already running for {task_title} ({elapsed_minutes} min). Stop it first."
   - If `active=false`:
     **READINESS CAPTURE (mandatory):**
     Ask: "Quick check — how sharp are you right now? (1=exhausted, 3=neutral, 5=very sharp)"
     Wait for user reply. Use the number as `pre_task_readiness`. If user says "skip" or doesn't reply with a number, use `null`. Never skip asking.
   - Call **start** with the task_id (or title) and `pre_task_readiness`
   - If the response has `is_future_task: true`, **do NOT proceed automatically**. Warn the user:
     "⚠️ This task is scheduled for {planned_start}. It hasn't started yet. Start the timer anyway? (yes/no)"
     Wait for explicit **"yes"** before calling start again. If user says **"no"**, do nothing.

3. When the user says "stop" or "done":
   - Call **stop** (`POST /v1/stopwatch/stop`, empty body `{}`) first
   - If the response has `requires_confirmation: true`:
     - Show the `confirmation_message` to the user
     - Ask: "Is the task complete? (yes/no)"
     - If user says **"yes"**:
       **REFLECTION CAPTURE (mandatory):**
       Ask: "How was your actual focus? (1=very poor, 3=average, 5=excellent)"
       Wait for user reply. Use the number as `post_task_reflection`. If user skips, use `null`.
       Call `POST /v1/stopwatch/stop?confirmed=true` with body `{"post_task_reflection": <value>}`
     - If user says **"no"**: call `GET /v1/stopwatch/status` and report elapsed time — timer is still running
   - If `requires_confirmation` was false (normal stop), after stop returns:
     **REFLECTION CAPTURE (mandatory):**
     Ask: "How was your actual focus? (1=very poor, 3=average, 5=excellent)"
     Wait for user reply. Call `POST /v1/stopwatch/stop` again with body `{"post_task_reflection": <value>}`.
     Do NOT confirm task completion to user until reflection is captured.
   - If the response has `notion_synced: false`, add: "Task logged but Notion may not reflect this yet."

4. To check what tasks exist:
   - Call **query** (`GET /v1/tasks/query?date=YYYY-MM-DD`)
   - Always query before asserting a task exists or doesn't exist

5. Always confirm actions to the user with the response data.

6. **UNDO WORKFLOW**:
   - If user says 'undo', 'wait no', 'cancel that', 'mistake' immediately after a create or delete action, call `POST http://backend:8000/v1/undo` with no body.
   - Report what was undone based on the API response.

7. **PROACTIVE NOTIFICATIONS**:
   - Every 30 seconds, poll `GET http://backend:8000/v1/notifications/pending`
   - If count > 0, send each notification message to the user via Telegram.
   - Clear after sending (already handled by the endpoint).


---

## Hard Rules (NEVER violate)

1. **NEVER auto-force a conflict.** When `/v1/create` returns `created: false` with conflicts, always show the full conflict list to the user and ask "Force schedule anyway?" before calling create with `force: true`. Do not silently override conflicts.

2. **NEVER perform bulk destructive operations without confirmation.**
This includes ANY phrasing like: "cancel everything", "delete all tasks", "clear my calendar", "clear everything", "wipe my schedule", "start fresh", or any request to delete multiple tasks at once.

Required steps before any bulk delete:
- Call GET /v1/tasks/query to list all affected tasks
- Show the list: "This will delete X tasks: [names]. Confirm?"
- Only proceed after explicit "yes" or "confirm" from user

3. **NEVER create tasks with generic names.** If the user asks for multiple tasks without specifying names (e.g. "5 back to back tasks"), ask for the name of each task before creating. Do not use "Task 1", "Task 2", etc.

4. **Always report times from the API response**, never from your own extraction. After calling `/v1/create`, report the `start` and `end` values from the response JSON, not what you extracted from the user's input.

5. **HARD RULE #5 — EARLY STOP GATE (NEVER BYPASS)**
When stopping a timer:
Step 1: ALWAYS call `POST /v1/stopwatch/stop` (no params) first.
Step 2: If response has `requires_confirmation: true` —
  - Show the `confirmation_message` to the user
  - **STOP ALL API CALLS**
  - Wait for explicit user reply: 'yes'/'done'/'1' OR 'no'/'pause'/'2'
  - Only after receiving reply: call `/stop?confirmed=true` or `/status`
Step 3: NEVER call `/stop?confirmed=true` as the first call.
NEVER call `/stop?confirmed=true` without first receiving explicit user input in this conversation turn. 
The `?confirmed=true` parameter is ONLY valid as a follow-up to a `requires_confirmation: true` response AND explicit user reply.
Calling `?confirmed=true` directly bypasses user consent and is forbidden.

6. **HARD RULE #6 — VERIFY BEFORE ACTING.**
Before starting a timer, deleting, or rescheduling any task referenced by name or from memory:
1. Call `GET /v1/tasks/query` to find the task_id
2. Call `GET /v1/tasks/{task_id}` to verify current state
3. Only then proceed with the action
NEVER use a task_id from conversation memory without verifying it still exists and is in the expected state.

7. **HARD RULE #7 — ALWAYS USE LYRA SECRETARY FOR SCHEDULING**
Any request containing "schedule", "add task", "remind me", "set a timer", "block time", "plan", or "add to my schedule" MUST call POST /v1/create and receive a task_id back before confirming to the user. If no task_id returned, tell the user the API call failed. Never say "I've scheduled" without a task_id.
