---
authority: parked
may_authorize_code: false
runtime_owner: none
promotion_condition: >
  Manual capture cannot represent recurring and provider-sourced obligations
  without clutter, duplicate state, or pressure-map mistrust.
---

# Provider Middleware And Recurring Obligations Plan

Status: parked future implementation.

## Global Product Frame

Lyra is not academic-only. Academia is the first concrete provider module.

General loop:

```text
capture/import obligations
-> normalize provider-blind structure
-> relate tasks, deadlines, schedules, and repeated commitments
-> visualize pressure/occupancy
-> create or adjust plans only after confirmation
-> track execution/recovery
-> recalibrate
```

## Provider Primitive Types

- `obligation`
- `deadline`
- `scheduled_block`
- `recurring_commitment`
- `meeting`
- `resource`
- `task_candidate`
- `completion_candidate`
- `availability_constraint`

## Provider Matrix

| Provider | Near-Term Role | Not Allowed |
| --- | --- | --- |
| Brain dump | manual capture into candidates | silent canonical task creation |
| ICS | schedule/deadline import, recurrence expansion | execution truth |
| Google Calendar | availability, meetings, constraints | attendance/completion truth |
| Moodle/Baseet | academic deadlines/resources | study proof or mastery |
| Outlook/Teams/Google Meet | scheduled obligations and meeting context | hidden monitoring |
| Sheets/Excel | structured plan import | behavioral evidence |
| Jira/Linear/Notion | future work/package context | completion truth without confirmation |

## Recurrence First Principles

Recurring obligations should create schedule structure, not execution truth.

Examples:

- university lectures;
- repeated meetings;
- gym sessions;
- office hours;
- standing calls;
- recurring review blocks.

Future recurrence fields may include:

- `recurrence_rule`
- `recurrence_source`
- `recurrence_instance_key`
- `series_id`
- `exception_of_series_id`
- `provider_event_id`
- `provider_uid`
- `provider_hash`

## Required Confirmation Boundary

Provider import can create:

- candidates;
- schedule constraints;
- pressure-map context.

Provider import cannot silently create:

- clean execution;
- completion;
- study proof;
- final task truth;
- adaptive personal claims.

## Tests If Promoted

- recurring events expand without duplicate spam;
- DST/timezone boundary cases;
- provider disconnect does not delete user-confirmed native tasks unless user
  explicitly chooses it;
- two-user isolation for provider rows;
- duplicate detection across provider IDs and content hashes;
- pressure map renders provider context as context, not truth;
- no provider-specific naming leaks into core product copy.
