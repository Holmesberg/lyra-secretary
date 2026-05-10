---
type: workstream
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - docs/cortex_product_research_contract_v0.md
  - backend/app/services/exposure_ledger.py
related:
  - "[[Exposure Ledger]]"
  - "[[Policy Becomes Invisible Truth]]"
  - "[[Cortex Gate Coverage]]"
data_class: internal_architecture
---

# Exposure Ledger v0 Rollout

## Goal

Make Exposure Ledger v0 the measurement-validity firewall for baseline inference.

## Current State

Decision, render, suppression, and policy effect tables exist. Attention proxies and temporal associations are deferred.

## Dependencies

- Cortex gate coverage
- legacy exposure adapters
- policy diagnostics

## Open Questions

- Which insight surfaces still need dual-write?
- Which exposed rows should later get stratified profiles?

## Risks

- Horizon policy becomes invisible truth.
- Legacy gaps create false `NONE`.

## Next Synthesis Checkpoint

Review policy effect logs and gate coverage after new exposure surfaces dual-write.
