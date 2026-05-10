---
type: tension
status: active
confidence: medium
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Tension Index]]"
  - "[[Self Model]]"
  - "[[Measurement Validity]]"
  - "[[Decision Index]]"
data_class: internal_architecture
---

# Tension Graph

## Central Tension Cluster

```text
Measurement Validity
        |
        v
Frictionless UX <-> Measurable Behavior
        |
        v
Helpfulness <-> Contamination
        |
        v
Policy Simplicity <-> Contamination Fidelity
```

## Operator Tension Cluster

```text
Automation <-> Provenance
        |
        v
LLM Plausibility <-> Ground Truth
        |
        v
Operator Chaos <-> Research Cleanliness
```

## Interpretation Rule

Do not resolve a tension by forgetting one side. Link decisions to the tension they are holding.

## Recursive Rule

The [[Self Model]] watches whether the graph is still organized around [[Measurement Validity]] or whether an implementation mechanism has become the accidental center.
