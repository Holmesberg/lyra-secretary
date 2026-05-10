---
type: pattern
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Feedback Surfaces]]"
  - "[[Exposure Contamination]]"
  - "[[Tension - Helpfulness vs Contamination]]"
data_class: internal_architecture
---

# Feedback Surfaces Are Also Contamination Surfaces

## Pattern

Every user-facing mirror, nudge, prediction, or repair prompt is both product value and possible research contamination.

## Evidence

- Exposure Ledger contract covers predictions, nudges, insights, reflections, and repair prompts.

## Counter-Evidence

Some exposures may have negligible effect, but this must be modeled or measured rather than assumed.

## Related Tensions

- [[Tension - Helpfulness vs Contamination]]

## Related Domains

- [[Feedback Surfaces]]
- [[Exposure Ledger]]

## Interpretation

The product cannot be separated from the measurement environment.

## Risk

LyraOS optimizes itself into a self-reinforcing measurement loop.

## Next Watch Signal

Insight surfaces that do not dual-write to Exposure Ledger.
