---
type: tension
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/openclaw_orchestration_contract_v0.md
  - docs/cortex_product_research_contract_v0.md
related_domains:
  - "[[JARVIS]]"
  - "[[OpenClaw Runtime]]"
related_decisions:
  - "[[Decision - Temporal Association Must Not Be Causal Language]]"
related_patterns:
  - "[[Stable Interpretation of Unstable Behavior]]"
data_class: internal_architecture
---

# Tension - LLM Plausibility vs Ground Truth

## Contradiction

LLMs are useful at synthesis but can make uncertain structures feel settled.

## Why Both Sides Are Real

LyraOS benefits from synthesis, adversarial review, and exploration. But plausible language can collapse uncertainty.

## Current Resolution

Agent output must preserve confidence, alternatives, provenance, and disagreement.

## Failure Mode

Narrative quality becomes mistaken for evidence quality.

## Watch Signals

- agent summaries without source refs
- missing uncertainty maps
- model-generated labels used as observed facts
