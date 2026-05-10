---
type: hypothesis
status: active
confidence: medium
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Exposure Contamination]]"
  - "[[System-Induced Signal]]"
  - "[[Feedback Surfaces Are Also Contamination Surfaces]]"
data_class: internal_architecture
---

# Insight Exposure Changes Self-Reporting Behavior

## Claim

Insights about readiness, reflection, or calibration may change future self-report behavior.

## Observable Signals

- readiness distributions change after meta-inference exposure
- reflection completion or dwell changes after insight display
- calibration improves only after insight exposure

## Counter-Signals

- no change after exposure windows
- comparable change in unexposed or withheld groups

## Clean-Data Requirements

Self-report analyses must check relevant exposure targets.

## Exposure Risks

The system may measure changed reporting behavior, not changed cognition.

## Related Patterns

- [[Feedback Surfaces Are Also Contamination Surfaces]]
- [[Policy Becomes Invisible Truth]]
