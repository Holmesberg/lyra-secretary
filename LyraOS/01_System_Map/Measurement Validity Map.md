---
type: domain
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-12
last_reviewed: 2026-05-12
source_refs:
  - docs/cortex_product_research_contract_v0.md
  - docs/cortex_contract_v0.md
  - docs/layered_epistemic_architecture.md
related:
  - "[[Layered Epistemic Architecture]]"
  - "[[Measurement Validity]]"
  - "[[Self Model]]"
  - "[[Measurement Validity Firewall]]"
  - "[[Fail-Closed Unknown]]"
  - "[[Exposure Ledger]]"
data_class: internal_architecture
---

# Measurement Validity Map

Measurement validity depends on keeping observed, derived, inferred, exposed, repaired, and unknown states distinct.

## Abstract Center

The abstract center is [[Measurement Validity]]. Cortex and Exposure Ledger are mechanisms that protect it, not replacements for it.

## Validity Stack

```text
Raw event -> layer classification -> provenance -> Cortex metric -> exposure context -> clean-data profile -> interpretation
```

## Guardrails

- Unknown is not neutral.
- Clean is policy-relative.
- Exposure policy is a hypothesis.
- Repair prompts are interventions.
- Derived metrics are recomputed at read time.
- Contradictions between layers are preserved before they are interpreted.

## Related

- [[Policy as Hypothesis]]
- [[Causal Firewall]]
- [[Epistemic Core]]
- [[Tension - Policy Simplicity vs Contamination Fidelity]]
