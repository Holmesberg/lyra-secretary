---
type: counterfactual
status: active
confidence: medium
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Human-in-the-Loop Repair]]"
  - "[[Manual Tracking Collapses Under Cognitive Load]]"
  - "[[Decision - Repair Prompts Are Interventions]]"
data_class: internal_architecture
---

# Counterfactual - No Repair Prompts

## Alternative World

LyraOS silently logs suspected lifecycle gaps but never asks the user to repair them.

## Expected Benefit

No prompt contamination or user interruption.

## Expected Harm

Continuity suffers and recoverable instrumentation gaps stay unresolved.

## What Current Architecture Assumes

Selective, throttled repair prompts are worth the intervention cost.

## What Evidence Could Change The Assumption

High dismissal rates, retention harm, or repair confirmations that do not improve continuity.

## Related Tensions

- [[Tension - Frictionless UX vs Measurable Behavior]]
- [[Tension - Helpfulness vs Contamination]]
