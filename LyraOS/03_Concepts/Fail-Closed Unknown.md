---
type: concept
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
  - MANIFESTO.md
related:
  - "[[Epistemic Core]]"
  - "[[Measurement Validity]]"
  - "[[Self Model]]"
  - "[[Baseline Cleanliness]]"
  - "[[Measurement Validity Firewall]]"
  - "[[Unknown Must Remain Structurally Expensive]]"
data_class: internal_architecture
---

# Fail-Closed Unknown

## Definition

`UNKNOWN` is not neutral. It blocks baseline learning unless a successor contract explicitly defines another profile.

Fail-closed unknown is the negative space of [[Measurement Validity]]: the system refuses to certify what it cannot inspect.

## Why It Matters

The most dangerous corruption is silent false cleanliness.

## Required Behavior

- Missing ledger availability returns `UNKNOWN`.
- Broken decision/render/suppression joins return `UNKNOWN`.
- Unavailable policy config returns `UNKNOWN`.
- Unmeasured or unsupported signal targets remain explicit instead of pretending protection exists.

## Consequences

- Some data becomes unusable for baseline learning until context is repaired.
- Diagnostics must make unknown rates visible.
- Product and analytics pressure must not downgrade unknowns into defaults.

## Where It Appears

- Exposure Ledger gate
- Cortex clean-data profiles
- repair provenance
- orchestration uncertainty maps

## Failure Mode

Unknowns become zeros, averages, or safe defaults.

## Failure Modes To Watch

- optional filters that include unknown rows by default
- UI labels that imply unknown means low confidence but still usable
- tests that only assert positive exposure cases and skip missing-ledger cases
- policy effect dashboards that do not split unknown reasons

## Related Tensions

- [[Tension - Product vs Research Velocity]]
- [[Tension - Policy Simplicity vs Contamination Fidelity]]
