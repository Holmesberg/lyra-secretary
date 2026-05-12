---
type: domain
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-12
last_reviewed: 2026-05-12
source_refs:
  - docs/cortex_product_research_contract_v0.md
  - docs/cortex_contract_v0.md
  - docs/layered_epistemic_architecture.md
related:
  - "[[Layered Epistemic Architecture]]"
  - "[[Cortex]]"
  - "[[Clean Data Profile]]"
  - "[[Baseline Cleanliness]]"
data_class: internal_architecture
---

# Research Layer Map

The research layer interprets product behavior under identifiability constraints. It does not create product semantics.

[[Layered Epistemic Architecture]] is the routing contract that tells the research layer whether it is reading observed behavior, derived metrics, interpretive hypotheses, or self-reported narrative.

## Owns

- derived metrics
- clean-data profiles
- hypothesis classification
- uncertainty propagation
- exposure-aware baseline gating

## Must Preserve

- reproducibility
- falsifiability
- unknown propagation
- source provenance
- layer provenance

## Related

- [[Measurement Validity Firewall]]
- [[Exposure Contamination]]
- [[Tension - Product vs Research Velocity]]
