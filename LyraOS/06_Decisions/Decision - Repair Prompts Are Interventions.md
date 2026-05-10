---
type: decision
status: accepted
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Human-in-the-Loop Repair]]"
  - "[[Manual Tracking Collapses Under Cognitive Load]]"
  - "[[Tension - Helpfulness vs Contamination]]"
data_class: internal_architecture
---

# Decision - Repair Prompts Are Interventions

## Context

Repair prompts help users recover missing lifecycle state but also change attention and measurement context.

## Decision

Repair prompts are exposure/intervention events and must preserve repair provenance.

## Why

Repair improves product continuity but cannot become observed stopwatch truth.

## Consequences

- Confirmed repairs are not equivalent to real-time observed transitions.
- Repaired durations remain excluded from default measured-execution learning.
- Prompt frequency is both product friction and research contamination.

## Links

- [[Human-in-the-Loop Repair]]
- [[Tension - Frictionless UX vs Measurable Behavior]]
- [[Repair Prompts Improve Continuity But Contaminate Baseline]]
