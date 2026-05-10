---
type: workstream
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_contract_v0.md
  - backend/app/services/cortex.py
related:
  - "[[Cortex]]"
  - "[[Exposure Ledger]]"
  - "[[Baseline Cleanliness]]"
data_class: internal_architecture
---

# Cortex Gate Coverage

## Goal

Ensure every baseline-learning path evaluates exposure context and fails closed.

## Current State

Cortex provides clean-data profiles and exposure-aware baseline helpers. Descriptive history remains separate.

## Dependencies

- `is_exposed`
- horizon policy config
- legacy exposure adapters

## Open Questions

- Which analytics endpoints still consume raw helpers?
- Which archetype calculations need explicit audit?

## Risks

- One bypass collapses the epistemic model.

## Next Synthesis Checkpoint

Map every baseline consumer to an exposure-aware helper.
