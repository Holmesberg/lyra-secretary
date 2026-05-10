---
type: decision
status: accepted
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_contract_v0.md
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Cortex]]"
  - "[[Observed vs Derived vs Inferred]]"
  - "[[Clean Data Profile]]"
data_class: internal_architecture
---

# Decision - Cortex Is Read-Only

## Context

Cortex canonicalizes metrics and clean-data profiles. If it writes state, it risks turning derived interpretation into stored truth.

## Decision

Cortex remains read-only.

## Why

Derived metrics should be recomputed from raw events and evaluation version.

## Consequences

- State writes belong in service wrappers or product flows.
- Diagnostics can read Cortex outputs but should not mutate from Cortex itself.
- Inference remains reproducible.

## Links

- [[Research Layer Map]]
- [[Tension - Product vs Research Velocity]]
- [[Baseline Cleanliness]]
