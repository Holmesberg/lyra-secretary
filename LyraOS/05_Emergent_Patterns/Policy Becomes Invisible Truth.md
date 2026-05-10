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
  - "[[Policy as Hypothesis]]"
  - "[[Exposure Ledger]]"
  - "[[Tension - Policy Simplicity vs Contamination Fidelity]]"
data_class: internal_architecture
---

# Policy Becomes Invisible Truth

## Pattern

Once a policy gates downstream inference, callers may treat the policy output as reality rather than a hypothesis.

## Evidence

- Horizon policy controls `NONE`, `EXPOSED`, and `UNKNOWN`.
- Policy effect logging was added to detect gate behavior over time.

## Counter-Evidence

Explicit policy audit and drift review can keep the policy visible.

## Related Tensions

- [[Tension - Policy Simplicity vs Contamination Fidelity]]

## Related Domains

- [[Exposure Ledger]]
- [[Cortex]]

## Interpretation

The gate itself must be an object of measurement.

## Risk

Wrong horizons silently create false clean or unusable baselines.

## Next Watch Signal

High `NONE`, `EXPOSED`, or `UNKNOWN` rates that do not match operator expectations.
