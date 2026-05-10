---
type: domain
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - archive/appstore/summary_of_app.md
related:
  - "[[Task Lifecycle]]"
  - "[[Human-in-the-Loop Repair]]"
  - "[[Manual Tracking Collapses Under Cognitive Load]]"
data_class: internal_architecture
---

# Task Execution

## What It Is

The task and stopwatch system records planning, execution, pause/resume, completion, and recovery behavior.

## Why It Exists

It is the primary product workflow and the core behavioral trace for planning-vs-execution research.

## Canonical Source Refs

- `backend/app/services/task_manager.py`
- `backend/app/services/stopwatch_manager.py`
- `backend/app/state_machine.py`

## Related Concepts

- [[Human-in-the-Loop Repair]]
- [[Observed vs Derived vs Inferred]]
- [[Clean Data Profile]]

## Active Risks

- Forgotten transitions create instrumentation gaps.
- Retroactive repair is mistaken for real-time observation.
- Product recovery creates invalid measured-execution rows.

## Open Questions

- Which repaired traces deserve a future validated repaired-data profile?

## Known Emergent Patterns

- [[Manual Tracking Collapses Under Cognitive Load]]
- [[User Recovery Affordances Create Research Boundary Pressure]]
