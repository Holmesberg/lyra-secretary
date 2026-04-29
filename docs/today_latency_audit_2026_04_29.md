# /today Latency Audit — 2026-04-29

**Trigger:** operator reported slow load on /today even with warm cache.
**Method:** two parallel Explore-agent passes (frontend network sequence + backend hot-path query cost) plus an attempted live curl probe (interrupted by the LYR-113 OAuth incident — full numbers TBD).
**Status:** diagnosis complete, fixes not yet applied. Recommendations queued for the post-launch perf sprint.

---

## Frontend network sequence (Explore-agent finding)

On every navigation to /today, the browser fires this exact set of requests:

| # | Endpoint | React Query Key | Where | Enabled | StaleTime | Refetch on focus | Polling |
|---|---|---|---|---|---|---|---|
| 1 | `/v1/users/me` | `["me"]` | `layout.tsx:88` | after session auth | 5min | false | none |
| 2 | `/v1/tasks/query?date=...` | `["tasks", viewedDate]` | `today/page.tsx:116` | always | **0** (default) | default | none |
| 3 | `/v1/stopwatch/status` | `["stopwatch-status"]` | `today/page.tsx:120` | always | **0** (default) | default | none (but see #6/#7) |
| 4 | `/v1/calendar/events?date_from=...&date_to=...` | `["calendar-events-today", viewedDate]` | `today/page.tsx:135` | always | 60s | default | every 60s |
| 5 | `/v1/deadlines` | `["deadlines"]` | `today/page.tsx:154` | always | 60s | default | none |
| 6 | `/v1/notifications/pending` | `["notifications-pending"]` | `today/page.tsx:162` | always | **0** | default | every 30s |
| 7 | `/v1/pause_predictions/pending-confirmation` | `["pause-predictions-pending-confirmation"]` | `today/page.tsx:172` | always | **0** | default | every 120s |

**Execution order:** layout's `/me` fires first (shared cache, 5-min stale), then all six today-page queries fire **in parallel** — no chaining. On warm cache, /me is reused instantly.

**Hot zone:** queries 2, 3, 6 have `staleTime: 0` (default). They re-fetch on every mount / window focus event regardless of whether the data could be stale yet. On a Cairo→eu-west-1 round-trip stack with Cloudflare Tunnel, that's 3 unnecessary roundtrips per page entry.

---

## Backend hot-path audit (Explore-agent finding)

Top 3 offenders ranked by impact on the warm path:

### 1. `GET /v1/users/me` — 5 DB queries, no composite indexes

The endpoint runs:
- `User` row fetch
- `ArchetypeAssignment` order-by-desc-limit-1 — no `(user_id, assigned_at DESC)` index
- `Task COUNT WHERE state=EXECUTED AND voided_at IS NULL` (executed_session_count)
- `Task COUNT WHERE voided_at IS NULL AND state NOT IN (SKIPPED, DELETED)` (active_task_count — the new field added in commit `67fa1fd` for the re-onboarding gate)
- `User.update(d1_return_at)` if grandfather backfill triggers

The two COUNTs hit the same `task` table without a composite `(user_id, state, voided_at)` index. On Supabase's task table they likely do an **index-only scan against the user_id index plus an in-memory filter** — fine for current n (≤200 tasks per user) but will degrade as users accumulate history.

**Recommendation:** add `idx_task_user_state_voided(user_id, state, voided_at)`. Even at current scale this would shave the worst-case cold-pool latency by avoiding two separate index-then-filter passes.

### 2. `GET /v1/calendar/events` — synchronous Google Calendar API call

The endpoint comment line 59 explicitly states the intention to cache events in Redis for 60s, **but the implementation never reads from Redis before calling Google**. Every request triggers a fresh `fetch_google_events()` round-trip which adds 1-3s of unpredictable latency (Google's edge varies).

**Recommendation:** wire the Redis cache that the docstring promises. Read-through pattern: check Redis with TTL=60s, miss → fetch Google → write back. This single fix would drop the warm-load cost of /today by 1-3 seconds for users with calendar connected.

### 3. `GET /v1/stopwatch/status` — cold-path joins without composite index

Hot path is Redis-cached (1 lookup). Cold path (recovery, when Redis is flushed or the active session was created in another process) does a `Task ⊲⊳ StopwatchSession` join filtered by state, but `idx_stopwatch_task(task_id)` is the only index that helps. No `(user_id, state)` composite. Masked by Redis caching today, fragile if Redis is wiped.

**Recommendation:** add `idx_stopwatch_user_state(user_id, state, end_time_utc)` — defense in depth.

---

## User-scoping middleware interaction with indexes

`backend/app/db/scoping.py` runs a `before_compile` hook that auto-appends `WHERE entity.user_id = :uid` to every user-scoped query. The hook itself is sound.

**Risk:** if existing indexes don't lead with `user_id`, the appended filter applies *after* a wider scan. Many of the prod indexes were created before scoping existed and never reordered. The right discipline going forward: **every new index on a user-scoped table must have `user_id` as the leading column.**

The `deadline` table already has `idx_deadline_user_state(user_id, state, voided_at)` — that's the template every other user-scoped table should match.

---

## Cloudflare Tunnel + Supabase RTT — pure overhead

Two costs that don't warm up no matter what:

| Hop | Per-request cost (Cairo) | Notes |
|---|---|---|
| Browser → Cloudflare edge → operator's WSL2 laptop | ~50-100ms | Tunnel is single-process; can't be optimized at the app layer |
| Backend → Supabase pooler eu-west-1 (port 6543) | ~80-120ms | Per-query. A 5-query endpoint pays this 5× |

A /today render with the current 6-parallel-fetch pattern, assuming each endpoint averages 2 DB queries, costs:
```
1 tunnel × 6 parallel + (max DB queries per endpoint) × 100ms RTT
≈ 100ms + 200ms = 300ms warm baseline
```

Plus the GCal sync at 1-3s (offender #2) → realistic warm-load is **1-3 seconds** today, dominated by GCal.

---

## Recommended fix order

1. **Wire the GCal Redis cache** — single biggest win, ~1-3s shaved from every warm /today.
2. **Add `idx_task_user_state_voided` composite** — Supabase migration, fixes /me's two COUNTs.
3. **Bump `staleTime` on queries 2/3/6** to a small value like 5-10s — kills duplicate fetches when the user navigates away and back quickly. Stopwatch status arguably needs to stay 0 (it's used for the timer banner; staleness here visibly desyncs the UI), but tasks-query and notifications-pending could safely be 5s.
4. **Audit other user-scoped tables** for `(user_id, ...)`-leading indexes; add where missing.
5. **(Out of scope for app-layer)** Cloudflare Tunnel hop is the floor — only fix is moving the host out of the operator's laptop. Per existing `strategic_decisions_april_24.md`, that decision is gated on Stage-2 retention.

---

## Memorialize this audit's lessons

- Every new endpoint added to /today's render path costs the user a tunnel-RTT × N pattern. **Default to staleTime > 0 unless there's a freshness reason.**
- Background jobs sharing the connection pool (12 APScheduler jobs running, including the every-5-second magic LLM parser) compete with user-request DB connections during high-frequency periods. Long-term: split read/write pools, or push background jobs to a separate worker process. Not urgent at current scale but document the failure mode.
- The `before_compile` user-scoping hook is invisible to anyone reading SQL — onboarding new contributors needs to surface this in `architecture.md` or a contributing guide so they don't think the queries are unscoped.
