---
type: concept
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - archive/appstore/summary_of_app.md
related:
  - "[[Task Execution]]"
  - "[[Human-in-the-Loop Repair]]"
  - "[[Clean Data Profile]]"
data_class: internal_architecture
---

# Task Lifecycle

## Definition

The state progression from planned work through execution, pause, completion, skipping, deletion, and recovery.

## Why It Matters

Task lifecycle events are both product state and the substrate for planning-vs-execution measurement.

## Where It Appears

- task state machine
- stopwatch manager
- overdue recovery
- repair prompts

## Failure Mode

Recovered or retroactive lifecycle state is treated as real-time observed execution.

## Related Tensions

- [[Tension - Frictionless UX vs Measurable Behavior]]
- [[Tension - Automation vs Provenance]]
