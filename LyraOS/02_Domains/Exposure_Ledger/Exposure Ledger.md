---
type: domain
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
  - backend/app/services/exposure_ledger.py
related:
  - "[[Epistemic Core]]"
  - "[[Measurement Validity]]"
  - "[[Self Model]]"
  - "[[Measurement Validity Firewall]]"
  - "[[Policy as Hypothesis]]"
  - "[[Tension - Policy Simplicity vs Contamination Fidelity]]"
data_class: internal_architecture
---

# Exposure Ledger

## What It Is

Exposure Ledger v0 is a causal firewall and replay boundary for baseline inference.

It is an operational mechanism for [[Measurement Validity]]. It should not become the conceptual center of the vault simply because many systems touch it.

## Why It Exists

Any nudge, prediction, mirror, or repair prompt can change later behavior. The ledger prevents future inference systems from treating post-exposure behavior as natural baseline by default.

## Conceptual Boundary

The ledger answers whether a measurement is admissible under an exposure policy. It does not define all of measurement validity. Cortex, clean-data profiles, provenance, unknown propagation, and the [[Self Model]] are separate load-bearing pieces.

## Core Invariants

- The ledger records information injection context, not intent or causal effect.
- `is_exposed` returns a contamination result, not a truth claim about behavior.
- `NONE` requires a complete policy, ledger, suppression, and legacy-adapter check.
- Missing ledger state returns `UNKNOWN`, never `NONE`.
- Suppression is not exposure, but missing suppression for an unrendered decision is incomplete state.
- Attention proxies and temporal associations are deferred and must not be treated as present.

## Consequences

- Baseline inference becomes policy-relative.
- User-visible feedback must be treated as possible measurement distortion.
- Legacy exposure sources remain relevant until replaced by full dual-write coverage.
- Policy diagnostics are part of the gate's credibility, not optional analytics.

## Canonical Source Refs

- `docs/cortex_product_research_contract_v0.md`
- `backend/app/services/exposure_ledger.py`
- `backend/app/core/exposure_horizon_policies.json`

## Related Concepts

- [[Causal Firewall]]
- [[Replay Boundary]]
- [[Exposure Contamination]]

## Active Risks

- Horizon policy becomes invisible truth.
- Legacy exposure adapters leave gaps.
- Attention proxies remain deferred.

## Failure Modes To Watch

- exposure records used as proof of causal influence
- rendered content represented only by a template id
- `UNKNOWN` collapsed into `NONE` for convenience
- no-render decisions treated as clean without suppression evidence
- policy effect logs ignored when unknown or exposed rates drift
- vault links treating Exposure Ledger as the theory rather than the gate

## Open Questions

- Which exposed rows need stratified analysis instead of exclusion?
- How should policy effect diagnostics drive horizon review?

## Known Emergent Patterns

- [[Policy Becomes Invisible Truth]]
- [[Feedback Surfaces Are Also Contamination Surfaces]]
