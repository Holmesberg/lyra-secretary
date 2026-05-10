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
  - "[[Exposure Ledger]]"
  - "[[Replay Boundary]]"
  - "[[Temporal Association Is Not Causality]]"
data_class: internal_architecture
---

# Causal Firewall

## Definition

The Exposure Ledger's role as a negative permission system: it stops false baseline claims rather than proving causal attribution.

## Why It Matters

The ledger is not an influence optimizer. Its core job is to prevent contaminated data from being treated as clean.

## Where It Appears

- `is_exposed`
- suppression logging
- policy effect diagnostics

## Failure Mode

Exposure records get misread as proof that the system caused later behavior.

## Related Tensions

- [[Tension - Policy Simplicity vs Contamination Fidelity]]
- [[Tension - Helpfulness vs Contamination]]
