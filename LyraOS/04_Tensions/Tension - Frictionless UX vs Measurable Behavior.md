---
type: tension
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
related_domains:
  - "[[Product Surface]]"
  - "[[Task Execution]]"
related_decisions:
  - "[[Decision - Repair Prompts Are Interventions]]"
related_patterns:
  - "[[Manual Tracking Collapses Under Cognitive Load]]"
data_class: internal_architecture
---

# Tension - Frictionless UX vs Measurable Behavior

## Contradiction

The easiest product flow often omits the cleanest measurement event.

## Why Both Sides Are Real

Users need low-friction execution. Research needs reliable transitions, timing, and provenance.

## Current Resolution

LyraOS favors product continuity and uses repair prompts only under interruption-budget rules.

## Failure Mode

Either users are overburdened, or missing lifecycle state gets laundered into clean data.

## Watch Signals

- increased prompt frequency
- rising repaired-duration usage
- users ignoring recovery prompts
