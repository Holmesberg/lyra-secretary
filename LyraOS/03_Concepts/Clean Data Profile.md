---
type: concept
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-12
last_reviewed: 2026-05-12
source_refs:
  - docs/cortex_contract_v0.md
  - docs/cortex_product_research_contract_v0.md
  - docs/layered_epistemic_architecture.md
related:
  - "[[Layered Epistemic Architecture]]"
  - "[[Cortex]]"
  - "[[Baseline Cleanliness]]"
  - "[[Observed vs Derived vs Inferred]]"
data_class: internal_architecture
---

# Clean Data Profile

## Definition

A declared subset of data that is valid for a specific inference purpose under known provenance and exclusion rules.

## Why It Matters

Different analyses need different exclusions. Descriptive history is not the same as baseline learning.

[[Layered Epistemic Architecture]] requires every Layer B metric, Layer C model, and output surface to declare which clean-data profile it consumes.

## Where It Appears

- measured execution
- planning calibration
- pause process
- descriptive history

## Failure Mode

Rows valid for display become training evidence.

## Related Tensions

- [[Tension - Product vs Research Velocity]]
- [[Tension - Frictionless UX vs Measurable Behavior]]
