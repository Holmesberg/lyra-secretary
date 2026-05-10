---
type: pattern
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - MANIFESTO.md
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Fail-Closed Unknown]]"
  - "[[Baseline Cleanliness]]"
  - "[[Tension - Policy Simplicity vs Contamination Fidelity]]"
data_class: internal_architecture
---

# Unknown Must Remain Structurally Expensive

## Pattern

LyraOS protects validity by making unknowns block or qualify inference instead of disappearing into defaults.

## Evidence

- Exposure Ledger returns `UNKNOWN` when ledger state is unavailable or incomplete.
- OpenClaw contract preserves `UNKNOWN` labels.

## Counter-Evidence

Too many unknowns can make models unusable; diagnostics must show unknown rate.

## Related Tensions

- [[Tension - Product vs Research Velocity]]
- [[Tension - Policy Simplicity vs Contamination Fidelity]]

## Related Domains

- [[Cortex]]
- [[Exposure Ledger]]

## Interpretation

Unknowns are not errors to smooth away. They are measurement facts.

## Risk

Pressure to ship turns unknown into neutral.

## Next Watch Signal

Code paths that default missing exposure state to `NONE`.
