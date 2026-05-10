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
  - "[[Exposure Ledger]]"
  - "[[Fail-Closed Unknown]]"
  - "[[Policy Becomes Invisible Truth]]"
data_class: internal_architecture
---

# Decision - Exposure Ledger Fails Closed

## Context

LyraOS shows predictions, nudges, mirrors, and repair prompts that can alter later behavior.

## Decision

Baseline learning is allowed only when exposure context returns `NONE`. `UNKNOWN`, `EXPOSED`, and `INTERVENTION` are not baseline-clean by default.

## Why

False clean is more dangerous than missing some usable data.

## Consequences

- Missing ledger state blocks baseline learning.
- Policy effect diagnostics must track gate behavior.
- Future stratified profiles require successor contracts.

## Links

- [[Causal Firewall]]
- [[Tension - Policy Simplicity vs Contamination Fidelity]]
- [[Unknown Must Remain Structurally Expensive]]
