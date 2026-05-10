---
type: decision
status: accepted
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/openclaw_orchestration_contract_v0.md
related:
  - "[[OpenClaw Runtime]]"
  - "[[Operator-Only Runtime]]"
  - "[[Tension - Operator Chaos vs Research Cleanliness]]"
data_class: internal_architecture
---

# Decision - OpenClaw Remains Operator Only

## Context

OpenClaw can decompose work, run agents, and summarize state, but agent traces are not user behavioral data.

## Decision

OpenClaw remains operator-only and outside Lyra product research data unless a successor contract admits operator-session analysis.

## Why

This preserves the product/research boundary and prevents agent output from becoming behavioral evidence.

## Consequences

- OpenClaw may inform implementation and vault understanding.
- OpenClaw must not create Lyra research labels.
- Operator traces remain distinct from user traces.

## Links

- [[Operator Chaos as Stress Test]]
- [[Tension - LLM Plausibility vs Ground Truth]]
- [[OpenClaw Runtime]]
