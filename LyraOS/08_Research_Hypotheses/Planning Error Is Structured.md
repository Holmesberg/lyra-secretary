---
type: hypothesis
status: active
confidence: medium
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - MANIFESTO.md
  - archive/appstore/summary_of_app.md
related:
  - "[[Cortex]]"
  - "[[Clean Data Profile]]"
  - "[[Baseline Cleanliness]]"
data_class: internal_architecture
---

# Planning Error Is Structured

## Claim

Humans may be wrong about execution capacity in structured, modelable ways that predict failure.

## Observable Signals

- consistent execution multipliers by category/time/duration bucket
- stable initiation delay patterns
- repeated pause topology

## Counter-Signals

- prediction error collapses to noise after exposure gating
- patterns fail across users or contexts

## Clean-Data Requirements

Baseline tasks must pass measured-execution and exposure gates.

## Exposure Risks

Calibration nudges may change future planning behavior.

## Related Patterns

- [[Exposure Ledger as Causal Firewall]]
- [[Policy Becomes Invisible Truth]]
