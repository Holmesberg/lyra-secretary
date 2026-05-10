---
type: hypothesis
status: active
confidence: medium
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Human-in-the-Loop Repair]]"
  - "[[Decision - Repair Prompts Are Interventions]]"
  - "[[Manual Tracking Collapses Under Cognitive Load]]"
data_class: internal_architecture
---

# Repair Prompts Improve Continuity But Contaminate Baseline

## Claim

Repair prompts can improve product continuity while making default baseline learning unsafe.

## Observable Signals

- users confirm missing transitions
- fewer abandoned or inconsistent sessions
- repaired rows increase after high-context workflows

## Counter-Signals

- prompts are ignored or dismissed
- prompt frequency harms retention

## Clean-Data Requirements

Repaired durations are not default measured-execution rows.

## Exposure Risks

The prompt itself changes attention and task framing.

## Related Patterns

- [[Manual Tracking Collapses Under Cognitive Load]]
- [[User Recovery Affordances Create Research Boundary Pressure]]
