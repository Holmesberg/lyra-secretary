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
  - "[[Cortex]]"
related_decisions:
  - "[[Decision - No New User Burden Without Contract]]"
related_patterns:
  - "[[User Recovery Affordances Create Research Boundary Pressure]]"
data_class: internal_architecture
---

# Tension - Product vs Research Velocity

## Contradiction

Product needs fast, useful iteration. Research needs stable measurement boundaries.

## Why Both Sides Are Real

Without product velocity, users leave. Without research discipline, behavior becomes uninterpretable.

## Current Resolution

Product changes are allowed for task completion, clarity, accessibility, latency, or bug repair. Research value alone cannot add friction.

## Failure Mode

Research prompts creep into the product, or product recovery flows silently corrupt baselines.

## Watch Signals

- new required fields
- insight surfaces added without exposure handling
- baseline queries bypassing Cortex gates
