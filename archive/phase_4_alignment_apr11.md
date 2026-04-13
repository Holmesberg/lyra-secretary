# Phase 4 Alignment Verification — April 11, 2026

Pre-implementation audit. Backend is source of truth. Frontend must honor it.

---

## 1. State Machine Coverage

### A. PLANNED → EXECUTING (start)

| Layer | Location | Status |
|-------|----------|--------|
| Frontend trigger | `task-row.tsx:106-114` — Play button on PLANNED rows → opens ReadinessModal | ✅ |
| Frontend trigger | `today/page.tsx:95-103` — `handleStart(task, readiness)` calls `startStopwatch(task_id, readiness)` | ✅ |
| Backend handler | `stopwatch.py:39-68` → `StopwatchManager.start()` → `TaskManager.start_task()` | ✅ |
| Readiness modal | `readiness-modal.tsx` — anchored 1–5 scale, blocks submit until selected | ✅ |
| Future task warning | Backend returns `is_future_task: true` if planned_start > now + 5min | ⚠️ Frontend ignores `is_future_task` — no warning shown |
| Conflict on start | Backend raises `StopwatchAlreadyRunningError` if timer active and not paused | ✅ Frontend disables Play when `timerBusy` |
| State machine error | Backend raises `InvalidStateTransitionError` for non-PLANNED tasks | ⚠️ Frontend shows raw error string (see §3) |

### B. EXECUTING → PAUSED (pause)

| Layer | Location | Status |
|-------|----------|--------|
| Frontend trigger | `active-timer-banner.tsx:47-69` — toggle() calls `pauseStopwatch()` | ✅ |
| Backend handler | `stopwatch.py:71-106` → `StopwatchManager.pause()` | ✅ |
| Optimistic update | Banner flips `paused` immediately, rolls back on error | ✅ |
| Banner color | Green (active) → Amber (paused), with "· paused" suffix | ✅ |
| Float paused_minutes | `total_paused_minutes` is Float in schema (`StopwatchResumeResponse`) | ✅ |
| Pause reason | Backend accepts `pause_reason` + `pause_initiator` | ⚠️ Frontend hardcodes `pause_reason: undefined` — no picker |

### C. PAUSED → EXECUTING (resume)

| Layer | Location | Status |
|-------|----------|--------|
| Frontend trigger | `active-timer-banner.tsx:57` — `resumeStopwatch()` | ✅ |
| Backend handler | `stopwatch.py:109-124` → `StopwatchManager.resume()` | ✅ |
| Optimistic update | Banner flips `paused` back, rolls back on error | ✅ |
| Float return | `paused_minutes: float, total_paused_minutes: float` in response | ✅ |
| Error handling | Catches error, shows in banner | ✅ |

### D. EXECUTING → EXECUTED (stop)

| Layer | Location | Status |
|-------|----------|--------|
| Frontend trigger | `task-row.tsx:126-128` — Square button on EXECUTING/PAUSED → opens ReflectionModal | ✅ |
| Frontend trigger | `today/page.tsx:106-131` — `handleStop(reflection, {confirmed})` | ✅ |
| Backend handler | `stopwatch.py:127-188` → early-stop check → `StopwatchManager.stop()` | ✅ |
| Early-stop gate | Backend returns `requires_confirmation: true` if elapsed < 50% planned | ✅ |
| Frontend early-stop | `reflection-modal.tsx:57-62` — yellow warning box, button text changes to "Confirm early stop" | ✅ |
| Completion % input | `reflection-modal.tsx:83-100` — only shown during early stop, clamped 0–100 | ✅ |
| Completion % clamp | `reflection-modal.tsx:115-122` — frontend clamps; backend `StopwatchStopRequest` has `ge=0, le=100` | ✅ |
| Paused parent notice | `today/page.tsx:123-126` — shows info banner with paused parent details | ✅ |
| Micro-mirror | Backend returns `micro_mirror` string | ⚠️ Frontend ignores `micro_mirror` — not displayed |
| Calibration nudge | Backend returns `calibration_nudge` string | ⚠️ Frontend ignores `calibration_nudge` — not displayed |
| Completion % passthrough | `today/page.tsx:112` — `stopStopwatch(reflection, opts)` | ⚠️ `task_completion_percentage` never passed — `opts` only has `confirmed`, not `completionPct` |

### E. PLANNED → SKIPPED (manual skip)

| Layer | Location | Status |
|-------|----------|--------|
| Frontend trigger | `task-row.tsx:115-123` — Ban icon on PLANNED rows → `onSkip(task)` | ✅ |
| Frontend handler | `today/page.tsx:169-177` — `handleSkip()` calls `markAbandoned(task_id, reason)` | ✅ |
| Backend handler | `tasks.py:234-276` — `mark_abandoned` endpoint, PLANNED → SKIPPED with `initiation_status='user_skipped'` | ✅ |
| Missing: EXECUTING skip | Ban icon only on PLANNED rows (`task-row.tsx:104`) | ❌ No skip affordance on EXECUTING/PAUSED rows |

### F. PLANNED → SKIPPED (auto via overdue worker)

| Layer | Location | Status |
|-------|----------|--------|
| Backend worker | `overdue_tasks.py:16-47` — filters `planned_end_utc < now, state=PLANNED, initiation_status='not_started'` | ✅ |
| Frontend discovery | Tasks refetch every 10s (`providers.tsx:8`), SKIPPED rows appear with red pill | ✅ |
| Auto vs manual distinction | Both show as "SKIPPED" — no visual distinction | ⚠️ Acceptable for now |

### G. PLANNED → DELETED (soft delete)

| Layer | Location | Status |
|-------|----------|--------|
| Backend endpoint | `tasks.py:166-185` — `POST /v1/delete` accepts `task_id`, transitions PLANNED/SKIPPED → DELETED | ✅ |
| Frontend trigger | **NONE** | ❌ **P0: No delete affordance anywhere in the frontend** |
| Frontend lib function | **NONE** — no `deleteTask()` function in `lib/tasks.ts` | ❌ |

### H. Void (any non-DELETED → voided_at stamped)

| Layer | Location | Status |
|-------|----------|--------|
| Backend endpoint | `tasks.py:188-231` — `POST /v1/tasks/{id}/void`, any non-DELETED, requires `voided_reason` enum | ✅ |
| Frontend trigger | `task-row.tsx:130-139` — Trash2 icon on EXECUTED/SKIPPED only | ⚠️ Missing on PLANNED/EXECUTING/PAUSED |
| Frontend handler | `today/page.tsx:134-142` — `handleVoid()` hardcodes `"data_quality"` reason | ❌ **P0: No reason picker, hardcoded reason** |
| Void_reason_detail | Backend requires when `voided_reason='other'` | ❌ Frontend never sends it |

### I. Interruption flow (PAUSED parent + new child)

| Layer | Location | Status |
|-------|----------|--------|
| Backend conflict response | `tasks.py:76-95` — returns `ConflictInfo` list with `state` field per conflict | ✅ |
| Frontend detection | `new-task-modal.tsx:81` — `allPaused = res.conflicts.every((c) => c.state === "PAUSED")` | ✅ Logic correct |
| Frontend interruption UI | `new-task-modal.tsx:198-207` — yellow box with "Start as interruption?" | ✅ |
| Frontend force-create | `new-task-modal.tsx:109-135` — `submitAsInterruption()` sends `force: true` | ✅ |
| Auto-readiness-modal | `today/page.tsx:144-167` — `handleInterruptionCreated()` opens ReadinessModal for new task | ✅ |
| Backend parent linking | `stopwatch_manager.py:218-221` — sets `parent_task_id` when paused session exists | ✅ |
| **Operator-reported failure** | "Got generic conflict message instead of interruption offer" | 🔴 See §2 investigation |

---

## 2. Interruption Flow Investigation (Operator-reported #17 broken)

**Operator report:** Created task overlapping a PAUSED parent, got generic "Conflicts with: X. Adjust the time and try again." instead of the interruption offer.

**Code analysis:**

The frontend logic at `new-task-modal.tsx:81` is:
```js
const allPaused = res.conflicts.every((c) => c.state === "PAUSED");
```

This requires **every** conflicting task to be in PAUSED state. If even one conflict is PLANNED or EXECUTING, the interruption offer is suppressed and the generic error shows instead.

**Root cause candidates:**

1. **Mixed conflicts** — If the new task overlaps both the PAUSED task AND another PLANNED task in the same window, `allPaused` is false. This is the most likely scenario in dogfood.
2. **State serialization mismatch** — Backend `ConflictInfo.state` is `TaskState` (Pydantic enum). Serialized value should be `"PAUSED"` (str enum). Verified: `TaskState(str, Enum)` serializes to string value. Not the issue.
3. **Timing race** — The task might be EXECUTING at query time (pause not yet committed). Unlikely with 10s polling.

**Test #14 doesn't cover this:** Test `test_cross_user_interruption_blocked` tests cross-tenant isolation, not the same-user interruption flow. No test verifies: (a) the create endpoint returns PAUSED conflicts distinguishably, or (b) the frontend shows the interruption offer.

**Phase 4 fix needed:**
- Handle mixed conflicts: if ANY conflict is PAUSED, show the interruption offer for that task (not require ALL to be PAUSED)
- Add backend test: create task overlapping exactly one PAUSED task, verify conflict response includes `state: "PAUSED"`
- Add backend test: create task overlapping one PAUSED + one PLANNED, verify both appear in conflicts

---

## 3. Void / Delete / Skip Alignment

### Operator-clarified UX model

| Operation | Semantic meaning | Difficulty | Where |
|-----------|-----------------|------------|-------|
| **DELETE** | User cancelled a planned task = real behavioral signal | Easy | Trash icon on PLANNED rows |
| **SKIP / MARK-ABANDONED** | User gave up on a task (any active state) = real behavioral signal | Easy | Ban icon on PLANNED, EXECUTING, PAUSED rows |
| **VOID** | Research cleanup — destructive to dataset, for contamination only | Hard | Settings page, multi-select, reason picker |

### Current frontend state vs desired

| Desired | Current state | Gap |
|---------|--------------|-----|
| Trash icon on PLANNED → `POST /v1/delete` | No delete button anywhere | ❌ P0 |
| Ban icon on PLANNED → `POST /v1/tasks/{id}/mark-abandoned` | ✅ Exists (`task-row.tsx:115-123`) | ✅ |
| Ban icon on EXECUTING → `POST /v1/tasks/{id}/mark-abandoned` | Not shown (only PLANNED gets Ban) | ❌ P0 |
| Ban icon on PAUSED → `POST /v1/tasks/{id}/mark-abandoned` | Not shown | ❌ P0 |
| Trash icon on EXECUTED/SKIPPED → removed | Trash2 icon triggers void with hardcoded reason | ❌ P0 — remove |
| Settings page void flow | Does not exist | ❌ P1 (Phase 4) |

### Backend validation for mark-abandoned

Backend at `tasks.py:253` correctly accepts PLANNED, EXECUTING, and PAUSED:
```python
if task.state not in (TaskState.EXECUTING, TaskState.PAUSED, TaskState.PLANNED):
    raise HTTPException(status_code=400, ...)
```

For EXECUTING → SKIPPED: `initiation_status='abandoned'` (started but gave up). Elapsed time is preserved on the task row — this is behavioral data, not a wipe. Verified: `skip_task()` calls `state_machine.transition(task, SKIPPED)` which only changes state + notes, does NOT clear executed fields.

### Backend delete validation

`TaskManager.delete_task()` at `task_manager.py:420-459`:
- Rejects EXECUTED and DELETED explicitly
- State machine allows: PLANNED → DELETED, SKIPPED → DELETED
- EXECUTING/PAUSED → DELETED: passes the explicit check but state machine rejects (not in `TRANSITIONS[EXECUTING]` or `TRANSITIONS[PAUSED]`)
- Error path inconsistency: EXECUTED/DELETED raise `ImmutableTaskError`, but EXECUTING/PAUSED raise `InvalidStateTransitionError` — same result (400) but different error messages

---

## 4. Error Response Parsing Audit

### Global error handling

`lib/api.ts:21-30`:
```js
if (!res.ok) {
    const text = await res.text();
    let msg = `${res.status}: ${text}`;
    try {
        const body = JSON.parse(text);
        const detail = body?.detail;
        if (typeof detail === "string") msg = detail;
        else if (detail?.message) msg = detail.message;
    } catch {}
    throw new Error(msg);
}
```

This correctly handles:
- `detail: "string message"` → extracts string
- `detail: { message: "..." }` → extracts message
- `detail: { error: "code", message: "..." }` → extracts message ✅

**But does NOT handle:** `detail: { error: "start_in_past", message: "..." }` correctly returns the message. ✅

### Per-endpoint audit

| Endpoint | Frontend caller | Error handling | Status |
|----------|----------------|---------------|--------|
| `POST /v1/create` | `new-task-modal.tsx:102` | `catch (e: any) setError(e?.message)` | ✅ Friendly via api.ts |
| `POST /v1/stopwatch/start` | `today/page.tsx:101-103` | `catch (e: any) setErrorMsg(e?.message)` | ⚠️ Backend `stopwatch.py:65` wraps `StopwatchAlreadyRunningError` as plain string detail. State machine errors (`InvalidStateTransitionError`) bubble as 500 with raw traceback |
| `POST /v1/stopwatch/pause` | `active-timer-banner.tsx:62-66` | `catch setErr(e.message)` | ✅ |
| `POST /v1/stopwatch/resume` | `active-timer-banner.tsx:62-66` | Same handler | ✅ |
| `POST /v1/stopwatch/stop` | `today/page.tsx:129-131` | `catch setErrorMsg(e?.message)` | ✅ |
| `POST /v1/tasks/{id}/void` | `today/page.tsx:138-141` | `catch setErrorMsg(e?.message)` | ✅ |
| `POST /v1/delete` | **No frontend caller** | N/A | ❌ Missing |
| `POST /v1/reschedule` | **No frontend caller** | N/A | ❌ Missing |
| `POST /v1/tasks/{id}/mark-abandoned` | `today/page.tsx:173-176` | `catch setErrorMsg(e?.message)` | ✅ |

### Specific error: "Cannot transition from SKIPPED to EXECUTING"

Operator reported seeing this raw. Source: `state_machine.py:69` raises `InvalidStateTransitionError`. The stopwatch start endpoint at `stopwatch.py:67-68` catches `Exception` and wraps as `HTTPException(status_code=500, detail=str(e))`. The api.ts parser reads `detail` as a string → shows it directly.

**Fix:** The start endpoint should catch `InvalidStateTransitionError` specifically and return a 400 with a user-friendly message like "This task is already completed/skipped and cannot be started."

---

## 5. Tiniest Features Checklist

### 1. New task modal default time
- `new-task-modal.tsx:17-23` — `defaultStart()` computes next 5-min boundary from `new Date()`.
- Called on **initial render** via `useState(defaultStart())`. Does NOT recompute when modal re-opens.
- **FAIL:** If the page has been open for 30 minutes, the default start time is 30 minutes stale.
- Phase 4 fix: recompute `defaultStart()` in the modal's `onOpenChange` or use `useCurrentTime` hook.

### 2. Time format (12-hour)
- `task-row.tsx:69` — `format(new Date(...), "h:mm a")` ✅
- `today/page.tsx:185` — `format(new Date(), "EEEE, MMMM d")` — date header, no time. ✅
- `active-timer-banner.tsx:22` — elapsed timer uses `MM:SS` / `HH:MM:SS` format (not clock time). ✅
- **No 24-hour leftovers found.** ✅

### 3. Status pill colors
- `task-row.tsx:11-18` — all 6 states mapped:

| State | Style | Visual |
|-------|-------|--------|
| PLANNED | `bg-white/10 text-white/70` | Gray ✅ |
| EXECUTING | `bg-blue-500/20 text-blue-300` | Blue ✅ |
| PAUSED | `bg-yellow-500/20 text-yellow-300` | Amber ✅ |
| EXECUTED | `bg-green-500/20 text-green-300` | Green ✅ |
| SKIPPED | `bg-red-500/15 text-red-300` | Red ✅ |
| DELETED | `bg-white/[0.03] text-white/30` | Dimmed ✅ |

### 4. Sort order
- `today/page.tsx:71-93` — sorts by execution-time axis (desc by sort key):
  - EXECUTED → executed_end
  - SKIPPED → executed_end or planned_start
  - EXECUTING/PAUSED → executed_start or planned_start
  - PLANNED → planned_start
- Sort is **descending** (`sortKey(b) - sortKey(a)`) → most recent at top.
- **FAIL:** PLANNED tasks sort by planned_start descending, so latest-scheduled appears first. Expected: ascending (next-up task first).
- Voided tasks filtered out: `today/page.tsx:91` — `.filter((t) => !t.voided_at)` ✅
- DELETED tasks filtered by `queryTasks` in `lib/tasks.ts:50` ✅

### 5. Active timer banner during long pauses
- `active-timer-banner.tsx:33-37` — interval only runs when NOT paused. When paused, `setTick` stops but banner stays rendered.
- `active-timer-banner.tsx:39` — `if (!status.active || !status.start_time) return null;`
- **Operator bug report:** "Paused for 5h, banner disappeared, came back on stop attempt."
- **Root cause:** TanStack Query global `refetchInterval: 10_000` (10 seconds). The stopwatch status endpoint returns the session from Redis, which is populated by `_recover_from_db()`. If Redis loses the key during a long pause (Redis restart, TTL, memory eviction), the status endpoint returns `{ active: false }`, and the banner disappears. On stop attempt, `_recover_from_db()` restores from SQLite.
- **This is LYR-080 territory** — Redis key has no TTL for active sessions, but Redis restart during Docker rebuild (which the operator does frequently) would clear it.
- **Phase 4 fix:** The status endpoint already calls `_recover_from_db()` — but only inside `StopwatchManager.get_status()` via `_get_active()`. Checking: `get_status()` at `stopwatch_manager.py:547-577` calls `redis.get_active_stopwatch(user_id)` but does NOT fall through to `_recover_from_db()` if Redis returns None. It just returns None.
- **BUG CONFIRMED:** `get_status()` does NOT call `_recover_from_db()`. Only `_get_active()` does, but `get_status()` does not use `_get_active()` — it calls `redis.get_active_stopwatch()` directly.
- File as **LYR-095**.

### 6. Readiness/focus/delta display on rows
- `task-row.tsx:30-65` — `ResearchLayer` component:
  - SKIPPED: shows "—" ✅
  - PLANNED: returns null ✅
  - EXECUTING/PAUSED: shows "ready X →" ✅
  - EXECUTED: shows "X → Y ±Nmin" ✅
- Delta sign convention: `task-row.tsx:50-58`:
  - `delta > 0` → `−Nmin` (finished early = negative deviation from plan)
  - `delta < 0` → `+Nmin` (ran over = positive deviation)
  - **⚠️ Sign is inverted from user expectation.** `duration_delta_minutes = planned - executed`. Positive delta means finished early. But the display shows `−` for positive (early) and `+` for negative (over). This is counter-intuitive: "−20min" looks like the task was shorter, which is correct numerically but confusing UX. Acceptable for now — operator can decide.

### 7. Trash icon affordance
- Currently shown on: EXECUTED, SKIPPED only (`task-row.tsx:130-139`, `isTerminal = state === "EXECUTED" || state === "SKIPPED"`)
- Action triggered: `onVoid(task)` → `handleVoid()` → `voidTask(task_id, "data_quality")` — hardcoded reason, no modal
- **Per operator UX model:** Should be removed entirely from rows. Void moves to settings page.

### 8. Edit affordance on PLANNED tasks
- **Does not exist.** No click handler on rows, no edit modal, no reschedule UI.
- ❌ **P0 for Phase 4** — click PLANNED row → opens NewTaskModal prefilled → "Save" button instead of "Create"

### 9. Completion % input
- Frontend: `reflection-modal.tsx:86-99` — text input, onChange strips non-digits, clamps to 100. Only shown during early stop.
- Backend: `StopwatchStopRequest.task_completion_percentage` has `ge=0, le=100` ✅
- **BUG:** Frontend sends `completionPct` in the `onConfirm` callback (`reflection-modal.tsx:128`), but `today/page.tsx:112` only passes `{ confirmed: opts?.confirmed }` — **`completionPct` is dropped and never sent to backend.**
- File as **LYR-096**.

### 10. Conflict response handling
- Generic conflict (PLANNED/EXECUTING overlap): `new-task-modal.tsx:89-93` — red error with task titles ✅
- PAUSED parent conflict: `new-task-modal.tsx:81-87` — yellow interruption offer with "Start as interruption" button ✅
- Two shapes correctly distinguished ✅ (when `allPaused` is actually true — see §2 for edge case)

### 11. Past-task creation
- Backend: `task_manager.py:159-161` — raises `ValueError("start_in_past: ...")` 
- Endpoint: `tasks.py:114-118` — catches and returns `detail: { error: "start_in_past", message: "Task start time is in the past. Did you mean tomorrow?" }`
- Frontend: `api.ts:27` — extracts `detail.message` ✅
- Friendly message shown ✅

### 12. Cross-day rendering
- `today/page.tsx:23-27` — `todayLocal()` computed once on render: `const date = todayLocal();`
- This is inside the component body, so it recomputes on each re-render. But TanStack Query's `queryKey: ["tasks", date]` means the date is baked into the query key.
- **FAIL:** After midnight, the page continues showing yesterday's date until a full page refresh or navigation. The `date` variable updates on re-render, but the component won't re-render unless triggered by state change or polling.
- **Actually:** TanStack Query refetches every 10s. On each refetch, `todayLocal()` is called again as part of the component re-render triggered by the refetch response. So the date WOULD update after midnight on the next 10s poll cycle. **PASS** — cross-day works via polling.

---

## 6. Bugs Discovered During Audit

### New bugs to file

| ID | Priority | Title | Details |
|----|----------|-------|---------|
| LYR-095 | 🔴 high | `get_status()` skips `_recover_from_db()` — banner disappears on Redis loss | `stopwatch_manager.py:550` calls `redis.get_active_stopwatch()` directly without fallback to `_recover_from_db()`. Root cause of operator's "banner disappeared after 5h pause" report. |
| LYR-096 | 🟡 medium | `task_completion_percentage` dropped between ReflectionModal and stopStopwatch call | `today/page.tsx:112` passes `{ confirmed: opts?.confirmed }` but not `task_completion_percentage`. The value from the modal is never forwarded to the backend. |
| LYR-097 | 🟡 medium | `is_future_task` warning from start endpoint not shown in UI | `StopwatchStartResponse.is_future_task` returned by backend but frontend ignores it. User starts timer for task 2 hours from now with no warning. |
| LYR-098 | 🟡 medium | `micro_mirror` and `calibration_nudge` from stop endpoint not displayed | Backend computes and returns these strings but frontend silently discards them. Research signal lost. |
| LYR-099 | 🟢 low | New task modal start time stale after idle | `defaultStart()` called once on mount via `useState`. If modal reopened 30min later, default time is 30min old. |

---

## 7. Phase 4 P0 List (must fix before Phase 4 features)

1. **Add trash icon to PLANNED rows → DELETE confirmation → `POST /v1/delete`**
   - Add `deleteTask(task_id)` to `lib/tasks.ts`
   - Add Trash2 icon on PLANNED rows in `task-row.tsx`
   - Confirmation dialog: "Delete this task?"
   - Backend already supports it

2. **Add ban icon to EXECUTING and PAUSED rows → SKIP confirmation → `POST /v1/tasks/{id}/mark-abandoned`**
   - `task-row.tsx` currently only shows Ban on PLANNED
   - Backend already accepts EXECUTING/PAUSED in mark-abandoned
   - Confirmation dialog: "Stop and skip this task?"

3. **Remove Trash2 (void) icon from EXECUTED/SKIPPED rows**
   - Per operator UX model: void is a research tool, not a row-level action
   - Removes the hardcoded `"data_quality"` reason problem

4. **Fix `task_completion_percentage` passthrough**
   - `today/page.tsx:112` — add `task_completion_percentage: opts?.completionPct` to the `stopStopwatch()` call

5. **Fix interruption flow: handle mixed PAUSED + other conflicts**
   - `new-task-modal.tsx:81` — change from `every` to check if ANY conflict is PAUSED
   - Show interruption offer if at least one PAUSED conflict exists, show remaining conflicts as warning

6. **Fix LYR-095: `get_status()` must call `_recover_from_db()`**
   - `stopwatch_manager.py:550` — use `_get_active()` instead of `redis.get_active_stopwatch()` directly

7. **Edit PLANNED tasks** — click PLANNED row → opens NewTaskModal prefilled with existing values + "Save" button → calls `POST /v1/reschedule`

8. **Stopwatch start: catch `InvalidStateTransitionError` and return friendly 400**
   - `stopwatch.py:67-68` — add specific catch for state machine errors with user-friendly message

---

## 8. Phase 4 P1 List (fix during Phase 4)

1. **Settings page void flow** — `/settings/data` with multi-select "Void sessions" tool, reason picker, `void_reason_detail` when reason='other'
2. **Display `micro_mirror` and `calibration_nudge`** on stop — show in info banner after timer stops
3. **Display `is_future_task` warning** — yellow warning in ReadinessModal before confirming start
4. **Recompute `defaultStart()`** when NewTaskModal opens — reset `start` state in `useEffect` or `onOpenChange`
5. **Pause reason picker** — small dropdown in ActiveTimerBanner's pause flow (6 reasons from PAUSE_REASONS)
6. **Sort PLANNED ascending** — currently desc with everything else; PLANNED tasks should show next-up first
7. **Reschedule UI** — no frontend path to `POST /v1/reschedule` exists; needed for edit-PLANNED flow

---

## 9. Items Correct As-Is

- 12-hour time format throughout
- Status pill color mapping (all 6 states)
- Voided tasks filtered from Today view
- DELETED tasks filtered from query response
- Readiness modal with behavioral anchors (not numeric-only)
- Reflection modal with anchored 1–5 scale
- Early-stop gate with confirmation flow
- Paused parent notification after stop
- Optimistic pause/resume with rollback
- Global error parsing in `api.ts` (handles string and structured detail)
- Past-task creation rejection with friendly message
- Cross-day rendering works via 10s polling
- Completion % clamped 0–100 on both layers (frontend onChange + backend Pydantic)
- Multi-user scoping via ContextVar (`StopwatchManager._user_key()`, `_require_current_user()`)
- `queryTasks` filters DELETED client-side; backend passes all states when `state=all`

---

## 10. Reframe: LLM-powered task creation in v2 backlog

The "LLM-powered task creation" item in `docs/product.md §3` should be reframed:

> **Phase 6 candidate, not deferred indefinitely.** Cost is much lower than originally estimated because OpenClaw infrastructure already exists and just needs to be exposed as a web client. Implementation sketch: text input field on web UI → POSTs to OpenClaw gateway → existing SKILL.md workflow → backend calls. The agent already handles natural-language parsing, conflict resolution, and readiness capture — the web UI just needs a chat input that proxies to the same agent.
