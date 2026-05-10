---
type: counterfactual
status: active
confidence: medium
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Exposure Ledger]]"
  - "[[Baseline Cleanliness]]"
  - "[[Tension - Helpfulness vs Contamination]]"
data_class: internal_architecture
---

# Counterfactual - Exposure Ledger Disabled

## Alternative World

LyraOS continues learning from post-exposure behavior without a baseline gate.

## Expected Benefit

More rows remain available for adaptive models.

## Expected Harm

Inference learns from behavior the system may have induced.

## What Current Architecture Assumes

False clean is worse than losing some data.

## What Evidence Could Change The Assumption

Reliable causal analysis showing specific exposure classes do not affect specific targets.

## Related Tensions

- [[Tension - Helpfulness vs Contamination]]
- [[Tension - Policy Simplicity vs Contamination Fidelity]]
