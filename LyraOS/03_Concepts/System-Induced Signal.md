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
  - "[[Exposure Contamination]]"
  - "[[Feedback Surfaces]]"
  - "[[Baseline Cleanliness]]"
data_class: internal_architecture
---

# System-Induced Signal

## Definition

Behavior or self-report that may have changed because LyraOS exposed a prediction, nudge, mirror, prompt, or system capability.

## Why It Matters

System-induced behavior may be valuable product behavior, but it is not clean baseline evidence.

## Where It Appears

- exposure-aware baseline gates
- JARVIS insights
- pause/resume predictions
- repair prompts

## Failure Mode

The system measures its own influence and calls it natural cognition.

## Related Tensions

- [[Tension - Helpfulness vs Contamination]]
- [[Tension - Frictionless UX vs Measurable Behavior]]
