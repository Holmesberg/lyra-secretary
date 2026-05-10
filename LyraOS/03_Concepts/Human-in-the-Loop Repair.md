---
type: concept
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Task Execution]]"
  - "[[Manual Tracking Collapses Under Cognitive Load]]"
  - "[[Repair Prompts Improve Continuity But Contaminate Baseline]]"
data_class: internal_architecture
---

# Human-in-the-Loop Repair

## Definition

The system may detect likely missing lifecycle transitions and ask the user to confirm or deny them, without silently converting inference into observed truth.

## Why It Matters

Manual lifecycle tracking decays under deep work. Repair can preserve continuity, but it is also an intervention.

## Where It Appears

- repair prompts
- stale session recovery
- overdue task recovery
- pause confirmation flows

## Failure Mode

Inferred durations are treated as measured stopwatch traces.

## Related Tensions

- [[Tension - Frictionless UX vs Measurable Behavior]]
- [[Tension - Helpfulness vs Contamination]]
