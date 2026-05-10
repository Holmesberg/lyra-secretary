---
type: domain
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_contract_v0.md
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Epistemic Core]]"
  - "[[Measurement Validity]]"
  - "[[Self Model]]"
  - "[[Research Layer Map]]"
  - "[[Clean Data Profile]]"
  - "[[Exposure Ledger]]"
data_class: internal_architecture
---

# Cortex

## What It Is

Cortex is the read-time canonicalization layer for behavioral metrics and clean-data profiles.

It is a mechanism that protects [[Measurement Validity]], not the whole measurement theory.

## Why It Exists

It prevents downstream inference from mixing spaces, treating derived metrics as raw facts, or learning from invalid baselines.

## Core Invariants

- Cortex is read-only.
- Derived metrics are recomputed from raw events and evaluation version.
- Clean-data profiles are purpose-specific, not generic.
- Baseline helpers must call exposure context and fail closed on unsafe states.
- Descriptive history can include exposed rows only when it declares descriptive use.

## Consequences

- Inference paths that cannot call exposure context cannot call themselves baseline inference.
- Metrics can be displayed or described without becoming learning evidence.
- Legacy product names such as `bias_factor` must remain mapped back to Cortex metric meaning.

## Canonical Source Refs

- `backend/app/services/cortex.py`
- `docs/cortex_contract_v0.md`
- `docs/cortex_product_research_contract_v0.md`

## Related Concepts

- [[Baseline Cleanliness]]
- [[Clean Data Profile]]
- [[Fail-Closed Unknown]]

## Active Risks

- A caller bypasses exposure-aware helpers.
- Descriptive history is mistaken for baseline learning.
- Legacy metric names obscure Cortex canonical meanings.

## Failure Modes To Watch

- raw queries rebuilding baseline logic outside Cortex
- analytics endpoints blending descriptive and learning profiles
- model outputs persisting labels that Cortex only derived at read time
- repaired or retroactive rows appearing in measured-execution baselines

## Open Questions

- Which helpers still need explicit exposure gate coverage?

## Known Emergent Patterns

- [[Exposure Ledger as Causal Firewall]]
- [[Unknown Must Remain Structurally Expensive]]
