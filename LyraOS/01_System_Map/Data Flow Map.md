---
type: domain
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - archive/appstore/summary_of_app.md
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Cortex]]"
  - "[[Exposure Ledger]]"
  - "[[Clean Data Profile]]"
data_class: internal_architecture
---

# Data Flow Map

## Baseline Flow

```text
Product action -> raw event/table row -> Cortex projection -> exposure check -> clean-data profile -> inference
```

## Feedback Flow

```text
Inference or rule -> user-visible mirror/nudge -> Exposure Ledger -> later behavior cannot be assumed baseline
```

## Failure Mode

If exposure checking is skipped, LyraOS may learn from behavior it helped create.

## Related

- [[Exposure Ledger as Causal Firewall]]
- [[Baseline Cleanliness]]
- [[System-Induced Signal]]
