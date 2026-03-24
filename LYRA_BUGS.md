# Lyra Secretary — Bug Tracker

Last updated: March 24, 2026 — stress test batches 1-10 complete

---

## Open

| ID | Priority | Tag | Title | Notes |
|----|----------|-----|-------|-------|
| LYR-003 | 🟡 medium | backend | Stopwatch path inconsistency | Endpoints at `/v1/start` and `/v1/stop` should be `/v1/stopwatch/start` and `/v1/stopwatch/stop`. Will cause path collisions later. Fix before OpenClaw tool schema is finalised. |
| LYR-007 | 🟡 medium | openclaw | OpenClaw memory vs actual state | If task deleted via Swagger, OpenClaw still believes it exists. Hard constraint added to SKILL.md but not fully validated yet. |
| LYR-010 | 🟢 low | docker | SKILL.md not auto-synced | Antigravity edits project SKILL.md but OpenClaw reads from inside container. Requires manual `docker cp` after every edit. Fix: volume mount the skills directory. |
| LYR-011 | 🟡 medium | skill | Timezone extraction ambiguity | OpenClaw runs UTC. "9am" without Cairo context may produce wrong UTC offset. SKILL.md rule added but not stress tested yet. |
| LYR-013 | ✅ resolved | skill | Query endpoint not called — memory used instead | Hard constraint added to SKILL.md. Batch 3 confirmed: Lyra now calls `/v1/tasks/query` correctly. Retested and passing. |
| LYR-015 | 🟡 medium | notion | No backfill for pre-fix tasks | Tasks created before Notion sync fix exist in SQLite but not in Notion. No manual sync endpoint exists. Need `POST /v1/tasks/{task_id}/sync`. |
| LYR-017 | 🟡 medium | backend | Meeting created in the past | "meeting in 2 hours" created at 4:26 PM which was already past by processing time. LYR-001 now resolved — past-time validation added. |
| LYR-018 | 🟢 low | notion | Orphaned SQLite records showing in conflict messages | CSE221 conflict referenced "CO Exam Prep" which exists in SQLite but not in Notion. Pre-fix orphan. Same class as LYR-015. |
| LYR-019 | 🟡 medium | skill | "Thursday" mapped to wrong date | Lyra put CO Exam Prep on Friday Mar 27 in weekly view but called it "Thursday Mar 27". Mar 27 is actually Friday. Day-of-week label mismatch. |
| LYR-020 | 🟢 low | notion | Test tasks polluting real schedule | Notion Test, Notion Test Final, Notion Live Test from smoke testing are visible in the weekly view. Need a way to delete or archive test data. |
| LYR-021 | 🟡 medium | skill | Timer started for future task without warning | Gym is scheduled tomorrow at 7am. Lyra started the timer at 4:33pm today with no warning. Should check if task start time is current before starting stopwatch. |
| LYR-024 | 🟡 medium | backend | No confirmation when timer stopped early | Timer stopped at 1 min out of 90 planned. System silently accepted. Should prompt if stopped before 50% of planned duration: "Did you complete this task or are you pausing?" |
| LYR-027 | 🟡 medium | skill | Gym shown as EXECUTED in query but EXECUTING in Notion | OpenClaw reported Gym as "Executed" in free-time query but Notion shows EXECUTING. State read from SQLite disagrees with Notion. Fixed by P2 — state now syncs to Notion on every mutation. |
| LYR-031 | 🟡 medium | backend | 0-minute duration reported, no early-stop confirmation | Timer stopped in under 1 minute. Reported "0 minutes" and "60 minutes under" with no confirmation prompt. LYR-024 confirmed again — early stop needs a "completed or pausing?" prompt. |

---

## Fixed

| ID | Priority | Tag | Title | Fix |
|----|----------|-----|-------|-----|
| LYR-001 | 🔴 high | backend | Past time not rejected | `create_task()` now rejects start times >5min in the past with `{"error": "start_in_past"}` 400 response. |
| LYR-002 | 🔴 high | skill | OpenClaw reports wrong time to user | SKILL.md Hard Rule #4: "Always report times from the API response, never from your own extraction." |
| LYR-004 | 🔴 high | backend | Missing `GET /v1/tasks/query` | Implemented in `query.py`, registered in router, documented in SKILL.md. |
| LYR-005 | 🔴 high | notion | Notion sync silently failing | `try/except` was swallowing all errors. `notion_synced` bool now returned in create response. |
| LYR-006 | 🟡 medium | skill | Double parsing | SKILL.md updated — OpenClaw extracts fields itself, `/v1/parse` is fallback only. |
| LYR-008 | 🔴 high | docker | Docker network isolation | OpenClaw and backend on separate networks. Fixed via `docker network connect` + permanent `docker-compose.yml` networks config. |
| LYR-009 | 🟡 medium | backend | Telegram token in backend `.env` | Removed from FastAPI config entirely. Telegram belongs to OpenClaw only. |
| LYR-012 | 🟡 medium | backend | No duplicate request protection | Redis idempotency key added via `X-Idempotency-Key` header with 30s TTL. |
| LYR-014 | 🔴 high | skill | Wrong time reported on query | Same root cause as LYR-002. Fixed by SKILL.md Hard Rule #4: report API response values. |
| LYR-016 | 🔴 high | skill | Gym scheduled at 8am not 6am | Same root cause as LYR-002. Fixed by SKILL.md Hard Rule #4: report API response values. |
| LYR-022 | 🔴 high | backend | Task state stuck on EXECUTING after timer stopped | `sync_task()` already fires after `complete_task()` → EXECUTED. Root cause was `notion_page_id` not persisted to DB, so sync was creating new pages. Fixed by passing `db` session to `sync_task()`. |
| LYR-023 | 🔴 high | notion | Reschedule creates duplicate instead of updating | `sync_task()` now receives `db` session, commits `notion_page_id` after first create. Subsequent syncs use `pages.update()`. |
| LYR-025 | 🟡 medium | notion | Soft delete not reflected in Notion | `delete_task()` now calls `archive_page()` with error logging instead of silent `pass`. |
| LYR-026 | 🔴 high | backend | Delete endpoint broken — enum .value error | Safe `.value` access: `task.state.value if hasattr(task.state, 'value') else str(task.state)` in delete undo cache. |
| LYR-028 | 🟡 medium | skill | Bulk delete without confirmation | SKILL.md Hard Rule #2: "NEVER perform bulk destructive operations without confirmation." |
| LYR-029 | 🔴 high | skill | Batch create auto-forces conflicts without asking | SKILL.md Hard Rule #1: "NEVER auto-force a conflict." |
| LYR-030 | 🟡 medium | skill | Generic task names created without asking | SKILL.md Hard Rule #3: "NEVER create tasks with generic names." |
| LYR-032 | 🔴 high | notion | Bulk reschedule creates duplicate Notion entries | Same root cause as LYR-023. Fixed by persisting `notion_page_id` to DB after first Notion create. |
| LYR-033 | 🔴 high | notion | Gym state split between SQLite and Notion | `sync_task(task, db=self.db)` now called after every state mutation (start, complete, skip, delete, reschedule). |

---

## April 3rd Backlog

- Fix LYR-001: add past-time validation to `/v1/create`
- Fix LYR-002 + LYR-014 + LYR-016: SKILL.md — report `start` from API response, never from extracted value
- Fix LYR-003: rename stopwatch paths to `/v1/stopwatch/start` and `/v1/stopwatch/stop`
- Fix LYR-010: volume mount SKILL.md so edits auto-sync without `docker cp`
- Fix LYR-015 + LYR-018 + LYR-020: delete smoke test tasks, implement `/v1/tasks/{task_id}/sync` for Notion backfill
- Fix LYR-019: investigate day-of-week label in weekly query response
- Fix LYR-022: state machine — EXECUTING → EXECUTED transition on stopwatch stop
- Fix LYR-023: reschedule should update existing Notion page, not create new one
- Fix LYR-024: add early-stop confirmation prompt (<50% planned duration)
- Fix LYR-025: sync delete state to Notion
- Fix LYR-026: patch enum .value bug in delete endpoint (same fix as was applied to create)
- Fix LYR-023 + LYR-032: reschedule must update existing Notion page, not create new one
- Fix LYR-033: Notion state sync on stopwatch stop — push EXECUTED state to Notion
- Fix LYR-030: SKILL.md — ask for task names before batch creating generic tasks

## Batch Results (March 24)

**Batch 3** — Queries
- Tomorrow query: ✅ called backend correctly
- Free at 2pm check: ✅ correct
- Weekly view: ✅ all tasks returned
- LYR-013 confirmed resolved

**Batch 4** — Mutations
- Reschedule gym: ✅ rescheduled correctly
- Delete study session: ✅ deleted
- Updated weekly view: ✅ reflected changes
- New bug: LYR-023 (duplicate Notion entries), LYR-025 (delete not in Notion)

**Batch 10** — Reschedule edge cases
- Move executed gym: ✅ correctly blocked, immutability enforced
- Push everything back 1 hour: ✅ bulk reschedule worked but ❌ LYR-032 (duplicate Notion entries)
- Move executed CO notes: ✅ correctly blocked
- New bugs: LYR-032 (duplicate Notion on bulk reschedule), LYR-033 (SQLite/Notion state split)
- Duplicate gym: ✅ conflict detected, offered alternatives
- 5 back to back tasks: ✅ created but ❌ LYR-029 (auto-forced conflict), LYR-030 (generic names)

**Batch 8** — Ambiguous input
- All 5 vague inputs: ✅ rejected with specific feedback per item

**Batch 9** — Timer collisions
- Double timer: ✅ second timer blocked correctly
- Double stop: ✅ "no active stopwatch" handled gracefully
- Review CO notes now EXECUTED in Notion: ✅ LYR-022 may be partially fixed
- Early stop 0 minutes: ❌ LYR-031 confirmed
- "remind me to call mom": ✅ rejected, asked for time
- "block 2 hours for deep work": ✅ rejected, asked for time
- "free time tomorrow afternoon": ✅ queried backend correctly
- Recurring tasks: ✅ identified no batch endpoint, offered alternatives
- "cancel everything thursday": ❌ LYR-026 (delete broken), LYR-028 (no confirmation)
- Timer start: ✅ started (but no future-task warning — LYR-021)
- Elapsed query: ✅ returned correct elapsed time
- Timer stop + delta: ✅ delta computed correctly (1 min actual vs 90 planned)
- New bugs: LYR-022 (stuck EXECUTING), LYR-024 (no early-stop confirmation)
