---
type: domain
status: active
confidence: medium
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - archive/appstore/summary_of_app.md
related:
  - "[[Operator Runtime Map]]"
  - "[[Operator-Only Runtime]]"
  - "[[Tension - LLM Plausibility vs Ground Truth]]"
data_class: internal_architecture
---

# JARVIS

## What It Is

JARVIS is an operator-only in-app AI assistant with read tools, confirmation-gated write tools, and behavioral query capabilities.

## Why It Exists

It helps the operator inspect, summarize, and manipulate LyraOS without turning LLM output into unreviewed product logic.

## Canonical Source Refs

- `backend/app/api/v1/endpoints/jarvis.py`
- `backend/app/services/jarvis_agent.py`
- `backend/app/services/jarvis_tools.py`

## Related Concepts

- [[Operator-Only Runtime]]
- [[Temporal Association Is Not Causality]]
- [[System-Induced Signal]]

## Active Risks

- Tool outputs become over-trusted.
- Write confirmations are treated as sufficient governance.
- Pattern summaries are mistaken for validated research claims.

## Open Questions

- Which JARVIS outputs should be summarized into source digests vs discarded?

## Known Emergent Patterns

- [[Automation Helps Only If It Preserves Provenance]]
- [[Stable Interpretation of Unstable Behavior]]
