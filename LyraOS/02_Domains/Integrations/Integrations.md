---
type: domain
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - archive/appstore/summary_of_app.md
related:
  - "[[Product Surface]]"
  - "[[Infrastructure]]"
  - "[[Tension - Automation vs Provenance]]"
data_class: internal_architecture
---

# Integrations

## What It Is

External system bridges for Google Calendar, Moodle, Notion, Telegram, and operator runtime connectivity.

## Why It Exists

Integrations reduce manual burden and make LyraOS fit into real schedules and workflows.

## Canonical Source Refs

- `backend/app/services/calendar_sync.py`
- `backend/app/services/moodle_ics_sync.py`
- `backend/app/services/moodle_submissions_sync.py`
- `backend/app/services/notion_client.py`

## Related Concepts

- [[Automation Helps Only If It Preserves Provenance]]
- [[User Burden Surface]]
- [[Operator-Only Runtime]]

## Active Risks

- Imported data lacks context.
- External credentials remain security debt.
- Automation looks observed when it is imported or inferred.

## Open Questions

- Which imported events can ever become baseline evidence?

## Known Emergent Patterns

- [[Automation Helps Only If It Preserves Provenance]]
