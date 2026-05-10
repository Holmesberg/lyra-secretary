---
type: workstream
status: active
confidence: medium
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - archive/appstore/summary_of_app.md
related:
  - "[[Product Surface]]"
  - "[[Governance]]"
  - "[[Evidence Index]]"
data_class: internal_architecture
---

# Legal and Privacy Readiness

## Goal

Make privacy, consent, and hosted-model disclosure match actual system behavior.

## Current State

Legal pages are known debt. Some credentials remain plaintext. Hosted LLM paths are operator-scoped.

## Dependencies

- privacy policy
- terms
- data handling disclosure
- redaction rules

## Open Questions

- Which logs are user-exportable?
- Which operator-only data paths need disclosure?

## Risks

- Vault redacted evidence accidentally preserves identifying structure.

## Next Synthesis Checkpoint

Review [[Evidence Index]] rules against legal copy.
