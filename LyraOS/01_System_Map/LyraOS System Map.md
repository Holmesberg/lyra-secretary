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
  - "[[Measurement Validity]]"
  - "[[Self Model]]"
  - "[[Product Layer Map]]"
  - "[[Research Layer Map]]"
  - "[[Operator Runtime Map]]"
data_class: internal_architecture
---

# LyraOS System Map

LyraOS is a product-research system. The product helps users plan, execute, recover, and return. The research layer interprets behavior only under explicit provenance, exposure, and clean-data constraints.

## Core Flow

```text
User -> Product Surface -> Event Stream -> Cortex -> Exposure Ledger Gate -> Inference -> Mirrors
```

## Major Subsystems

- [[Measurement Validity]]
- [[Epistemic Core]]
- [[Product Surface]]
- [[Task Execution]]
- [[Cortex]]
- [[Exposure Ledger]]
- [[Feedback Surfaces]]
- [[JARVIS]]
- [[OpenClaw Runtime]]
- [[Governance]]

## Boundaries

- Product creates behavior.
- Research interprets behavior.
- Operator tooling does not become product research data by default.
- Vault stores understanding, not source truth.
