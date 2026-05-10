---
type: tension
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
related_domains:
  - "[[Epistemic Core]]"
  - "[[Measurement Validity]]"
  - "[[Self Model]]"
  - "[[Exposure Ledger]]"
  - "[[Cortex]]"
related_decisions:
  - "[[Decision - Exposure Ledger Fails Closed]]"
related_patterns:
  - "[[Policy Becomes Invisible Truth]]"
data_class: internal_architecture
---

# Tension - Policy Simplicity vs Contamination Fidelity

## Contradiction

Simple horizon policy is implementable and auditable, but contamination is contextual and uncertain.

## Why Both Sides Are Real

No policy means no gate. Overconfident policy means false clean or everything contaminated.

## Current Resolution

Use versioned horizon policy and policy effect diagnostics. Treat policy as hypothesis, not truth.

## Current Holding Pattern

- Keep v0 horizons simple enough to implement and audit.
- Keep policy versions explicit in gate outputs.
- Use policy effect logs to detect when the simple policy behaves incoherently.
- Record interpretation drift when evidence changes what a policy is believed to mean.

## Failure Mode

The gate becomes invisible authority.

## Opposite Failure Mode

The policy becomes so cautious that all meaningful baseline learning collapses into `EXPOSED` or `UNKNOWN`.

## Watch Signals

- high unknown rate
- high ledger incomplete rate
- unexpectedly high clean rate after many exposures
- broad exposed rate that makes baselines unusable
- source changes without matching policy review
- policy diagnostics not consulted during model interpretation
