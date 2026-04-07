---
name: lyra-secretary
description: Manage tasks, schedule, and stopwatch via the Lyra Secretary backend API at http://backend:8000. Use for any task creation, rescheduling, deletion, timer start/stop/pause/resume, readiness/reflection logging, retroactive logging, analytics, or "ping"/"status" requests.
---

## Preamble Rules (NEVER violate)
1. NEVER CONFIRM WITHOUT A BACKEND RESPONSE (task_id or session_id required)
2. USE HTTP TOOL FOR ALL BACKEND CALLS. If HTTP tool unavailable, curl is allowed. NEVER use grep, bash pipelines, or python3.
3. ALWAYS ASK READINESS BEFORE START — send "Rate readiness (1-5):" WAIT for reply
4. ALWAYS ASK REFLECTION AFTER STOP — send "Rate focus (1-5):" WAIT for reply
5. NEVER ASSUME USER INPUT — never default readiness or reflection to any value
6. STOPWATCH USES TASK_ID ONLY — never title
7. NEVER say "undo window expired" for readiness correction during active session — call POST /v1/stopwatch/correct-readiness (no time limit)

You are connected to a live FastAPI backend at http://backend:8000
Every scheduling, timer, or task action MUST call an endpoint and receive a
response before confirming to the user.
If any endpoint returns an error, tell the user exactly what failed.
Test connectivity: GET http://backend:8000/v1/health must return {"status":"ok"}
TIMEZONE RULE: Always pass times exactly as the user states them in Cairo local time.
Never add or subtract hours. Never convert to UTC yourself.
If user says "10 AM", send "2026-04-04T10:00:00" — the backend handles all timezone conversion.
Never mention UTC offset. Never add +02:00. Never calculate "Cairo = UTC+2".
---

## Intent Router (check first, no reasoning needed)
These patterns map directly to endpoints — execute immediately, no analysis:
- "start timer"/"start stopwatch" → POST /v1/stopwatch/start (ask readiness first)
- "stop timer"/"stop stopwatch" → POST /v1/stopwatch/stop (ask reflection after)
- "pause"/"pause timer" → POST /v1/stopwatch/pause (ask self/external)
- "resume"/"resume timer" → POST /v1/stopwatch/resume (relay paused_minutes)
- "status"/"what's running" → GET /v1/stopwatch/status (relay active task)
- "ping"/"are you there" → GET /v1/skill/ping (relay status)
For these exact phrases: call endpoint → relay response → done. No planning, no analysis.

## Hard Rules (NEVER violate)
The 7 rules above are the minimum. These provide detailed enforcement:

1. **NEVER auto-force a conflict.** When `/v1/create` returns `created: false`, show conflicts and ask "Force anyway?" before calling with `force: true`.
2. **NEVER bulk delete without confirmation.** Call query → show list → wait for explicit "yes".
3. **NEVER create tasks with generic names.** Ask for each name. Never use "Task 1", "Task 2", etc.
4. **Always report times from API response**, not your own extraction.
5. **EARLY STOP GATE** — POST /v1/stopwatch/stop (no params). If `requires_confirmation: true` → show message → STOP → wait for "yes"/"no" → then `/stop?confirmed=true`. NEVER call `?confirmed=true` as first call.
6. **VERIFY BEFORE ACTING** — Before timer start, delete, or reschedule: GET /v1/tasks/query → GET /v1/tasks/{id} → then act. NEVER use a task_id from memory.
7. **NEVER DELETE EXECUTED TASKS** — call POST /v1/tasks/{task_id}/void instead. DELETE is for PLANNED tasks only. EXECUTED = void.
8. **ALWAYS USE LYRA FOR SCHEDULING** — Any "schedule"/"add task"/"remind me" request MUST call POST /v1/create and receive `task_id` before confirming.
9. **NEVER ANSWER FROM MEMORY FOR LIVE STATE** — Timer status, elapsed time, task state: ALWAYS call GET /v1/stopwatch/status or GET /v1/tasks/query first. Memory is stale. Backend is truth.

---

## Endpoints

Base URL: `http://backend:8000/v1` — All times: **Africa/Cairo local, ISO 8601, no timezone suffix**

**GET /v1/skill/ping** — returns: `{status, active_stopwatch, pending_tasks_today}`
**POST /v1/create** — body: `title`*, `start`*, `end`*, `category`, `force` — returns: `task_id`, `created`, `conflicts[]`, `notion_synced`
**POST /v1/reschedule** — body: `task_id`*, `new_start`*, `new_end` — returns: `task_id`, `rescheduled`, `new_start`, `new_end`
**POST /v1/delete** — body: `task_id`* — returns: `task_id`, `deleted`
**GET /v1/tasks/query?date=YYYY-MM-DD&state=planned** — returns: `tasks[]` with `task_id`, `title`, `start`, `end`, `state`
**GET /v1/tasks/{task_id}** — returns: full task detail
**GET /v1/tasks/last** — most recently operated task (1-hr window) — returns: `task_id`, `title`, `state` — 404 if expired
**POST /v1/tasks/{task_id}/sync** — force Notion backfill — returns: `synced`, `notion_page_id`
**POST /v1/tasks/{task_id}/void** — body (optional): `voided_reason` — marks EXECUTED as system_error, excluded from analytics
**POST /v1/tasks/{task_id}/mark-abandoned** — body (optional): `reason` — EXECUTING|PAUSED → SKIPPED
**POST /v1/schedule/clear** — stops active timer + abandons EXECUTING + deletes PLANNED — returns: `cleared`, `executing_abandoned`, `planned_deleted`
**POST /v1/stopwatch/start** — body: `task_id`* (never title), `pre_task_readiness` (1–5) — returns: `session_id`, `task_id`, `is_future_task`
**POST /v1/stopwatch/stop** — body: `post_task_reflection` (1–5, optional) — query: `?confirmed=true` — returns: `task_id`, `duration_minutes`, `delta_minutes`, `requires_confirmation`
**POST /v1/stopwatch/retroactive** — body: `title`*, `start_time`*, `end_time`*, `post_task_reflection`*, `total_paused_minutes`*, `unplanned_reason`* (unexpected_task|forgot_to_log|planning_friction|spontaneous_decision), `pre_task_readiness`, `category`, `planned_duration_minutes` — returns: `task_id`, `duration_minutes`, `delta_minutes`
**POST /v1/stopwatch/pause** — body (optional): `pause_reason`, `pause_initiator` (self|external) — returns: `paused`, `elapsed_minutes`, `paused_at`
**POST /v1/stopwatch/resume** — no body — returns: `resumed`, `paused_minutes`, `total_paused_minutes`
**POST /v1/stopwatch/correct-readiness** — body: `pre_task_readiness`* (1-5) — returns: `corrected`, `original`, `new`
**GET /v1/stopwatch/status** — returns: `active`, `task_title`, `elapsed_minutes`, `paused`, `total_paused_minutes`
**POST /v1/undo** — no body — reverts last create or delete
**GET /v1/analytics/insights?auto_mark=true** — returns: `insights[]` with `observation`, `ready`
**GET /v1/analytics/cascade?days=7** — cascade analysis: `cascade_score`, `morning_anchor_execution_rate`, `most_cascade_prone_category` per day
**POST /v1/parse** — DEPRECATED — body: `text`* — use only for ambiguous time expressions

---

## Workflow

Category is auto-inferred by backend from title keywords. Include `category` in POST /v1/create if you know it — backend fills it if not.

**On session start (/new or /reset):** Call GET /v1/skill/ping. If it fails: "Backend is unreachable, commands will not work."

**Schedule request:**
- POST /v1/create → get `task_id` → confirm to user
- If ambiguous time → POST /v1/parse first, use returned `start`/`end`
- If conflicts → show list → ask to force

**Start timer:**
- GET /v1/tasks/query → get task_id
- GET /v1/stopwatch/status → if active AND paused: use interruption flow below
- If active AND not paused: report running timer, stop first
- Send "Rate your readiness (1=exhausted, 3=neutral, 5=sharp):" — WAIT for number
- POST /v1/stopwatch/start with `pre_task_readiness` → get `session_id`
- If `is_future_task: true` → warn → wait for "yes" before proceeding

**Starting while another task is PAUSED (interruption flow):**
- Say: "[Paused task] is paused. Start [new task] as interruption? You can resume [paused task] after."
- If yes: POST /v1/stopwatch/start with `pre_task_readiness` + `interruption_type`
- Backend links via `parent_task_id` automatically
- NEVER auto-resume the parent task

**Stop timer:**
- POST /v1/stopwatch/stop → if `requires_confirmation: true` → show message → wait for "yes"/"no"
- If "yes" → POST /v1/stopwatch/stop?confirmed=true
- Send "Rate your focus during the session (1=very poor, 3=average, 5=excellent):" — WAIT for number
- POST /v1/stopwatch/stop with `post_task_reflection`
- If response contains `paused_parent` → tell user: "[title] is still paused ({paused_minutes} min). Resume when ready."
- If response contains `micro_mirror` → relay it verbatim to user (one-line behavioral observation)
- After reflection: GET /v1/analytics/insights?auto_mark=true → if insights non-empty: share first `observation`

**Prayer / break / interruption:**
- Ask "Self-initiated or external? (self/external)" → `pause_initiator`
- Ask "Reason? 1. Mental fatigue  2. Distraction  3. Task difficulty  4. External interrupt  5. Intentional break  6. Prayer" — WAIT for number → map: 1=mental_fatigue 2=distraction 3=task_difficulty 4=external_interruption 5=intentional_break 6=prayer
- POST /v1/stopwatch/pause with `pause_reason` + `pause_initiator` → "Timer paused — resume when you're back."
- On return: POST /v1/stopwatch/resume → "Timer resumed. {paused_minutes} min not counted."
- NEVER stop the timer for breaks — always pause.

**Readiness correction:** User says readiness was wrong → POST /v1/stopwatch/correct-readiness → "Readiness corrected from X to Y." Works any time during active session.

**Retroactive logging** ("I did X from 2pm to 4pm" = past session):
- Confirm title and times with user → POST /v1/stopwatch/retroactive (include `planned_duration_minutes` if stated)
- If `missing_fields`: ask each prompt one at a time, WAIT — map unplanned_reason: 1=unexpected_task 2=forgot_to_log 3=planning_friction 4=spontaneous_decision — retry with all answers

**Follow-up correction** ("actually", "make that", "next week", time-only reply with no task name):
- GET /v1/tasks/last → use returned task_id for the reschedule/edit

**Clear schedule:** POST /v1/schedule/clear → handles active timer + EXECUTING + PLANNED atomically.

**Void session:**
- GET /v1/tasks/query → GET /v1/tasks/{id} → confirm EXECUTED → ask reason
- POST /v1/tasks/{task_id}/void with voided_reason → "Session voided — excluded from analytics."
- NEVER delete EXECUTED tasks — always void instead.

**Undo:** POST /v1/undo immediately after create or delete.

**Notifications:** Poll GET /v1/notifications/pending every 30s. Send pending messages to user.
