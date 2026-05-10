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
  - "[[Epistemic Core]]"
  - "[[Measurement Validity]]"
  - "[[Self Model]]"
  - "[[Exposure Ledger]]"
  - "[[Policy Becomes Invisible Truth]]"
  - "[[Interpretation Drift Log]]"
data_class: internal_architecture
---

# Policy as Hypothesis

## Definition

Exposure horizon policy is a model of possible contamination, not contamination itself.

Policy protects [[Measurement Validity]] only while it remains visible as a hypothesis.

## Why It Matters

If the policy is too short, it certifies contaminated rows as clean. If too long, it makes everything unusable.

## Consequences

- Policy versions must be visible in contamination results.
- Policy effect distributions must be reviewed over time.
- Changing a horizon can change historical clean/unsafe interpretation.
- No policy version should be treated as final scientific truth.

## Review Signals

- unexpected rise in `NONE`
- high `UNKNOWN`
- high ledger incomplete rate
- high `EXPOSED` rate that collapses usable baseline data
- disagreement between operator judgment and gate distribution

## Where It Appears

- exposure horizon policy
- policy effect logs
- clean-data gates

## Failure Mode

The gate becomes a hidden truth authority.

## Failure Modes To Watch

- policy values edited without a rationale note
- diagnostics collected but never reviewed
- clean-data claims omitting policy version
- horizon values copied into prose as if validated facts

## Related Tensions

- [[Tension - Policy Simplicity vs Contamination Fidelity]]
- [[Tension - Automation vs Provenance]]
