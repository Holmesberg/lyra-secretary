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
  - "[[User Burden Surface]]"
  - "[[Retention as Research Constraint]]"
  - "[[Tension - Frictionless UX vs Measurable Behavior]]"
data_class: internal_architecture
---

# Decision - No New User Burden Without Contract

## Context

More prompts could improve model data while harming retention and real-world use.

## Decision

No new required user input is allowed for research convenience without a successor contract or explicit amendment.

## Why

Longitudinal inference depends on users continuing to use the product.

## Consequences

- Passive signals and derived metrics are preferred.
- New burden requires friction cost, retention risk, clean-data impact, and sunset plan.
- Repair prompts must obey interruption budgets.

## Links

- [[Tension - Product vs Research Velocity]]
- [[Retention as Research Constraint]]
- [[User Burden Surface]]
