# Lyra Secretary — Bug Tracker

Last updated: April 21, 2026 — v1.10 (Path B P0 + delete hotfix). 13 open, 26 deferred (OpenClaw), 64 fixed.

---

## Open (13 bugs)

| ID | Priority | Tag | Title | Notes |
|----|----------|-----|-------|-------|
| LYR-018 | 🟢 low | notion | Orphaned SQLite records in conflict messages | Old tasks in SQLite but not in Notion appear in conflict detection. Same class as LYR-015. |
| LYR-020 | 🟢 low | notion | Test tasks polluting schedule | Smoke test tasks still visible in Notion. Need cleanup. |
| LYR-047 | 🟢 low | notion | "Past Due" showing on EXECUTED tasks | Status groups correctly configured (EXECUTED in Complete). Notion platform limitation — no programmatic fix available. Document only. |
| LYR-050 | 🟡 medium | data | `initiation_status` stuck on `not_started` for historical EXECUTED tasks | Tasks created before discrepancy fields existed completed successfully but never had `initiation_status` set. Backfill script needed: set `initiated` on all EXECUTED tasks where `initiation_status = 'not_started'`. |
| LYR-054 | 🟢 low | data | `category` null on tasks without explicit category context | Parser not inferring category from task title when user omits it (e.g. "lec 2 AI" → `category: null`). `category_mapping` keyword lookup not applied during task creation via OpenClaw. |
| LYR-060 | 🟢 low | backend | 5-minute task overflow notification didn't fire | APScheduler may not catch short-duration tasks that complete before the 2-min poll interval. |
| LYR-068 | 🟡 medium | notion | Notion date property timezone confusion | UTC offset in payload causes double conversion depending on property timezone setting. |
| LYR-080 | 🔴 high | backend | Backend rebuild during active paused session corrupts task/session references | Desync recovery restores pause time but loses task linkage. Delta not computed. stop response returns wrong task_id. |
| LYR-088 | 🟡 medium | backend | `resume()` loses Redis session reference after another stopwatch runs in between | Pause A → start B → stop B → resume A: Redis loses task A's active session reference. User continues work untracked. |
| LYR-091 | 🟢 low | backend | `resolve_user_from_token` matches by email only | `google_id` stays as `simulated-google-sub` placeholder after real sign-in. Upsert real `google_id` from JWT `sub` claim on first real sign-in. Phase 9 fix. |
| LYR-096 | 🟡 medium | frontend | `task_completion_percentage` dropped between ReflectionModal and stopStopwatch | `today/page.tsx:112` passes `{ confirmed }` but not `task_completion_percentage`. Value from modal never reaches backend. |
| LYR-097 | 🟡 medium | frontend | `is_future_task` warning from start endpoint not shown in UI | Backend returns `is_future_task: true` but frontend ignores it. No warning when starting timer for future task. |
| LYR-099 | 🟢 low | frontend | New task modal start time stale after idle | `defaultStart()` called once on mount. Reopening modal after 30min shows stale default time. |

---

## Fixed (64 bugs)

| ID | Priority | Tag | Title | Fix |
|----|----------|-----|-------|-----|
| LYR-100 | 🔴 high | backend | `DELETE /v1/users/me` fails with Postgres syntax error on `user` table | Raw SQL `DELETE FROM user WHERE user_id = :u` at `endpoints/users.py:223,230` hit `psycopg2.errors.SyntaxError: syntax error at or near "user"` because `user` is a reserved keyword in Postgres. Worked against SQLite in tests (non-reserved there). Surfaced when first non-operator user (user_id=8, moriartyholmesberg@gmail.com) tried to self-delete after onboarding 2026-04-21; operator is gated via `is_operator` check so the bug was latent for all dogfood prior. Fix: quote the table name as `DELETE FROM "user" WHERE user_id = :u` in both retain_for_research and hard-delete branches. SQLAlchemy ORM queries against User elsewhere auto-quote reserved identifiers; only the raw SQL in this endpoint bypassed that. No data corruption — the failing transaction rolled back atomically before commit. |
| LYR-056 | 🟡 medium | parser | Multi-task chaining via "then" keyword not supported | `TaskParser.parse_chained()` added in commit `5fa85d8` — splits on "then", chains end→start for tasks without explicit time. `/v1/parse` endpoint updated to return `{ tasks: [...], compound: bool }`. Apr-18 alignment-audit integrity pass: body already described fix; moved OPEN → FIXED. Multi-user validation pending post-alpha. |
| LYR-058 | 🟢 low | backend | Stopwatch API returns UTC datetimes to agent | Fixed in commit `9e7c650` — `start_time`, `executed_at`, `paused_at` in stopwatch responses now pass through `to_local()`. Apr-18 alignment-audit integrity pass: body already described fix; moved OPEN → FIXED. |
| LYR-092 | 🟡 medium | notion | notion_sync retry loop infinitely retries archived pages | Fixed in commit `951160e` — detects "Can't edit block that is archived" error and drops page from Redis retry queue permanently instead of re-queueing every 5 min. Note: commit message labels the fix `LYR-091` but LYR-091 is the unrelated `resolve_user_from_token` Phase-9 bug that remains OPEN; the `951160e` fix is actually for LYR-092. Apr-18 alignment-audit integrity pass resolved the ID collision. |
| LYR-098 | 🟡 medium | frontend | `micro_mirror` and `calibration_nudge` not displayed after stop | Shipped Apr 16 as 4 commits (fixture tests `553d7b0` → text neutralization + filter fix `a8aeae0` → `reflection_view_log` persistence + write-on-fire `0593d71` → Toast UI + dismiss callbacks `c8efff2`). Full feedback loop live: micro_mirror auto-dismiss, calibration_nudge pinned, both stamp viewed/dismissed to reflection_view_log. |
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
| LYR-015 | 🟡 medium | notion | No backfill for pre-fix tasks | Fixed: `POST /v1/tasks/{task_id}/sync` implemented. |
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
| LYR-036 | 🟡 medium | skill | Context lost on follow-up corrections | Fixed: `GET /v1/tasks/last` returns most recently operated task (1-hr TTL). SKILL.md rule added. |
| LYR-040 | 🔴 high | backend | `'str' object has no attribute 'value'` in state machine | `state_machine.py` normalizes `task.state` to `TaskState` enum. All `.value` calls guarded with `hasattr()`. Confirmed: clean 400 on immutable delete. |
| LYR-041 | 🔴 high | backend | Stopwatch/Redis desync | `_recover_from_db()` added to `StopwatchManager`. Restores Redis from SQLite on desync. Fixed 3-tuple unpack in unplanned task creation. |
| LYR-042 | 🟡 medium | skill | Clear schedule leaves EXECUTING tasks | Fixed: `POST /v1/schedule/clear` atomically stops timer + abandons EXECUTING + deletes PLANNED. |
| LYR-044 | 🔴 high | notion | Notion sync fails on stopwatch stop | Removed invalid `Duration` property from `_build_properties()`. Notion sync now succeeds on task completion. Confirmed `Notion synced: ✅` via Telegram. |
| LYR-046 | 🟡 medium | notion | Category field null in Notion after task executes | Fixed: `_build_properties()` always includes Category (empty array if null, preventing drift). |
| LYR-055 | 🟢 low | docker | `version` attribute in docker-compose.yml generates warning | `version: "3.8"` is obsolete in Docker Compose v2+; generates warning on every command. Removed. |
| LYR-061 | 🟡 medium | backend | Insight fires after 1 session with noise data | Fixed: MIN_SESSIONS=3 gate enforced. `_insight_discrepancy_signal()` returns None instead of noise message. |
| LYR-070 | 🟡 medium | backend | Conflict detection fires on EXECUTED tasks | Fixed: filter to `state IN ('PLANNED', 'EXECUTING')` only. Also fixed `is_mutable` to include SKIPPED. |
| LYR-073 | 🟡 medium | backend | Conflict detected with DELETED task | Fixed by LYR-070 — DELETED excluded from conflict detection. |
| LYR-074 | 🔴 high | backend | Undo window too short for readiness correction | Fixed: `POST /v1/stopwatch/correct-readiness` — no time limit, works during active session. Logs original value. |
| LYR-075 | 🟡 medium | backend | Overflow notification fires while timer is paused | Fixed: subtract `total_paused_minutes` and current pause from elapsed in `timer_overflow.py`. |
| LYR-076 | 🟡 medium | skill | "75%" completion misinterpreted as focus rating | Fixed: overflow prompt now says "Reply with 'done' or a completion percentage". |
| LYR-079 | 🟡 medium | backend | `session_index_in_day` not exposed in task query responses | Fixed: field was already present in `GET /v1/tasks/query` response; confirmed in this session. |
| LYR-083 | 🟡 medium | backend | Category inference returns wrong category for "debug session" | Fixed: `task_manager._infer_category` rewritten with word-boundary matching (exact word check before substring fallback). "debug" → development. |
| LYR-084 | 🟡 medium | backend | `unplanned_reason` bypassed when `planned_duration_minutes` present in retroactive | Fixed: removed bypass — `unplanned_reason` always required regardless of `planned_duration_minutes`. |
| LYR-085 | 🔴 high | backend | `POST /v1/schedule/clear` auto-stopped timer and mass-deleted PLANNED tasks without confirmation | Fixed: blocks with 400 `{"error":"active_timer"}` if stopwatch running. Only deletes PLANNED tasks; never touches EXECUTING/PAUSED. |
| LYR-086 | 🟡 medium | skill | Agent answered timer status from memory instead of calling backend | Fixed: SKILL.md Hard Rule #9 — never answer live state (timer, elapsed, task state) from memory; always call backend first. |
| LYR-087 | 🟡 medium | backend | DELETED tasks inflated cascade_score as false skips | Fixed: `_is_skip()` now only treats `SKIPPED` state as a skip; DELETED tasks filtered from each day's chain before cascade scoring. |
| LYR-089 | 🟡 medium | skill | Reflection not asked when early stop confirmed | Fixed: SKILL.md stop flow — ask reflection BEFORE `?confirmed=true` call. Eliminated the erroneous 3-call pattern. |
| LYR-090 | 🔴 high | backend | 0-minute active session marked EXECUTED instead of SKIPPED | Fixed: `StopwatchManager.stop()` early-exits with SKIPPED transition when `active_elapsed == 0`. Stop response includes `skipped: true, skip_reason: 'zero_duration'`. |
| LYR-095 | 🔴 high | backend | `get_status()` skips `_recover_from_db()` — banner disappears on Redis loss | Fixed: `get_status()` now falls through to `_get_active()`, which internally recovers from the DB when Redis is empty. Defense-in-depth `voided_at` filter added to `_recover_from_db()` so orphan voided sessions never rehydrate. Commits 9b7756f + this batch. |
| LYR-101 | 🔴 high | backend | Voided task still shows paused timer banner | Fixed: `void_task` endpoint now calls `StopwatchManager.void_cleanup()` atomically after stamping `voided_at`. Closes any unclosed `StopwatchSession` for the task and clears the user's Redis `active_stopwatch` + `pause_state` keys. Surfaced as 65h CO-block ghost on Apr 11. Commit 59ca80d. |
| LYR-102 | 🔴 high | skill | OpenClaw void failed with 422 on missing `voided_reason` | Fixed: SKILL.md endpoint line marks `voided_reason`* as required with full enum listed; workflow section adds "ALWAYS ASK REASON" rule with explicit "never pick a reason yourself, never default to system_error". Commit e57aa7e. |
| LYR-103 | 🔴 high | backend | Missing `stale_session_recovery` APScheduler job | Fixed: new `stale_session_recovery.py` job sweeps every 15 min, closes unclosed `StopwatchSession` rows whose `start_time_utc < now - 24h` with `auto_closed=True`, sets `end_time = start + max(planned_duration, 1)` min, clears matching Redis `active_stopwatch`/`pause_state` keys, per-user iteration via `for_each_user`. Root cause of the 65h CO-block ghost. |
| LYR-GET | 🟡 medium | backend | Missing single task fetch endpoint | `GET /v1/tasks/{task_id}` implemented. Returns full TaskDetail. Router reordered to prevent `/query` collision. Enables Hard Rule #6 verification flow. |
| LYR-UNDO | 🟡 medium | backend | Missing undo endpoint | `POST /v1/undo` implemented. 30-second TTL via Redis. Reverts `create_task` (soft-delete) and `delete_task` (restore to PLANNED). Confirmed working via curl and Telegram. |
| LYR-SCHED | 🟡 medium | backend | Missing APScheduler background workers | `scheduler.py` + 4 jobs: reminders (1min), Notion retry (5min), timer overflow (2min), overdue (30min). Hooked into FastAPI lifespan. Confirmed firing via logs. |
| LYR-NOTIF | 🟡 medium | backend | No notification delivery to Telegram | Polling system implemented. Backend pushes to `POST /v1/notifications/push`. OpenClaw polls `GET /v1/notifications/pending` every 30s. Verified queue push/pop working. |
| LYR-RULE6 | 🟡 medium | skill | No backend verification before mutations | Hard Rule #6 added to SKILL.md: always call query + single fetch before any timer start, delete, or reschedule. |
| LYR-DISC | 🟡 medium | backend | No cognitive measurement data captured | Discrepancy measurement layer implemented: `pre_task_readiness`, `post_task_reflection`, `initiation_status`, `initiation_delay_minutes` on Task model. `discrepancy_score` property. Abandoned task detection job (30 min). `GET /v1/analytics/discrepancy` endpoint. Readiness/reflection capture workflow added to SKILL.md. Migration 002 applied. |

---

## Priority Order for Next Session

### Critical (🔴)
1. LYR-080 — Backend rebuild during active paused session corrupts task/session linkage; delta not computed

### Medium (🟡)
3. LYR-096 — `task_completion_percentage` dropped in frontend stop flow
4. LYR-097 — `is_future_task` warning not shown in UI
5. LYR-088 — resume() loses Redis session reference after another stopwatch runs in between
6. LYR-068 — Notion date timezone double conversion
8. LYR-050 — backfill initiation_status on historical tasks

### Low (🟢)
11. LYR-099 — New task modal start time stale after idle
12. LYR-060 — overflow notification misses short tasks
13. LYR-054 — category_mapping inference at creation time
14. LYR-018 + LYR-020 — backfill sync, clean test data
15. LYR-047 — document as Notion limitation
16. LYR-091 — resolve_user_from_token Phase 9 fix

---

## Deferred — OpenClaw interface (operator-only)

OpenClaw remains the operator's primary interface via Telegram. These bugs affect agent behavior (model compliance with SKILL.md, exec-approval enforcement, model-specific quirks) but do not block web UI alpha users. They retain their original IDs and will be addressed when OpenClaw integration is the active workstream.

| ID | Priority | Tag | Title | Notes |
|----|----------|-----|-------|-------|
| LYR-007 | 🟡 medium | openclaw | OpenClaw memory vs actual state | Hard constraint in SKILL.md not fully validated. If task deleted via Swagger, OpenClaw may still believe it exists. |
| LYR-019 | 🟡 medium | skill | Day-of-week label mismatch | Lyra labeled Friday Mar 27 as "Thursday Mar 27". Day label wrong in weekly view. |
| LYR-035 | 🟡 medium | skill | Task ID retrieved from memory not backend | On delete/start, Lyra uses conversation memory for task ID instead of querying backend. Hard Rule #6 added but not fully validated. |
| LYR-037 | 🟡 medium | skill | False conflict between tasks on different days | Hallucinated conflict between Monday and Tuesday tasks. Likely ghost records from bad-UTC era. Retest on clean database. |
| LYR-043 | 🔴 high | skill | Duplicate task created instead of using existing | When starting timer, Lyra creates new task from memory instead of querying backend for existing PLANNED task. Hard Rule #6 should fix — not yet fully validated. |
| LYR-045 | 🟡 medium | notion | Duplicate EXECUTING tasks in Notion | Ghost tasks from memory leaked into Notion. Downstream of LYR-043. |
| LYR-048 | 🔴 high | skill | Early-stop gate bypassed — model calls `?confirmed=true` directly | GLM skips `/stop` entirely and calls `/stop?confirmed=true` without user input. Confirmed via logs. Hard Rule #5 strengthened but not yet re-validated. |
| LYR-049 | 🔴 high | skill | Reschedule used as proxy for stopwatch/start on model switch | Sonnet without SKILL.md context improvises wrong endpoints — uses `/v1/reschedule` instead of `/v1/stopwatch/start`. Happens when model switches mid-session and new model has no skill context. Root cause same as LYR-051. |
| LYR-051 | 🔴 high | openclaw | Tasks confirmed to user but never POSTed to backend | Lyra says "scheduled" without a `task_id`. Hard Rule #7 added. Root cause: model loses SKILL.md context on rate-limit fallback and improvises confirmation without calling the API. Needs validation after rate-limit recovery. |
| LYR-052 | 🟡 medium | openclaw | Reminder cron fires during active session → `LiveSessionModelSwitchError` | Isolated cron session clashes with live session's model state; delivery silently dropped. Partially addressed by backend-direct Telegram delivery (no longer OpenClaw-dependent). Needs validation that direct path fires reliably. |
| LYR-053 | 🟡 medium | openclaw | Exec approval not enabled on Telegram — blocks autonomous skill execution | Every HTTP tool call requires Web UI approval rather than auto-approving on Telegram. Must enable exec approvals for Telegram channel in `openclaw.json` `gateway.nodes` or exec-approvals config. |
| LYR-057 | 🔴 high | skill | Stopwatch called with `title` instead of `task_id` → 404 | Model calls `/v1/stopwatch/start` with `{"title": "..."}` instead of querying first for `task_id`. Returns 404, timer never starts. Hard Rule #8 added to SKILL.md. Needs validation. |
| LYR-059 | 🟡 medium | openclaw | Haiku 4.5 uses curl shell commands instead of HTTP tool | Triggers exec approval on every backend call. SKILL.md rule updated to allow curl as fallback. |
| LYR-062 | 🟡 medium | openclaw | Lyra approves its own exec requests | `/approve` sent by agent not user — approval loop bypasses security intent. |
| LYR-063 | 🔴 high | openclaw | auth-profiles.json caches billing failure from old API key | New key never picked up without manual edit of `~/.openclaw/agents/main/agent/auth-profiles.json`. OpenClaw doesn't re-read env vars into cached credential store. |
| LYR-064 | 🟡 medium | docker | ANTHROPIC_API_KEY not passed to OpenClaw Docker container | Requires manual `docker-compose.yml` env entry. Key in `.env` but not mapped in compose environment block. |
| LYR-065 | 🟡 medium | openclaw | Qwen3.5:9b assumes readiness 5/5 without asking | Hard Rules ignored by local model. Readiness/reflection capture skipped entirely. |
| LYR-066 | 🔴 high | openclaw | Qwen3.5:9b deletes tasks without user confirmation to resolve conflicts | Violates Hard Rule #1 and #2. Local model doesn't follow SKILL.md constraints. |
| LYR-067 | 🟡 medium | openclaw | Qwen3.5:9b gets stuck replaying cached response in loop under GPU load | Model repeats same output indefinitely when Ollama is under memory pressure. |
| LYR-069 | 🟢 low | openclaw | Claude 3 Haiku too old to load skill system | Ignores SKILL.md entirely, uses built-in cron instead of Lyra endpoints. |
| LYR-071 | 🔴 high | openclaw | Approval requests still firing despite exec-approvals fix | `ask:"never"` + wildcard `"*"` not fully suppressing prompts. Haiku still triggers approval on every curl call. |
| LYR-072 | 🟡 medium | skill | Must delete conflicting task to schedule replacement | No "replace" or "skip and reschedule" flow. User said "skip CO review and schedule debugging" which required a delete + create. Should be atomic. |
| LYR-077 | 🟢 low | skill | Readiness assumed 5 without asking | Debugging session started with `pre_task_readiness:5` without Lyra asking the question first. Hard Rule violation again. |
| LYR-078 | 🔴 high | openclaw | Agent autonomously executed Lyra build during testing | Claude Code agent started and stopped the Lyra build task during testing — zero-duration session, bypassed early-stop gate with `?confirmed=true`, pre/post self-filled. Session voided via `POST /v1/tasks/{id}/void`. |
| LYR-081 | 🔴 high | skill | Agent auto-forces conflict override without asking user | Hard Rule #1 violation. During batch scheduling, agent resolved conflict silently instead of showing conflict list and waiting for explicit yes/no. |
| LYR-082 | 🟡 medium | skill | Agent uses planned_duration to compute end_time when explicit end_time provided | "Debugging from 2:37pm to 4pm, planned 54 mins" → end_time computed as 15:31 (2:37 + 54min) instead of 16:00. `planned_duration_minutes` should only affect delta, never override explicit end_time. |
