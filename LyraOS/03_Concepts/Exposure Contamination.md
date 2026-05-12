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
  - "[[Exposure Ledger]]"
  - "[[System-Induced Signal]]"
  - "[[Feedback Surfaces]]"
data_class: internal_architecture
---

# Exposure Contamination

## Definition

The possibility that a user-visible system output affected later behavior or self-report, making that later measurement unsafe as natural baseline.

In [[Layered Epistemic Architecture]], outputs are not a truth layer. They are a contamination boundary between internal inference and user perception.

## Why It Matters

LyraOS shows mirrors, predictions, and repair prompts. These can change the same behavior the system later tries to learn from.

## Where It Appears

- feedback surfaces
- pause/resume predictions
- creation nudges
- repair prompts

## Failure Mode

The system learns from behavior it helped induce.

## Related Tensions

- [[Tension - Helpfulness vs Contamination]]
- [[Tension - Frictionless UX vs Measurable Behavior]]
