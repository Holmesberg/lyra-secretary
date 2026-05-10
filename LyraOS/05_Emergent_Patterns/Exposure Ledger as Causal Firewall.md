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
  - "[[Measurement Validity]]"
  - "[[Self Model]]"
  - "[[Exposure Ledger]]"
  - "[[Causal Firewall]]"
  - "[[Decision - Exposure Ledger Fails Closed]]"
data_class: internal_architecture
---

# Exposure Ledger as Causal Firewall

## Pattern

Exposure Ledger is most valuable as a permission boundary for baseline inference, not as an attribution system.

## Evidence

- `is_exposed` returns fail-closed states.
- Exposure policy effect diagnostics exist to audit gate behavior.

## Counter-Evidence

Future causal experiments may require randomized withholding or stratified analysis.

## Related Tensions

- [[Tension - Helpfulness vs Contamination]]
- [[Tension - Policy Simplicity vs Contamination Fidelity]]

## Related Domains

- [[Exposure Ledger]]
- [[Cortex]]

## Interpretation

The ledger's negative role is stronger than its analytic role.

It remains a mechanism inside [[Measurement Validity]], not the conceptual center of the system.

## Risk

Teams start reading exposure records as proof of influence.

## Next Watch Signal

Any analytics language implying exposure caused behavior.
