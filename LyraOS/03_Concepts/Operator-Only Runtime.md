---
type: concept
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/openclaw_orchestration_contract_v0.md
related:
  - "[[OpenClaw Runtime]]"
  - "[[JARVIS]]"
  - "[[Tension - Operator Chaos vs Research Cleanliness]]"
data_class: internal_architecture
---

# Operator-Only Runtime

## Definition

An AI or automation surface used for operator work, not user-facing product behavior or research data by default.

## Why It Matters

Operator tooling can generate useful synthesis, but it must not silently create product claims or research labels.

## Where It Appears

- OpenClaw
- JARVIS
- Telegram operator notifications
- vault synthesis workflows

## Failure Mode

Operator traces become treated as user behavioral data.

## Related Tensions

- [[Tension - Operator Chaos vs Research Cleanliness]]
- [[Tension - LLM Plausibility vs Ground Truth]]
