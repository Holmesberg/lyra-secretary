---
type: concept
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - MANIFESTO.md
  - docs/cortex_contract_v0.md
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Epistemic Core]]"
  - "[[Self Model]]"
  - "[[Cortex]]"
  - "[[Exposure Ledger]]"
  - "[[Baseline Cleanliness]]"
  - "[[Policy as Hypothesis]]"
data_class: internal_architecture
---

# Measurement Validity

## Definition

Measurement validity is the system's ability to say what a behavioral measurement can and cannot support without laundering product behavior, model output, repair state, or missing context into baseline truth.

## Why It Matters

This is the true center of the LyraOS epistemic graph. Exposure Ledger, Cortex, clean-data profiles, fail-closed unknowns, and horizon policies are mechanisms that protect measurement validity. They are not the principle itself.

## What It Requires

- raw events keep provenance
- derived metrics remain derived
- inferred labels remain hypotheses
- exposure context is evaluated before baseline learning
- unknowns block unsafe claims
- policy versions stay visible
- drift in interpretation is logged

## Implementing Mechanisms

- [[Cortex]] canonicalizes metrics and clean-data profiles.
- [[Exposure Ledger]] evaluates system-induced contamination.
- [[Baseline Cleanliness]] defines policy-relative baseline admissibility.
- [[Fail-Closed Unknown]] prevents missing context from becoming clean.
- [[Policy as Hypothesis]] keeps gate policy auditable.
- [[Measurement Validity Firewall]] names the enforcement boundary.

## What It Does Not Mean

- It does not prove behavior is objectively true.
- It does not prove no unmodeled contamination exists.
- It does not make a policy correct.
- It does not authorize causal claims from temporal association.

## Failure Modes

- A mechanism becomes the conceptual center.
- Clean means "no detected problem" but is described as "true."
- Policy becomes invisible truth.
- Product recovery becomes research evidence.
- LLM synthesis turns uncertainty into narrative confidence.

## Recursive Watch

[[Self Model]] watches whether LyraOS still understands itself as a measurement-validity system or has drifted into productivity tooling, behavioral optimization, or AI-generated certainty.

## Related Tensions

- [[Tension - Policy Simplicity vs Contamination Fidelity]]
- [[Tension - Helpfulness vs Contamination]]
- [[Tension - LLM Plausibility vs Ground Truth]]
