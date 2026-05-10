---
type: counterfactual
status: active
confidence: low
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - archive/appstore/summary_of_app.md
related:
  - "[[JARVIS]]"
  - "[[Tension - Frictionless UX vs Measurable Behavior]]"
  - "[[Tension - LLM Plausibility vs Ground Truth]]"
data_class: internal_architecture
---

# Counterfactual - Synchronous LLM Enrichment

## Alternative World

LLM enrichment happens in the task creation path rather than asynchronously.

## Expected Benefit

Users may see richer suggestions immediately.

## Expected Harm

Latency and plausibility pressure increase; user-visible state may feel model-authored.

## What Current Architecture Assumes

Fast deterministic creation is more important than rich immediate enrichment.

## What Evidence Could Change The Assumption

Strong retention or correction gains with low latency and clear provenance.

## Related Tensions

- [[Tension - Frictionless UX vs Measurable Behavior]]
- [[Tension - LLM Plausibility vs Ground Truth]]
