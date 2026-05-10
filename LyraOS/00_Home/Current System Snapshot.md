---
type: review
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - archive/appstore/summary_of_app.md
  - MANIFESTO.md
  - docs/cortex_product_research_contract_v0.md
related:
  - "[[LyraOS System Map]]"
  - "[[Measurement Validity]]"
  - "[[Self Model]]"
  - "[[Exposure Ledger]]"
data_class: internal_architecture
---

# Current System Snapshot

LyraOS is currently a pre-alpha dogfood system with a low-friction scheduling and execution product, a research-grade behavioral measurement layer, and operator-only AI runtime surfaces.

## Current Shape

- Product layer: Next.js app, task lifecycle, stopwatch, calendar, deadlines, insights, settings.
- Backend layer: FastAPI, SQLAlchemy, Supabase Postgres, Redis, APScheduler.
- Research layer: Cortex canonical metrics, clean-data profiles, bias factor, pause/resume prediction, archetype proximity.
- Validity layer: Exposure Ledger v0 fails closed for baseline inference.
- Operator layer: JARVIS and OpenClaw remain operator-only unless future contracts say otherwise.

## Current Doctrine

- [[Measurement Validity]]
- [[Epistemic Core]]
- [[Mirror Do Not Judge]]
- [[Fail-Closed Unknown]]
- [[Measurement Validity Firewall]]
- [[Retention as Research Constraint]]
- [[Operator-Only Runtime]]

## Active Pressure

- [[Tension - Frictionless UX vs Measurable Behavior]]
- [[Tension - Automation vs Provenance]]
- [[Tension - Helpfulness vs Contamination]]
- [[Tension - Policy Simplicity vs Contamination Fidelity]]
