# Lyra Secretary — Bug Tracker

Last updated: April 4, 2026 — v1.3. 35 open, 37 fixed.

---

## Open (35 bugs)

| ID | Priority | Tag | Title | Notes |
|----|----------|-----|-------|-------|
| LYR-007 | 🟡 medium | openclaw | OpenClaw memory vs actual state | Hard constraint in SKILL.md not fully validated. If task deleted via Swagger, OpenClaw may still believe it exists. |
| LYR-015 | 🟡 medium | notion | No backfill for pre-fix tasks | Tasks created before Notion sync fix exist in SQLite but not in Notion. Need `POST /v1/tasks/{task_id}/sync`. |
| LYR-018 | 🟢 low | notion | Orphaned SQLite records in conflict messages | Old tasks in SQLite but not in Notion appear in conflict detection. Same class as LYR-015. |
| LYR-019 | 🟡 medium | skill | Day-of-week label mismatch | Lyra labeled Friday Mar 27 as "Thursday Mar 27". Day label wrong in weekly view. |
| LYR-020 | 🟢 low | notion | Test tasks polluting schedule | Smoke test tasks still visible in Notion. Need cleanup. |
| LYR-035 | 🟡 medium | skill | Task ID retrieved from memory not backend | On delete/start, Lyra uses conversation memory for task ID instead of querying backend. Hard Rule #6 added but not fully validated. |
| LYR-036 | 🟡 medium | skill | Context lost on follow-up corrections | Short follow-ups like "next week" treated as new standalone request instead of continuing previous intent. |
| LYR-037 | 🟡 medium | skill | False conflict between tasks on different days | Hallucinated conflict between Monday and Tuesday tasks. Likely ghost records from bad-UTC era. Retest on clean database. |
| LYR-042 | 🟡 medium | skill | Clear schedule leaves EXECUTING tasks | Clear schedule only deletes PLANNED tasks. Should stop active timers first, then delete. |
| LYR-043 | 🔴 high | skill | Duplicate task created instead of using existing | When starting timer, Lyra creates new task from memory instead of querying backend for existing PLANNED task. Hard Rule #6 should fix — not yet fully validated. |
| LYR-045 | 🟡 medium | notion | Duplicate EXECUTING tasks in Notion | Ghost tasks from memory leaked into Notion. Downstream of LYR-043. |
| LYR-046 | 🟡 medium | notion | Category field null in Notion after task executes | Category present on create but cleared on update sync. Likely conditional in `_build_properties()` skipping category during updates. |
| LYR-047 | 🟢 low | notion | "Past Due" showing on EXECUTED tasks | Status groups correctly configured (EXECUTED in Complete). Notion platform limitation — no programmatic fix available. Document only. |
| LYR-048 | 🔴 high | skill | Early-stop gate bypassed — model calls `?confirmed=true` directly | GLM skips `/stop` entirely and calls `/stop?confirmed=true` without user input. Confirmed via logs. Hard Rule #5 strengthened but not yet re-validated. |
| LYR-049 | 🔴 high | skill | Reschedule used as proxy for stopwatch/start on model switch | Sonnet without SKILL.md context improvises wrong endpoints — uses `/v1/reschedule` instead of `/v1/stopwatch/start`. Happens when model switches mid-session and new model has no skill context. Root cause same as LYR-051. |
| LYR-050 | 🟡 medium | data | `initiation_status` stuck on `not_started` for historical EXECUTED tasks | Tasks created before discrepancy fields existed completed successfully but never had `initiation_status` set. Backfill script needed: set `initiated` on all EXECUTED tasks where `initiation_status = 'not_started'`. |
| LYR-051 | 🔴 high | openclaw | Tasks confirmed to user but never POSTed to backend | Lyra says "scheduled" without a `task_id`. Hard Rule #7 added. Root cause: model loses SKILL.md context on rate-limit fallback and improvises confirmation without calling the API. Needs validation after rate-limit recovery. |
| LYR-052 | 🟡 medium | openclaw | Reminder cron fires during active session → `LiveSessionModelSwitchError` | Isolated cron session clashes with live session's model state; delivery silently dropped. Partially addressed by backend-direct Telegram delivery (no longer OpenClaw-dependent). Needs validation that direct path fires reliably. |
| LYR-053 | 🟡 medium | openclaw | Exec approval not enabled on Telegram — blocks autonomous skill execution | Every HTTP tool call requires Web UI approval rather than auto-approving on Telegram. Must enable exec approvals for Telegram channel in `openclaw.json` `gateway.nodes` or exec-approvals config. |
| LYR-054 | 🟢 low | data | `category` null on tasks without explicit category context | Parser not inferring category from task title when user omits it (e.g. "lec 2 AI" → `category: null`). `category_mapping` keyword lookup not applied during task creation via OpenClaw. |
| LYR-056 | 🟡 medium | parser | Multi-task chaining via "then" keyword not supported | Only first task in a compound request gets created. Second task silently dropped, no error returned. Fix: `TaskParser.parse_chained()` added — splits on "then", chains end→start for tasks without explicit time. `/v1/parse` endpoint updated to return `{ tasks: [...], compound: bool }`. |
| LYR-057 | 🔴 high | skill | Stopwatch called with `title` instead of `task_id` → 404 | Model calls `/v1/stopwatch/start` with `{"title": "..."}` instead of querying first for `task_id`. Returns 404, timer never starts. Hard Rule #8 added to SKILL.md. Needs validation. |

| LYR-058 | 🟢 low | backend | Stopwatch API returns UTC datetimes to agent | `start_time`, `executed_at`, `paused_at` in stopwatch responses were raw UTC. Agent sees wrong times. Fixed: all datetime fields now pass through `to_local()`. |
| LYR-059 | 🟡 medium | openclaw | Haiku 4.5 uses curl shell commands instead of HTTP tool | Triggers exec approval on every backend call. SKILL.md rule updated to allow curl as fallback. |
| LYR-060 | 🟢 low | backend | 5-minute task overflow notification didn't fire | APScheduler may not catch short-duration tasks that complete before the 2-min poll interval. |
| LYR-061 | 🟡 medium | backend | Insight fires after 1 session with noise data | Threshold check not working, fires before `min_sessions_required=3`. |
| LYR-062 | 🟡 medium | openclaw | Lyra approves its own exec requests | `/approve` sent by agent not user — approval loop bypasses security intent. |
| LYR-063 | 🔴 high | openclaw | auth-profiles.json caches billing failure from old API key | New key never picked up without manual edit of `~/.openclaw/agents/main/agent/auth-profiles.json`. OpenClaw doesn't re-read env vars into cached credential store. |
| LYR-064 | 🟡 medium | docker | ANTHROPIC_API_KEY not passed to OpenClaw Docker container | Requires manual `docker-compose.yml` env entry. Key in `.env` but not mapped in compose environment block. |
| LYR-065 | 🟡 medium | openclaw | Qwen3.5:9b assumes readiness 5/5 without asking | Hard Rules ignored by local model. Readiness/reflection capture skipped entirely. |
| LYR-066 | 🔴 high | openclaw | Qwen3.5:9b deletes tasks without user confirmation to resolve conflicts | Violates Hard Rule #1 and #2. Local model doesn't follow SKILL.md constraints. |
| LYR-067 | 🟡 medium | openclaw | Qwen3.5:9b gets stuck replaying cached response in loop under GPU load | Model repeats same output indefinitely when Ollama is under memory pressure. |
| LYR-068 | 🟡 medium | notion | Notion date property timezone confusion | UTC offset in payload causes double conversion depending on property timezone setting. |
| LYR-069 | 🟢 low | openclaw | Claude 3 Haiku too old to load skill system | Ignores SKILL.md entirely, uses built-in cron instead of Lyra endpoints. |
| LYR-070 | 🟡 medium | backend | Conflict detection fires on EXECUTED tasks | Tasks in EXECUTED/SKIPPED/DELETED state should not block new task creation in the same time slot. Only PLANNED and EXECUTING states should conflict. Fix in `conflict_detector.py`: filter candidate tasks to `state IN ('PLANNED', 'EXECUTING')` before checking overlap. |

---

## Fixed (37 bugs)

| ID | Priority | Tag | Title | Fix |
|----|----------|-----|-------|-----|
| LYR-001 | 🔴 high | backend | Past time not rejected | `create_task()` rejects start >5min in past. Confirmed working. |
| LYR-002 | 🔴 high | skill | OpenClaw reports wrong time to user | SKILL.md Hard Rule #4: report `start` from API response, never own extraction. |
| LYR-003 | 🟡 medium | backend | Stopwatch path inconsistency | Router prefixed with `/stopwatch`. Paths now `/v1/stopwatch/start`, `/v1/stopwatch/stop`, `/v1/stopwatch/status`. Confirmed 404 on old paths. |
| LYR-004 | 🔴 high | backend | Missing `GET /v1/tasks/query` | Implemented in `query.py`, registered in router, documented in SKILL.md. |
| LYR-005 | 🔴 high | notion | Notion sync silently failing | `notion_synced` bool now returned in response. Silent swallowing removed. |
| LYR-006 | 🟡 medium | skill | Double parsing | OpenClaw extracts fields itself. `/v1/parse` is fallback only. |
| LYR-008 | 🔴 high | docker | Docker network isolation | Permanent `docker-compose.yml` networks config. OpenClaw joins backend network on startup. |
| LYR-009 | 🟡 medium | backend | Telegram token in backend `.env` | Removed. Telegram belongs to OpenClaw only. |
| LYR-010 | 🟢 low | docker | SKILL.md not auto-synced | Symlinked to volume-mounted path. Auto-syncs into OpenClaw on restart. |
| LYR-011 | 🔴 high | backend | Timezone pipeline broken — ROOT CAUSE | OpenClaw sends UTC, stored as-is. `notion_client` converts UTC→Cairo with `+02:00` before sending to Notion. |
| LYR-012 | 🟡 medium | backend | No duplicate request protection | Redis idempotency via `X-Idempotency-Key` header, 30s TTL. |
| LYR-013 | 🔴 high | skill | Query endpoint not called — memory used | Hard constraint added to SKILL.md. Confirmed working. |
| LYR-014 | 🔴 high | skill | Wrong time reported on query | Fixed by SKILL.md Hard Rule #4. |
| LYR-016 | 🔴 high | skill | Wrong time reported on create | Fixed by SKILL.md Hard Rule #4. |
| LYR-017 | 🟡 medium | backend | Meeting created in the past | Fixed by LYR-001 past-time validation. |
| LYR-021 | 🟡 medium | skill | Timer started for future task without warning | `stopwatch_manager.start()` returns `is_future_task: bool`. SKILL.md requires yes/no confirmation. Confirmed working via Telegram. |
| LYR-022 | 🔴 high | backend | Task stuck on EXECUTING after timer stop | `sync_task(db)` called after every state mutation. |
| LYR-023 | 🔴 high | notion | Reschedule creates duplicate Notion pages | `notion_page_id` persisted to DB. Future syncs call `pages.update()` instead of `pages.create()`. |
| LYR-024 | 🔴 high | backend | Early-stop prompt not enforced | Backend gate: `/v1/stopwatch/stop` returns `requires_confirmation: true` if elapsed < 50% planned. `?confirmed=true` required to proceed. Confirmed working via Telegram with Sonnet. |
| LYR-025 | 🟡 medium | notion | Soft delete not reflected in Notion | `delete_task()` calls `archive_page()` with error logging. |
| LYR-026 | 🔴 high | backend | Delete endpoint enum .value error (original) | `hasattr(x, 'value')` guard applied to delete endpoint. Confirmed working. |
| LYR-027 | 🟡 medium | skill | State disagreement SQLite vs Notion | Fixed by LYR-022 — state now syncs to Notion on every mutation. |
| LYR-028 | 🟡 medium | skill | Bulk delete without confirmation | SKILL.md Hard Rule #2: list tasks and confirm before bulk delete. |
| LYR-029 | 🔴 high | skill | Batch create auto-forces conflicts | SKILL.md Hard Rule #1: never auto-force, always ask user. |
| LYR-030 | 🟡 medium | skill | Generic task names created | SKILL.md Hard Rule #3: never use generic names like "Task 1". |
| LYR-032 | 🔴 high | notion | Bulk reschedule creates duplicates | Fixed by LYR-023. |
| LYR-033 | 🔴 high | notion | State split between SQLite and Notion | Fixed by LYR-022. |
| LYR-040 | 🔴 high | backend | `'str' object has no attribute 'value'` in state machine | `state_machine.py` normalizes `task.state` to `TaskState` enum. All `.value` calls guarded with `hasattr()`. Confirmed: clean 400 on immutable delete. |
| LYR-041 | 🔴 high | backend | Stopwatch/Redis desync | `_recover_from_db()` added to `StopwatchManager`. Restores Redis from SQLite on desync. Fixed 3-tuple unpack in unplanned task creation. |
| LYR-044 | 🔴 high | notion | Notion sync fails on stopwatch stop | Removed invalid `Duration` property from `_build_properties()`. Notion sync now succeeds on task completion. Confirmed `Notion synced: ✅` via Telegram. |
| LYR-GET | 🟡 medium | backend | Missing single task fetch endpoint | `GET /v1/tasks/{task_id}` implemented. Returns full TaskDetail. Router reordered to prevent `/query` collision. Enables Hard Rule #6 verification flow. |
| LYR-UNDO | 🟡 medium | backend | Missing undo endpoint | `POST /v1/undo` implemented. 30-second TTL via Redis. Reverts `create_task` (soft-delete) and `delete_task` (restore to PLANNED). Confirmed working via curl and Telegram. |
| LYR-SCHED | 🟡 medium | backend | Missing APScheduler background workers | `scheduler.py` + 4 jobs: reminders (1min), Notion retry (5min), timer overflow (2min). Hooked into FastAPI lifespan. Confirmed firing via logs. |
| LYR-NOTIF | 🟡 medium | backend | No notification delivery to Telegram | Polling system implemented. Backend pushes to `POST /v1/notifications/push`. OpenClaw polls `GET /v1/notifications/pending` every 30s. Verified queue push/pop working. |
| LYR-RULE6 | 🟡 medium | skill | No backend verification before mutations | Hard Rule #6 added to SKILL.md: always call query + single fetch before any timer start, delete, or reschedule. |
| LYR-DISC | 🟡 medium | backend | No cognitive measurement data captured | Discrepancy measurement layer implemented: `pre_task_readiness`, `post_task_reflection`, `initiation_status`, `initiation_delay_minutes` on Task model. `discrepancy_score` property. Abandoned task detection job (30 min). `GET /v1/analytics/discrepancy` endpoint. Readiness/reflection capture workflow added to SKILL.md. Migration 002 applied. |
| LYR-055 | 🟢 low | docker | `version` attribute in docker-compose.yml generates warning | `version: "3.8"` is obsolete in Docker Compose v2+; generates warning on every command. Removed. |

---

## Priority Order for Next Session

### Critical (🔴)
1. LYR-063 — OpenClaw caches stale API keys in auth-profiles.json; billing failures block model permanently
2. LYR-066 — Qwen3.5:9b deletes tasks without confirmation; local models ignore Hard Rules
3. LYR-051 — validate Hard Rule #7 stops "scheduled without task_id" pattern
4. LYR-048 — validate Hard Rule #5 fix with Haiku (GLM bypass confirmed)
5. LYR-049 — skill context loss on model switch; model improvises wrong endpoints

### Medium (🟡)
6. LYR-064 — ANTHROPIC_API_KEY not in docker-compose.yml env block (fixed locally, needs upstream)
7. LYR-059 — Haiku uses curl instead of HTTP tool; SKILL.md rule softened
8. LYR-065 — Qwen3.5:9b skips readiness/reflection capture
9. LYR-062 — agent approves its own exec requests
10. LYR-061 — insights fire after 1 session, should require 3
11. LYR-053 — enable exec approvals on Telegram
12. LYR-057 — validate Hard Rule #8 fix; stopwatch/start with task_id only
13. LYR-043 — validate Hard Rule #6 fixes duplicate task creation
14. LYR-052 — validate backend-direct Telegram reminders
15. LYR-067 — Qwen3.5:9b loops under GPU load
16. LYR-068 — Notion date timezone double conversion
17. LYR-046 — category cleared on Notion update
18. LYR-042 — clear schedule leaves EXECUTING tasks
19. LYR-056 — validate "then" chaining in parse_chained()
20. LYR-050 — backfill initiation_status on historical tasks
21. LYR-035 — validate Hard Rule #6 covers memory ID issue
22. LYR-036 — context lost on follow-up corrections

### Low (🟢)
23. LYR-060 — overflow notification misses short tasks
24. LYR-069 — Claude 3 Haiku too old for skill system
25. LYR-054 — category_mapping inference at creation time
26. LYR-037 — retest false conflict on clean database
27. LYR-015 + LYR-018 + LYR-020 — backfill sync, clean test data
28. LYR-019 — day-of-week label fix
29. LYR-007 — validate memory constraint
30. LYR-047 — document as Notion limitation
