---
type: domain
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
  - "[[Measurement Validity]]"
  - "[[Self Model]]"
  - "[[Cortex]]"
  - "[[Exposure Ledger]]"
  - "[[Baseline Cleanliness]]"
  - "[[Fail-Closed Unknown]]"
  - "[[Policy as Hypothesis]]"
data_class: internal_architecture
---

# Epistemic Core

This is the routing map for LyraOS measurement validity. It is not the deepest center; that role belongs to [[Measurement Validity]]. The core exists to keep implementation mechanisms, policies, profiles, and tensions connected without letting any one mechanism become the whole theory.

## Center Of Gravity

[[Measurement Validity]] is the principle. The notes below are mechanisms, constraints, and failure detectors that protect it.

## Core Chain

```text
Measurement Validity
-> Product event provenance
-> Cortex canonicalization
-> Exposure Ledger gate
-> Clean-data profile
-> Baseline inference or descriptive-only use
```

## Core Mechanisms

| Note | Role | Failure if weak |
| --- | --- | --- |
| [[Cortex]] | canonicalizes behavioral measurements | metrics drift into mixed spaces |
| [[Exposure Ledger]] | operational gate for system-induced contamination | the mechanism becomes mistaken for the principle |
| [[Baseline Cleanliness]] | defines when data can be treated as baseline | clean becomes default instead of proven |
| [[Fail-Closed Unknown]] | blocks silent inference from missing context | unknown becomes neutral |
| [[Measurement Validity Firewall]] | names the boundary around baseline claims | analytics replaces epistemic enforcement |
| [[Policy as Hypothesis]] | keeps horizon policy auditable | policy becomes invisible truth |
| [[Clean Data Profile]] | scopes valid data by analysis purpose | descriptive rows become training rows |
| [[Tension - Policy Simplicity vs Contamination Fidelity]] | preserves the central policy contradiction | horizon policy overfits or under-protects |

## Non-Negotiable Invariants

- Baseline is not default; it is certified.
- `UNKNOWN` is a blocking state, not a soft maybe.
- Clean means no detected exposure under current policy, not metaphysical truth.
- Cortex does not write truth; it projects and filters.
- Exposure Ledger does not prove causality; it prevents false baseline claims.
- Horizon policy is a hypothesis that must remain visible through diagnostics.
- The [[Self Model]] must notice when the core itself starts drifting.

## Review Questions

- Did any inference path bypass exposure context?
- Did any note call data clean without naming the policy boundary?
- Did any model output become a fact without source evidence?
- Did a product recovery affordance create research evidence by accident?
- Did a policy effect change without a drift entry?
- Did Exposure Ledger become the conceptual center instead of the operational gate?
- Did the [[Self Model]] register any change in what LyraOS thinks it is becoming?

## Related

- Tension cluster: [[Tension Graph]]
- Recursive watcher: [[Self Model]]
- Drift tracking: [[Interpretation Drift Log]]
- Evidence base: [[Evidence Index]]
