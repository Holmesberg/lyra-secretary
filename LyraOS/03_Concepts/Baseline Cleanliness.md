---
type: concept
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-12
last_reviewed: 2026-05-12
source_refs:
  - docs/cortex_product_research_contract_v0.md
  - docs/layered_epistemic_architecture.md
related:
  - "[[Layered Epistemic Architecture]]"
  - "[[Epistemic Core]]"
  - "[[Measurement Validity]]"
  - "[[Self Model]]"
  - "[[Exposure Ledger]]"
  - "[[Fail-Closed Unknown]]"
  - "[[Clean Data Profile]]"
data_class: internal_architecture
---

# Baseline Cleanliness

## Definition

A measurement is baseline-clean only when exposure context was evaluated and returned `NONE` for the relevant signal target under the current policy.

Baseline cleanliness is one admissibility state inside [[Measurement Validity]], not a universal truth label.

[[Layered Epistemic Architecture]] makes baseline cleanliness layer-dependent: a row may be valid for descriptive history while being invalid for clean behavioral inference.

## Why It Matters

Clean is not default. Missing evidence does not make data safe.

## What Clean Does Mean

- exposure context was checked
- horizon policy was available
- relevant legacy exposure sources were checked
- no relevant rendered exposure or intervention was found in the policy window

## What Clean Does Not Mean

- the behavior is true in a metaphysical sense
- no ambient measurement effect exists
- no unmodeled exposure mattered
- the row is valid for every research purpose

## Consequences

- Cleanliness is always tied to a signal target and policy version.
- A row can be clean for one analysis and unsafe for another.
- Clean status can drift when policy changes.

## Where It Appears

- Cortex clean-data helpers
- Exposure Ledger gate
- bias factor, pause learning, archetype evidence

## Failure Mode

Post-exposure behavior gets treated as naturalistic behavior.

## Failure Modes To Watch

- `NONE` described as "uncontaminated" without policy context
- clean-data profile names omitted from analysis outputs
- exposed rows included because they are useful or numerous
- missing exposure data treated as absence of exposure

## Related Tensions

- [[Tension - Helpfulness vs Contamination]]
- [[Tension - Policy Simplicity vs Contamination Fidelity]]
