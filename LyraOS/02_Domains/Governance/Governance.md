---
type: domain
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - MANIFESTO.md
  - docs/cortex_product_research_contract_v0.md
  - docs/openclaw_orchestration_contract_v0.md
related:
  - "[[Decision Index]]"
  - "[[Tension Index]]"
  - "[[Self Model]]"
data_class: internal_architecture
---

# Governance

## What It Is

The contracts, manifesto rules, and review practices that prevent LyraOS from turning plausible behavior into ungrounded claims.

## Why It Exists

LyraOS blends product, behavioral research, and AI assistance. Governance keeps these layers from silently defining each other.

## Canonical Source Refs

- `MANIFESTO.md`
- `docs/cortex_product_research_contract_v0.md`
- `docs/openclaw_orchestration_contract_v0.md`

## Related Concepts

- [[Observed vs Derived vs Inferred]]
- [[Policy as Hypothesis]]
- [[Fail-Closed Unknown]]

## Active Risks

- Contract drift.
- Decision rationale lost after implementation.
- Vault synthesis mistaken for canonical doctrine.

## Open Questions

- Which vault insights should graduate into repo docs?

## Known Emergent Patterns

- [[Stable Interpretation of Unstable Behavior]]
- [[Unknown Must Remain Structurally Expensive]]
