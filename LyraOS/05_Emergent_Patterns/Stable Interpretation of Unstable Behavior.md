---
type: pattern
status: active
confidence: medium
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Interpretation Drift Log]]"
  - "[[Self Model]]"
  - "[[Tension - LLM Plausibility vs Ground Truth]]"
data_class: internal_architecture
---

# Stable Interpretation of Unstable Behavior

## Pattern

The system is tempted to keep old interpretations after behavior, context, or instrumentation has changed.

## Evidence

- Exposure Ledger was introduced because baseline interpretation changed after recognizing system-induced signal.
- Repair prompts changed the meaning of timer truth.

## Counter-Evidence

Strong contracts and drift logs can preserve interpretation history.

## Related Tensions

- [[Tension - LLM Plausibility vs Ground Truth]]
- [[Tension - Policy Simplicity vs Contamination Fidelity]]

## Related Domains

- [[Governance]]
- [[Self Model]]

## Interpretation

The vault must track changes in meaning, not just changes in architecture.

## Risk

Old explanations continue to guide new decisions after their assumptions fail.

## Next Watch Signal

Architecture updates without matching drift entries.
