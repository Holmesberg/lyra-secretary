---
authority: parked
may_authorize_code: false
runtime_owner: none
promotion_condition: >
  Trusted users lose continuity after interruptions or long pauses, and simple
  paused-task/resume-banner affordances are not enough.
---

# Open Threads Re-entry Recovery Plan

Status: parked future implementation.

## Core Product Angle

This should strengthen re-entry, not insight.

Preferred product posture:

```text
open threads -> recovery options
```

Forbidden posture:

```text
switches -> fragmentation score
```

Near-term user-facing copy:

```text
You have 3 open threads from earlier today.
```

or:

```text
Parked after a task switch.
Paused for 42m.
Pick it back up, reschedule, or drop?
```

Do not expose `context_switching_footprint` in product UI.

## Required Read-Time Metrics

Derive first; persist only if attribution cannot be reconstructed:

- `open_thread_count`
- `parked_task_count`
- `reentry_latency_minutes`
- `reentry_resolution_type`
- `time_to_resolution_minutes`
- `open_thread_end_of_day_count`
- `task_switch_count`
- `interruption_chain_count`

Resolution outcome values:

- `resumed`
- `completed_later`
- `rescheduled`
- `dropped`
- `marked_irrelevant`
- `stale_open_end_of_day`
- `auto_closed`

Without resolution outcomes, Lyra only knows switching happened, not whether it
mattered.

## First Surface

Pulse / Today recovery module:

```text
Open threads
3 from earlier today

[Pick back up] [Reschedule] [Drop] [Mark done] [Keep parked]
```

Rules:

- No weekly "you switch a lot" insight.
- No focus/motivation/avoidance copy.
- No `fragmentation_score`.
- No passive/provider evidence.
- No automatic mutation.
- User chooses the resolution.

## Target Files If Promoted

Likely backend:

- `backend/app/services/runtime_topology.py`
- `backend/app/services/stopwatch_manager.py`
- `backend/app/api/v1/endpoints/stopwatch.py`
- `backend/app/api/v1/endpoints/tasks.py`
- `backend/app/api/v1/endpoints/analytics.py`

Likely frontend:

- `frontend/components/active-timer-banner.tsx`
- Today/Pulse task-list surfaces
- recovery/insight components

## Tests If Promoted

Backend:

- task switch creates recoverable parent-child topology;
- open thread derives from paused open session;
- stale/auto-closed/voided/dirty sessions are excluded from clean averages;
- resolution outcome derives correctly for resume, reschedule, drop, mark done,
  and auto-close;
- `executed_duration_minutes` never includes pause overhead.

Frontend/browser:

- start Task A, interrupt into Task B, resume Task A;
- open-thread copy is neutral;
- all actions require explicit confirmation;
- copy does not mention focus, motivation, avoidance, failure, or
  fragmentation score.

## Kill Criteria

Kill or park if:

- users read it as judgment;
- false positives dominate;
- it requires passive browser tracking;
- it becomes a score;
- it adds less value than the existing resume banner;
- exposure logging cannot separate pre/post surface behavior.
