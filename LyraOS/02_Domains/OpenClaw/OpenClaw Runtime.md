---
type: domain
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/openclaw_orchestration_contract_v0.md
related:
  - "[[Operator Runtime Map]]"
  - "[[Operator-Only Runtime]]"
  - "[[Tension - Operator Chaos vs Research Cleanliness]]"
data_class: internal_architecture
---

# OpenClaw Runtime

## What It Is

OpenClaw is the operator-only multi-agent orchestration runtime for LyraOS work.

## Why It Exists

It decomposes tasks, runs implementation and adversarial agents, preserves disagreement, and summarizes local memory for operator work.

## Canonical Source Refs

- `docs/openclaw_orchestration_contract_v0.md`
- `openclaw/`

## Related Concepts

- [[Operator-Only Runtime]]
- [[Observed vs Derived vs Inferred]]
- [[Tension - LLM Plausibility vs Ground Truth]]

## Active Risks

- Agent output becomes treated as research data.
- Synthesis hides disagreement.
- Operator-session traces are over-read as user behavior.

## Open Questions

- What operator-session analysis would require a successor contract?

## Known Emergent Patterns

- [[Operator Chaos as Stress Test]]
- [[Automation Helps Only If It Preserves Provenance]]
