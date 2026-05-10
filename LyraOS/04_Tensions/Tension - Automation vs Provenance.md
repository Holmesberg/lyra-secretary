---
type: tension
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
  - docs/openclaw_orchestration_contract_v0.md
related_domains:
  - "[[Integrations]]"
  - "[[OpenClaw Runtime]]"
related_decisions:
  - "[[Decision - Vault Stores Understanding Not Truth]]"
related_patterns:
  - "[[Automation Helps Only If It Preserves Provenance]]"
data_class: internal_architecture
---

# Tension - Automation vs Provenance

## Contradiction

Automation reduces burden, but it can obscure source, timing, agency, and uncertainty.

## Why Both Sides Are Real

Manual tracking collapses under load. Unlabeled automation creates false observations.

## Current Resolution

Automation may create candidates, imported events, and repair proposals, but provenance must remain explicit.

## Failure Mode

System-generated state is mistaken for user-observed behavior.

## Watch Signals

- auto-written rows lacking provenance
- generated vault notes promoted without source refs
- repair candidates treated as measured transitions
