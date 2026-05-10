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
  - "[[Causal Firewall]]"
  - "[[Policy as Hypothesis]]"
data_class: internal_architecture
---

# Replay Boundary

## Definition

The minimum audit trail needed to reconstruct what information the system injected into a user's decision context.

## Why It Matters

Dynamic generated content cannot be reconstructed from a template alone. Rendered stimulus, hash, and policy version matter.

## Where It Appears

- exposure render events
- content snapshots
- source digests

## Failure Mode

The system cannot later tell what the user actually saw.

## Related Tensions

- [[Tension - Automation vs Provenance]]
- [[Tension - Policy Simplicity vs Contamination Fidelity]]
