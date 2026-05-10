---
type: decision
status: accepted
confidence: high
created: 2026-05-10
updated: 2026-05-10
last_reviewed: 2026-05-10
source_refs:
  - archive/appstore/summary_of_app.md
related:
  - "[[How To Use This Vault]]"
  - "[[Home]]"
  - "[[Tension - Automation vs Provenance]]"
data_class: internal_architecture
---

# Decision - Vault Stores Understanding Not Truth

## Context

LyraOS already has code and repo docs as canonical sources. A vault can add value only if it does something different.

## Decision

The vault stores interpretation, relationships, tensions, drift, and redacted evidence. It does not define canonical implementation truth.

## Why

This avoids creating a second source of truth while making the system more human-readable.

## Consequences

- Source refs are required.
- Repo docs remain canonical.
- Vault insights can graduate into repo docs when they become doctrine.

## Links

- [[How To Use This Vault]]
- [[Tension - Automation vs Provenance]]
- [[Stable Interpretation of Unstable Behavior]]
