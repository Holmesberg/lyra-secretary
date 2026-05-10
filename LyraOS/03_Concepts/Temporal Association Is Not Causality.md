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
  - "[[Causal Firewall]]"
  - "[[Exposure Contamination]]"
  - "[[Pause Predictions Can Reduce Overrun Or Interrupt Flow]]"
data_class: internal_architecture
---

# Temporal Association Is Not Causality

## Definition

An event following an exposure is a temporal association unless a specific causal design supports stronger claims.

## Why It Matters

Response-style logs are seductive. They can make correlation look like proof of influence.

## Where It Appears

- deferred temporal association atom
- pause prediction response analysis
- feedback-loop interpretation

## Failure Mode

The system claims intervention effects from proximity alone.

## Related Tensions

- [[Tension - LLM Plausibility vs Ground Truth]]
- [[Tension - Helpfulness vs Contamination]]
