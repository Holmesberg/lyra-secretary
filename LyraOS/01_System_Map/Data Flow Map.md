---
type: domain
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-12
last_reviewed: 2026-05-12
source_refs:
  - archive/appstore/summary_of_app.md
  - docs/cortex_product_research_contract_v0.md
  - docs/layered_epistemic_architecture.md
related:
  - "[[Layered Epistemic Architecture]]"
  - "[[Cortex]]"
  - "[[Exposure Ledger]]"
  - "[[Clean Data Profile]]"
data_class: internal_architecture
---

# Data Flow Map

## Baseline Flow

```text
Product action -> raw event/table row -> layer classification -> Cortex projection -> exposure check -> clean-data profile -> inference
```

## Feedback Flow

```text
Inference or rule -> output-surface registry -> user-visible mirror/nudge -> Exposure Ledger -> later behavior cannot be assumed baseline
```

## Layer Router

[[Layered Epistemic Architecture]] decides whether a row is observed behavior, a derived metric, an interpretation, self-report, or an output exposure before it is allowed to feed downstream inference.

## Mixed-Row Projection Rule

Analytics reads the projection chosen by the clean-data profile. Product UI
reads `descriptive_history` by default. Training and clean baselines read only
profile-approved projections such as `raw_observed`,
`correction_adjusted_effective`, `external_submission_trace`,
`repair_prompt_result`, or `diagnostic_projection`.

## Failure Mode

If exposure checking is skipped, LyraOS may learn from behavior it helped create.

## Related

- [[Exposure Ledger as Causal Firewall]]
- [[Baseline Cleanliness]]
- [[System-Induced Signal]]
