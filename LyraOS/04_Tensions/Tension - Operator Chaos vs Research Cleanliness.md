---
type: tension
status: active
confidence: medium
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/openclaw_orchestration_contract_v0.md
related_domains:
  - "[[OpenClaw Runtime]]"
  - "[[JARVIS]]"
related_decisions:
  - "[[Decision - OpenClaw Remains Operator Only]]"
related_patterns:
  - "[[Operator Chaos as Stress Test]]"
data_class: internal_architecture
---

# Tension - Operator Chaos vs Research Cleanliness

## Contradiction

Operator chaos is a useful stress test for cognitive continuity, but operator tooling is not normal user behavior.

## Why Both Sides Are Real

The operator is the harshest dogfood case. But treating operator traces as product research data would blur boundaries.

## Current Resolution

OpenClaw and JARVIS remain operator-only. Their outputs may inform implementation and vault understanding, not product research data.

## Failure Mode

Operator-specific failure modes get generalized into user claims.

## Watch Signals

- operator-session summaries entering Cortex
- vault notes turning operator stories into universal patterns without evidence
- OpenClaw traces used as behavioral labels
