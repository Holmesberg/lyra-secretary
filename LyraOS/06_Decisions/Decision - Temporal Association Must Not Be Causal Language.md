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
  - "[[Temporal Association Is Not Causality]]"
  - "[[Causal Firewall]]"
  - "[[Tension - LLM Plausibility vs Ground Truth]]"
data_class: internal_architecture
---

# Decision - Temporal Association Must Not Be Causal Language

## Context

Response-style tables invite misuse because people read exposure followed by action as causality.

## Decision

The deferred event atom must be named temporal association, not response linkage, and must be described as correlational only.

## Why

Language shapes downstream interpretation.

## Consequences

- Association rows cannot be used as causal evidence.
- Causal claims require specific research design.
- Future schemas must include explicit caution comments.

## Links

- [[Temporal Association Is Not Causality]]
- [[Exposure Ledger as Causal Firewall]]
- [[Tension - Helpfulness vs Contamination]]
