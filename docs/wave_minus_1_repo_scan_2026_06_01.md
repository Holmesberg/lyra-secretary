# Wave -1 Repo Scan - 2026-06-01

**Status:** Completed Wave -1 scan artifact.
**Authority:** Repo scan and implementation guidance. Does not authorize Wave 1+
work by itself.
**Related plan:** `docs/core_product_loop_wave_plan.md`.

## Scope

Wave -1 asked four agents to scan the repo before implementation:

1. Code Agent A - frontend/product loop.
2. Code Agent B - backend/state/data integrity.
3. Docs Agent A - product/global positioning.
4. Docs Agent B - authority/contracts/provider boundaries.

This document records the actionable findings and the Wave 0 decisions taken
from them. It intentionally separates "ship now" from "park" so the core loop
does not absorb every good idea at once.

## Cross-Agent Verdict

The current repo already supports the skeleton of the core loop:

```text
Pulse -> brain dump -> tasks/deadlines -> pressure map -> timer/recovery -> insights
```

The repo is not ready for Wave 1+ automation yet. The safe Wave 0 move is to
stabilize the existing loop, make Pulse the hub, keep Pressure Map diagnostic,
and add tests around resume prediction so recovery does not become nagging.

## What Already Exists

- `/pulse` is a real dashboard hub with today's plan, focus timer, deadlines,
  academic pressure, recovery, integrations, and quick capture.
- Pulse quick capture already opens `BrainDumpQuickModal`, which calls
  `/v1/brain-dump/parse` and `/v1/brain-dump/commit`.
- `/today` remains the dense execution feed with task rows, timer banner,
  resume prediction banner, New Task, retroactive logging, voiding, and
  deadline editing.
- Stopwatch lifecycle is implemented in backend endpoints and
  `StopwatchManager`, with Redis/DB recovery paths and pause-event tracking.
- Resume prediction exists as predictor, worker, scheduler job, notification
  payload, and Today banner.
- Settings has JSON export, staged account deletion, integrations, and profile
  controls.
- Provider and authority docs already establish the core rule:

```text
Adapters translate local dialects.
Core reasons in provider-blind primitives.
Surfaces translate results back into local dialects.
```

## What Is Missing

- Brain dump does not yet bind tasks to already-existing obligations; it only
  confirms bindings discovered inside the same dump. This is Wave 1, not Wave 0.
- Pressure Map recovery options are display-only. Preview-and-confirm recovery
  task creation belongs in Wave 2.
- Occupancy exists in estimate surfaces but is not yet a full pressure-map
  visual primitive.
- Frontend brain-dump logic is duplicated between onboarding and Pulse modal.
- Export is not yet a complete account export across every auxiliary table.
  Treat this as a trust/backlog item, not a quiet Wave 0 rewrite.
- Resume prediction lacked focused worker tests before this pass.
- Several docs contain stale references or supersession ambiguity.

## What Is Duplicated

- Brain-dump parse/commit/review UI exists in onboarding and Pulse with
  slightly different behavior.
- Timer command surfaces exist in both Today and Pulse.
- Deadline matching exists in older parse code and newer deadline heuristic
  code.
- Pressure Map authority is documented in several places. This is safer than
  under-documenting, but future cleanup should centralize references.

## What Should Be Deleted Or Cleaned Later

Do not delete large historical docs in Wave 0. Cleanups should be targeted:

- Remove stale "new/preview" framing around Pulse now that it is the main hub.
- Remove or hide inert Pulse controls until they have real behavior.
- Fix stale docs claiming brain-dump commit is a single DB transaction.
- Fix stale "5 min cooldown" resume-prediction comments; the actual cooldown is
  60 minutes.
- Rewrite stale docs that still call Moodle WS submissions parked.
- Clarify export copy where it implies full-account export but only exports the
  current client-side task table.

## What Should Be Parked

Park these until their wave:

- Existing-obligation brain-dump binding: Wave 1.
- Pressure-map plan creation: Wave 2.
- Occupancy map visuals: after Wave 2 unless dogfood proves it blocks the loop.
- Recurring schedule imports and provider adapters: Wave 5.
- Browser extension/passive activity capture: Wave 6 candidate only.
- Autonomous planning, proactive interventions, and provider-native completion
  truth: parked until explicit successor governance.
- Observer sovereignty: concept-note/watchlist only.

## Wave 0 Changes Implemented

Frontend:

- Promoted Pulse as the first nav item and brand target.
- Removed the Pulse "new" framing from navigation.
- Confirmed Today empty-state brain-dump link points to `/pulse#quick-capture`.
- Confirmed quick capture has the `quick-capture` anchor.
- Brain-dump commit now invalidates the academic pressure-map query.
- Pulse focus card now surfaces the same "started early" informational hint as
  Today when the backend returns `is_future_task`.
- Pulse greeting hides inert search/notification controls unless a search
  handler exists.

Backend/tests:

- Added resume-prediction worker tests for:
  - firing writes one log row and queues one notification,
  - fresh pauses do not fire,
  - cooldown blocks refire,
  - max-fire cap blocks nagging,
  - per-user scoping prevents another user's paused task from being evaluated.

Docs:

- Added this Wave -1 scan artifact as the repo-level handoff for the scan.

## Browser Verify After Wave 0

Use two trusted accounts if possible.

1. Open `/pulse`.
2. Confirm Pulse is first in nav and the LyraOS brand returns to Pulse, not
   Today.
3. Scroll to quick capture or click any empty-state brain-dump link; confirm the
   URL/scroll target is `/pulse#quick-capture`.
4. Paste a small messy dump, parse, commit, and confirm tasks/deadlines appear.
5. Confirm Pressure Map refreshes after the commit without a hard reload.
6. Start a future-scheduled task from Pulse; confirm the "started early" hint
   appears.
7. Pause, refresh, resume, stop; confirm the timer survives page switches
   between Pulse and Today.
8. Pause a task long enough for resume prediction or seed/simulate the worker;
   confirm Today shows:

```text
You left {task} paused {duration} ago. Pick it back up?
```

9. Dismiss/resume the banner; confirm it does not nag immediately.
10. Export data and walk through account deletion modal up to the final
    destructive confirmation without completing deletion unless intended.
11. Switch accounts and verify no tasks, deadlines, pressure data, timer state,
    or resume banners leak between users.

## Not Wave 0

Do not judge Wave 0 by whether these exist yet:

- Brain dump binding to pre-existing deadlines.
- Pressure Map creating recovery tasks.
- Full task graph/grouping.
- ICS/Google/Outlook/Teams/Sheets/Excel import expansion.
- Browser extension candidate capture.
- AI estimate priors beyond the already existing estimate/occupancy surfaces.
