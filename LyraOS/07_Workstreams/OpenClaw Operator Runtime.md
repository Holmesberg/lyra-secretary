---
type: workstream
status: active
confidence: medium
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/openclaw_orchestration_contract_v0.md
related:
  - "[[OpenClaw Runtime]]"
  - "[[Operator Chaos as Stress Test]]"
  - "[[Tension - Operator Chaos vs Research Cleanliness]]"
data_class: internal_architecture
---

# OpenClaw Operator Runtime

## Goal

Use OpenClaw for implementation, adversarial review, exploration, synthesis, and memory without crossing product research boundaries.

## Current State

OpenClaw is wired with Kimi, Codex, Gemini, and role-specific agents.

## Dependencies

- orchestration contract
- operator-only boundary
- provenance-preserving summaries

## Open Questions

- Which operator-session traces should be summarized in the vault?

## Risks

- Agent disagreement gets compressed into consensus.
- Operator traces are generalized too broadly.

## Next Synthesis Checkpoint

Review OpenClaw outputs for conflict logs and uncertainty maps.
