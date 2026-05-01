# Stale-session recovery policy (2026-05-01 rework)

## Trigger incident

Operator's `Build session` task (planned 60 min) was started at 02:24 UTC,
paused at 08:22 UTC for a context-switch with intent to resume, then auto-
SKIPPED by the 12h sweep at 14:37 UTC. **5h 58m of honest work was
mis-classified as abandoned.** Restored manually:

- task → EXECUTED, executed_duration = 358 min
- session.end_time = paused_at (08:22 UTC), auto_closed = false
- pause_event normalized to zero-length (intent preserved, no fake hours)

## Old policy (12h blanket)

Any open session with `start_time_utc < now - 12h` was closed and the task
flipped to SKIPPED — regardless of whether the user had paused with intent
to resume, or how much honest work had accumulated before the pause.

Failure modes:
- Real deep-work sessions paused for context-switch are killed at 12h.
- Honest executed work is mis-classified as SKIPPED, biasing research data.
- Operator gets no signal — silent state mutation.
- Pause-event close path could write **negative** `duration_minutes` when
  `paused_at_utc > end_time_utc` (separate bug found during this work).

## New policy

Two distinct branches based on session shape:

### Paused branch (`session.paused_at_utc < now - 48h`)

User explicitly paused; intent-to-resume is real. Decision uses the same
**50% early-stop gate** as the manual stopwatch path:

```
executed_so_far = (paused_at - start) - sum(closed pause durations)
if executed_so_far ≥ 0.5 * planned:
    task → EXECUTED, executed_duration = round(executed_so_far)
else:
    task → SKIPPED  (early-stop gate)
session.end_time = paused_at  (the honest stop moment)
session.auto_closed = True
open pause_event → resumed_at = max(paused_at, end_time), duration ≥ 0
```

### Active branch (`session.paused_at_utc IS NULL AND session.start_time_utc < now - 48h`)

No pause means no explicit user signal of intent. An unattended always-
running timer cannot honestly claim executed time:

```
task → SKIPPED (always)
session.end_time = start_time + planned  (defensible synthetic; SKIPPED
                                          tasks are filtered from research)
```

### Why 48h on both

- 24h is too short — `pause → sleep → resume next day` routinely crosses
  12-18h, and `pause Friday → resume Monday` crosses 60h. Under 48h, the
  weekend-pause pattern is still ambushed; the operator's preference was
  to accept that for now.
- Higher (72h+, or "never auto-resolve paused") was considered. Rejected
  because Redis active-stopwatch state and the multi-tasking swap path
  (Apr 25 fix in `stopwatch_manager.py`) have edge cases when paused
  sessions sit forever — ghost active keys, stale rehydrated banners.
  48h is the floor where Redis-side risk starts dominating.

## Bugs fixed in same change

1. **Negative `pause_event.duration_minutes`.** Old recovery code blindly
   set `evt.resumed_at_utc = end_time` even when `paused_at > end_time`,
   producing negative durations (observed: -298 min on the trigger
   incident). New code: `resumed_at = max(paused_at, end_time)`, then
   `duration = max(0, ...)`.

2. **Honest `executed_duration_minutes` for recovered EXECUTED tasks.**
   Previously the recovery never wrote `executed_duration` (always
   SKIPPED). The new EXECUTED branch writes the computed real time so
   research queries see honest data.

## Files

- `backend/app/workers/jobs/stale_session_recovery.py` — implementation
- `backend/tests/test_jobs_skip_voided_tasks.py` — fixture bumped to 49h
- `backend/tests/test_pause_resume_pause_event.py` — fixture bumped to 49h
- `CLAUDE.md` — APScheduler description updated

## Open follow-ups (not in this change)

- **`orphan_task_recovery.py` consistency.** Currently a PAUSED-with-no-
  open-session task always → SKIPPED. Same 50% gate could be applied for
  consistency, but that job runs on Task state alone (no session to
  compute executed time from), so the data isn't there. Defer.
- **UI demotion of long-paused tasks.** Visually mute paused tasks past
  ~24h in the today view so the queue doesn't bloat with stale Resume
  buttons. Separate ticket.
