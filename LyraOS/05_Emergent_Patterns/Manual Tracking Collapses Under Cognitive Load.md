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
  - "[[Human-in-the-Loop Repair]]"
  - "[[Redacted Evidence - Forgotten Timer During OpenClaw Wiring]]"
  - "[[Tension - Frictionless UX vs Measurable Behavior]]"
data_class: internal_architecture
---

# Manual Tracking Collapses Under Cognitive Load

## Pattern

Manual lifecycle instrumentation decays when work becomes exploratory, multi-threaded, interrupted, or emotionally charged.

## Evidence

- [[Redacted Evidence - Forgotten Timer During OpenClaw Wiring]]
- Observability repair doctrine in `docs/cortex_product_research_contract_v0.md`

## Counter-Evidence

Simple deterministic tasks may remain well-tracked with ordinary timers.

## Related Tensions

- [[Tension - Frictionless UX vs Measurable Behavior]]
- [[Tension - Automation vs Provenance]]

## Related Domains

- [[Task Execution]]
- [[Product Surface]]

## Interpretation

LyraOS should recover from forgetfulness rather than assume users are reliable instrumentation devices.

## Risk

Repair logic can contaminate baseline if confirmed repairs are treated like real-time observation.

## Next Watch Signal

Rate of missing lifecycle repair candidates during high-context work.
