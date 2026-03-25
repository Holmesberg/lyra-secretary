# Lyra Secretary — Bug Tracker

Last updated: March 25, 2026 — post stress test cleanup

---

## Open (11 bugs)

| ID | Priority | Tag | Title | Notes |
|----|----------|-----|-------|-------|
| LYR-003 | 🟡 medium | backend | Stopwatch path inconsistency | Endpoints at `/v1/start` and `/v1/stop` should be `/v1/stopwatch/start` and `/v1/stopwatch/stop`. Will cause path collisions later. |
| LYR-007 | 🟡 medium | openclaw | OpenClaw memory vs actual state | Hard constraint added to SKILL.md but not fully validated. If task deleted via Swagger, OpenClaw may still believe it exists. |
| LYR-015 | 🟡 medium | notion | No backfill for pre-fix tasks | Tasks created before Notion sync fix exist in SQLite but not in Notion. Need `POST /v1/tasks/{task_id}/sync`. |
| LYR-018 | 🟢 low | notion | Orphaned SQLite records in conflict messages | Old tasks in SQLite but not in Notion appear in conflict detection. Same class as LYR-015. |
| LYR-019 | 🟡 medium | skill | Day-of-week label mismatch | Lyra labeled Friday Mar 27 as "Thursday Mar 27". Day label wrong in weekly view. |
| LYR-020 | 🟢 low | notion | Test tasks polluting schedule | Smoke test tasks still visible in Notion. Need cleanup. |
| LYR-021 | 🟡 medium | skill | Timer started for future task without warning | Lyra starts stopwatch for tomorrow's task with no warning. Should warn if task start time hasn't arrived. |
| LYR-024 | 🟡 medium | backend | No early-stop confirmation | Timer stopped at 1 min of 90 planned — silently accepted. Should prompt "completed or pausing?" if stopped before 50% of planned. |
| LYR-035 | 🟡 medium | skill | Task ID retrieved from memory not backend | On delete, Lyra used conversation memory for task ID. Violates hard constraint. |
| LYR-036 | 🟡 medium | skill | Context lost on follow-up corrections | Short follow-ups like "next week" treated as new standalone request instead of continuing previous intent. |
| LYR-037 | 🟡 medium | skill | False conflict between tasks on different days | Hallucinated conflict between Monday and Tuesday tasks. Likely ghost records from bad-UTC era. Retest on clean database. |

---

## Fixed (24 bugs)

| ID | Priority | Tag | Title | Fix |
|----|----------|-----|-------|-----|
| LYR-001 | 🔴 high | backend | Past time not rejected | `create_task()` rejects start >5min in past. Confirmed working. |
| LYR-002 | 🔴 high | skill | OpenClaw reports wrong time to user | SKILL.md Hard Rule #4: report `start` from API response, never own extraction. |
| LYR-004 | 🔴 high | backend | Missing `GET /v1/tasks/query` | Implemented in `query.py`, registered in router, in SKILL.md. |
| LYR-005 | 🔴 high | notion | Notion sync silently failing | `notion_synced` bool now returned. Silent swallowing removed. |
| LYR-006 | 🟡 medium | skill | Double parsing | OpenClaw extracts fields itself, `/v1/parse` is fallback only. |
| LYR-008 | 🔴 high | docker | Docker network isolation | Permanent `docker-compose.yml` networks config. OpenClaw joins backend network. |
| LYR-009 | 🟡 medium | backend | Telegram token in backend `.env` | Removed. Telegram belongs to OpenClaw only. |
| LYR-010 | 🟢 low | docker | SKILL.md not auto-synced | Moved to volume-mounted `/mnt/c/Users/alina/openclaw/skills/lyra-secretary/`. Auto-syncs on restart. |
| LYR-011 | 🔴 high | backend | Timezone pipeline broken — ROOT CAUSE | OpenClaw sends UTC, stored as-is, notion_client converts UTC→Cairo with `+02:00`. Notion displays correct Cairo time. |
| LYR-012 | 🟡 medium | backend | No duplicate request protection | Redis idempotency via `X-Idempotency-Key`, 30s TTL. |
| LYR-013 | 🔴 high | skill | Query endpoint not called — memory used | Hard constraint in SKILL.md. Confirmed working batch 3. |
| LYR-014 | 🔴 high | skill | Wrong time reported on query | Fixed by SKILL.md Hard Rule #4. |
| LYR-016 | 🔴 high | skill | Wrong time reported on create | Fixed by SKILL.md Hard Rule #4. |
| LYR-017 | 🟡 medium | backend | Meeting created in the past | Fixed by LYR-001 past-time validation. |
| LYR-022 | 🔴 high | backend | Task stuck on EXECUTING after timer stop | `sync_task(db)` called after every state mutation. |
| LYR-023 | 🔴 high | notion | Reschedule creates duplicate Notion pages | `notion_page_id` persisted to DB. Future syncs call `pages.update()`. |
| LYR-025 | 🟡 medium | notion | Soft delete not in Notion | `delete_task()` calls `archive_page()` with error logging. |
| LYR-026 | 🔴 high | backend | Delete endpoint enum .value error | `hasattr(x, 'value')` guard applied. Confirmed working. |
| LYR-027 | 🟡 medium | skill | State disagreement SQLite vs Notion | Fixed by LYR-022 — state syncs to Notion on every mutation. |
| LYR-028 | 🟡 medium | skill | Bulk delete without confirmation | SKILL.md Hard Rule #2: list tasks and confirm before bulk delete. |
| LYR-029 | 🔴 high | skill | Batch create auto-forces conflicts | SKILL.md Hard Rule #1: never auto-force, always ask user. |
| LYR-030 | 🟡 medium | skill | Generic task names created | SKILL.md Hard Rule #3: never use generic names like "Task 1". |
| LYR-032 | 🔴 high | notion | Bulk reschedule creates duplicates | Fixed by LYR-023 — `notion_page_id` persisted. |
| LYR-033 | 🔴 high | notion | State split SQLite vs Notion | Fixed by LYR-022. |

---

## April 3rd Backlog (priority order)

1. LYR-037 — retest false conflict on clean database
2. LYR-003 — rename stopwatch paths
3. LYR-024 — early-stop confirmation prompt
4. LYR-021 — warn before starting timer for future task
5. LYR-015 + LYR-018 + LYR-020 — backfill sync endpoint, clean test data
6. LYR-035 — always query backend for task ID
7. LYR-036 — carry context on follow-up corrections
8. LYR-019 — day-of-week label fix
9. LYR-007 — validate memory constraint fully working