---
type: pattern
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Product Surface]]"
  - "[[Human-in-the-Loop Repair]]"
  - "[[Tension - Product vs Research Velocity]]"
data_class: internal_architecture
---

# User Recovery Affordances Create Research Boundary Pressure

## Pattern

Recovery flows improve product continuity but can look like research-valid state if provenance is not preserved.

## Evidence

- Retrospective done affordance is product recovery, not measured execution.
- Repair prompts are allowed only with provenance and exclusions.

## Counter-Evidence

Some future repaired-data profiles may be validated.

## Related Tensions

- [[Tension - Frictionless UX vs Measurable Behavior]]
- [[Tension - Product vs Research Velocity]]

## Related Domains

- [[Product Surface]]
- [[Task Execution]]

## Interpretation

Recovery should preserve continuity without laundering uncertainty.

## Risk

Product repairs update adaptive models as if observed in real time.

## Next Watch Signal

New recovery routes that lack clean-data exclusions.
