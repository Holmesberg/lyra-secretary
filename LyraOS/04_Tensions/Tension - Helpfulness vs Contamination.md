---
type: tension
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
related_domains:
  - "[[Feedback Surfaces]]"
  - "[[Exposure Ledger]]"
related_decisions:
  - "[[Decision - Exposure Ledger Fails Closed]]"
related_patterns:
  - "[[Feedback Surfaces Are Also Contamination Surfaces]]"
data_class: internal_architecture
---

# Tension - Helpfulness vs Contamination

## Contradiction

The system helps users by showing insights, but those insights can contaminate future baseline measurements.

## Why Both Sides Are Real

Feedback is the product's value loop. Feedback also changes the measurement environment.

## Current Resolution

User-visible feedback is allowed, but later baseline inference must query exposure context and fail closed.

## Failure Mode

LyraOS learns from improvements or changes it caused and calls them natural patterns.

## Watch Signals

- new mirrors without exposure events
- high exposed rate in policy diagnostics
- insight exposure followed by changed self-report behavior
