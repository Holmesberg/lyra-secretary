---
type: domain
status: active
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - archive/appstore/summary_of_app.md
  - docs/architecture.md
related:
  - "[[Data Flow Map]]"
  - "[[Integrations]]"
  - "[[OpenClaw Runtime]]"
data_class: internal_architecture
---

# Infrastructure

## What It Is

The runtime substrate: Docker Compose, Supabase Postgres, Redis, APScheduler, Cloudflare Tunnel, and external service bridges.

## Why It Exists

LyraOS currently runs as a dogfood product with real operational dependencies but remains pre-alpha.

## Canonical Source Refs

- `docker-compose.yml`
- `docs/architecture.md`
- `archive/appstore/summary_of_app.md`

## Related Concepts

- [[Retention as Research Constraint]]
- [[Tension - Automation vs Provenance]]
- [[Operator-Only Runtime]]

## Active Risks

- Operator-host tunnel is an operational floor.
- Redis hot state and Postgres durable state can diverge.
- Background jobs can create state that looks user-driven.

## Open Questions

- What hosting boundary should replace operator-host tunneling?

## Known Emergent Patterns

- [[Automation Helps Only If It Preserves Provenance]]
