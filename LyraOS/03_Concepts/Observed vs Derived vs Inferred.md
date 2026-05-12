---
type: concept
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-12
last_reviewed: 2026-05-12
source_refs:
  - MANIFESTO.md
  - docs/cortex_product_research_contract_v0.md
  - docs/layered_epistemic_architecture.md
related:
  - "[[Layered Epistemic Architecture]]"
  - "[[Cortex]]"
  - "[[Fail-Closed Unknown]]"
  - "[[Governance]]"
data_class: internal_architecture
---

# Observed vs Derived vs Inferred

## Definition

Observed values are directly captured system traces. Self-reported values are user narrative or priors. Derived values are computed from declared inputs. Inferred values are hypotheses and must remain labeled as such.

[[Layered Epistemic Architecture]] extends this distinction into four routing layers: observed behavior, behavioral metrics, interpretive models, and self-reported priors/corrections.

## Why It Matters

LyraOS loses validity if derived metrics or hypotheses become stored as truth.

## Where It Appears

- Cortex event envelopes
- OpenClaw uncertainty maps
- vault redacted evidence notes

## Failure Mode

Inference hardens into identity or behavioral fact.

## Related Tensions

- [[Tension - LLM Plausibility vs Ground Truth]]
- [[Tension - Automation vs Provenance]]
