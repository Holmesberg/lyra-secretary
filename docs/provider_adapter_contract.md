# Provider Adapter Contract

**Status:** Scalability contract.
**Created:** 2026-05-18.
**Purpose:** Freeze the provider-ingestion boundary before Baseet, Moodle,
calendar, Jira/Linear, or future structured environments expand the substrate.
**Governance:** Subordinate to `MANIFESTO.md`, `docs/academic_execution_substrate.md`,
`docs/cortex_contract_v0.md`, and `docs/prodblueprint_security.md`.

This document authorizes no new provider feature. It defines the normalization
contract that must exist before provider-specific data reaches Cortex,
clean-data profiles, adaptive scheduling, or stronger research claims.

---

## 1. Boundary

Provider-specific code may live in:

- provider adapters,
- provider connection settings,
- provider-native UI surfaces,
- import/sync jobs,
- redaction/audit helpers,
- and provider-specific trust-state explanations.

Provider-specific logic must not live in:

- Cortex,
- clean-data admission,
- adaptive scheduling,
- exposure truth authority,
- calibration queries,
- or behavioral inference services.

The rule:

```text
Adapters translate local dialects.
Core reasons in provider-blind primitives.
Surfaces translate results back into local dialects.
```

## 2. Normalized Provider Facts

Every provider import must normalize into substrate facts before downstream
consumption.

Minimum normalized fields:

| Field | Rule |
| --- | --- |
| `provider` | Source label for provenance only. Not an inference branch. |
| `provider_item_type` | Local type such as assignment, lecture, ticket, event. |
| `external_id_hash` | Stable, non-raw identifier. Raw URLs/tokens forbidden. |
| `user_id` | Required before persistence or user-visible reads. |
| `occurred_at` / `due_at_utc` | Use only when actually provided or derived with provenance. |
| `title` | User-visible label; avoid using it as truth authority. |
| `evidence_class` | Usually `external_obligation` or `passive_activity`. |
| `provenance` | `external_import`, `provider_reachable`, `self_reported`, etc. |
| `trust_state` | Provider reachability/authority state. |
| `raw_authority_level` | Whether the source is exact, reachable, stale, denied, unknown. |
| `redaction_status` | Must prove tokens/URLs/payloads were removed. |

The normalized record may preserve provider vocabulary for display, but the
core must consume the normalized evidence class and substrate primitive.

## 3. Required Primitives

Adapters must translate into these provider-blind primitives where applicable:

```text
obligation
intention
execution_event
outcome
interruption
exposure
drift
recalibration
```

Provider imports usually create obligations or weak activity traces. They do
not create planning calibration unless the user accepted or confirmed an
intention.

## 4. Provider Failure Invariant

Provider failure must degrade functionality, not weaken authentication or user
scoping.

Examples:

- Moodle auth failure disables Moodle context for that user; it does not permit
  a fallback user id.
- Calendar refresh failure returns empty availability context; it does not make
  calendar-derived constraints trusted.
- Baseet export failure delays plan generation; it does not create synthetic
  obligations without provenance.

Provider outage paths must not create trusted execution evidence.

## 5. Adapter Acceptance Checklist

A new provider adapter is incomplete unless it has:

- normalized DTO or equivalent mapping,
- user-id scoping at persistence and read time,
- redaction tests for raw URLs, tokens, OAuth payloads, and provider secrets,
- trust-state copy,
- provider outage degradation tests,
- clean-data exclusion tests for provider-bound rows,
- exposure registration for any provider-native suggestion,
- and a browser/API smoke path proving another user cannot see imported data.

## 6. Forbidden Shortcuts

Forbidden:

- branching in Cortex on provider names,
- admitting provider rows into `planning_calibration` because the provider said
  an item was complete,
- treating provider reachability as learning/completion truth,
- storing raw provider URLs/tokens in audit rows,
- weakening auth or scoping after provider failure,
- and provider-specific shortcuts in adaptive scheduling.

Allowed:

- Baseet-specific pressure cards,
- Moodle-specific import UI,
- calendar-specific availability copy,
- Jira/Linear-specific drift language,
- and provider-native icons/labels/links at the surface.

The difference is location:

```text
Specific at the edge.
General in the substrate.
Specific again at the surface.
```
