---
type: domain
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - archive/appstore/summary_of_app.md
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[Product Surface]]"
  - "[[Task Execution]]"
  - "[[Feedback Surfaces]]"
data_class: internal_architecture
---

# Product Layer Map

The product layer helps users plan, execute, recover, and return with minimal cognitive overhead.

## Owns

- task creation and scheduling
- stopwatch state transitions
- deadlines and integrations
- feedback surfaces
- recovery affordances

## Must Preserve

- user flow
- low burden
- provenance
- deterministic state transitions

## Must Not Do

- add research prompts for convenience
- present latent states as facts
- optimize user behavior to make models look accurate

## Related

- [[Tension - Frictionless UX vs Measurable Behavior]]
- [[User Burden Surface]]
- [[Retention as Research Constraint]]
