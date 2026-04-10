# Phase 4 Prerequisites — Design Notes

*Status: design only. No code changes in this document.*
*Author: April 9, 2026.*

These are implementation designs that must be reviewed before Phase 4 coding begins. Each section is self-contained and can be implemented independently.

---

## 1. Schema refactor: `planned_end_utc` rename

### Current state

The `task` table stores planned time as `start` and `end` columns (both `DateTime`, UTC). The `end` column is ambiguous — it could mean "planned end" or "executed end" depending on context. The executed end is stored separately as `executed_end`.

### Proposed rename

| Current | Proposed | Reason |
|---|---|---|
| `task.start` | `task.planned_start_utc` | Explicit about what the timestamp represents and its timezone |
| `task.end` | `task.planned_end_utc` | Disambiguates from `executed_end`; mirrors `planned_start_utc` |

### Migration plan

1. Add new columns `planned_start_utc` and `planned_end_utc` (nullable).
2. Backfill: `UPDATE task SET planned_start_utc = start, planned_end_utc = "end"`.
3. Drop old columns `start` and `end`.
4. Update all references in:
   - `app/db/models.py` — column definitions
   - `app/services/task_manager.py` — all reads/writes
   - `app/services/conflict_detector.py` — interval overlap queries
   - `app/api/v1/endpoints/query.py` — response serialization
   - `app/api/v1/endpoints/analytics.py` — all analytics queries
   - `app/schemas/` — request/response models
   - `frontend/lib/tasks.ts` — `TaskRow.start` / `TaskRow.end` field names
   - `frontend/app/(app)/today/page.tsx` — `sortKey()` references `t.start`
5. The API response field names (`start`, `end`) can stay as-is for backwards compatibility with OpenClaw, or be renamed to `planned_start` / `planned_end` with a deprecation period.

### Risk

This is a high-touch refactor that touches every layer. Do it in a single PR with a comprehensive test run. Do NOT do it alongside any other schema change.

---

## 2. `useCurrentTime` hook — frontend time freshness

### Problem

The Today page uses `new Date()` at render time to compute the current date string and display formatting. This value is captured once and never refreshed. If the user leaves the tab open past midnight, the page still shows yesterday's tasks. The `date-fns` `format()` call in the header and the `todayLocal()` function both use a stale `new Date()`.

More subtly: the active timer banner shows elapsed time but relies on the `elapsed_minutes` field from the polling response, not on a local clock. This is correct (server is authoritative) but feels laggy because polling is every 10 seconds.

### Proposed hook

```typescript
// lib/hooks/use-current-time.ts
import { useState, useEffect } from "react";

/**
 * Returns a Date that updates every `intervalMs` milliseconds.
 * Components that depend on "now" use this instead of `new Date()`.
 */
export function useCurrentTime(intervalMs: number = 60_000): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}
```

### Usage sites

1. **`todayLocal()`** — replace `new Date()` with the hook's value. When the date rolls over at midnight, the query key changes automatically, triggering a fresh `queryTasks()` fetch.
2. **Header date display** — `format(now, "EEEE, MMMM d")` updates without a page refresh.
3. **Timer banner** — optionally use `useCurrentTime(1000)` for a 1-second local clock alongside the 10s polling, so the displayed elapsed time ticks smoothly between server updates.

### Why not just poll faster?

Faster polling (1s) would give fresh server data but wastes bandwidth and battery. The hook gives a fresh *display* clock locally and only fetches server data every 10s. The server remains authoritative for actual elapsed time; the local clock is a UX smoothing layer.

---

## 3. Stale session recovery job

### Problem

If the server crashes or Redis is flushed while a stopwatch is running, the Redis key disappears but the `stopwatch_session` row in SQLite still has `end_time IS NULL`. The task remains in EXECUTING state forever. Currently there is no recovery mechanism — the operator must manually stop the session via a direct DB update or API call.

### Proposed design

A new APScheduler job (`workers/stale_session_recovery.py`) that runs every 5 minutes:

```
stale_session_recovery():
    # Find sessions that have been running for longer than their planned
    # duration + a grace buffer, with no corresponding Redis active key.
    
    cutoff = now_utc() - timedelta(hours=4)  # absolute maximum session length
    
    stale_sessions = db.query(StopwatchSession).filter(
        StopwatchSession.end_time.is_(None),
        StopwatchSession.start_time < cutoff,
    ).all()
    
    for session in stale_sessions:
        # Check if Redis still has an active key for this user
        user_key = f"stopwatch:active:{session.task.user_id}"
        if redis.exists(user_key):
            continue  # session is legitimately running, just long
        
        # No Redis key → session is orphaned. Auto-close it.
        session.end_time = session.start_time + timedelta(hours=4)  # cap at cutoff
        session.auto_recovered = True  # new boolean column
        
        task = session.task
        task.state = TaskState.EXECUTED
        task.executed_end = session.end_time
        task.executed_duration_minutes = (session.end_time - session.start_time).total_seconds() / 60
        task.duration_delta_minutes = (task.planned_duration_minutes or 0) - task.executed_duration_minutes
        
        # Do NOT set post_task_reflection — it wasn't captured
        
        db.commit()
        log.warning(f"Auto-recovered stale session {session.id} for task {task.task_id}")
```

### Schema addition

| Table | Field | Type | Notes |
|---|---|---|---|
| `stopwatch_session` | `auto_recovered` | `Boolean` | Default `False`. Set `True` by the recovery job. |

### Design decisions

- **4-hour cutoff** is generous. No legitimate session should run 4 hours without a pause or stop. This is a safety net, not a feature.
- **Do not set `post_task_reflection`** — the user wasn't present to rate their focus. Analytics queries already handle `NULL` reflection gracefully.
- **Log a warning** so the operator can see recovery events. Optionally push a notification via the OpenClaw gateway.
- **Do not auto-close sessions that have an active Redis key** — this prevents the job from fighting with a legitimately long session.
- **Run every 5 minutes** — matches the existing Notion sync retry cadence. Not time-critical.

### Edge cases

1. **Redis flushes mid-session but server doesn't crash:** The recovery job will catch this at the next 5-min tick. The user may have already noticed the timer disappeared from the UI (polling shows `active: false`). The auto-recovery closes the DB-side cleanly.
2. **Server crashes and restarts within 5 minutes:** The existing rehydration logic (reading `stopwatch_session` rows with `end_time IS NULL` on startup) should handle this. The recovery job is a backup for cases where rehydration also fails or the session is genuinely abandoned.
3. **Multiple stale sessions for the same user:** Process all of them. Each gets its own recovery entry.

---

## Implementation order (recommended)

1. `useCurrentTime` hook — smallest scope, no backend changes, immediate UX improvement.
2. Stale session recovery job — independent backend change, no schema dependencies on other work.
3. Schema refactor (`planned_end_utc`) — largest scope, do last and in isolation.

All three are independent of the Phase 4 analytics features (bias-factor v2, cascade scoring, archetype clustering). They can be implemented in Phase 4 Sprint 0 (infrastructure sprint) before the analytics work begins.
