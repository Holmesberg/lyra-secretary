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
During the architecture freeze it also does not authorize new provider
adapters, passive tracking, runtime AI synthesis, new user-facing insights,
behavior-transition equations, schema migrations, or automatic interventions.

R5a extraction rule: any "allowed provider-native surface" or adapter-shape
language below describes the boundary for a future explicitly approved adapter.
It does not authorize new provider-native UI, imports, passive collection,
credential storage, schema work, or provider-derived truth during freeze
closure.

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

## 3. Dirty Provider Input Assumptions

Provider data is expected to be incomplete, stale, contradictory, malformed,
or semantically misleading.

Examples:

- a Jira/Linear ticket remains "in progress" after the human stopped working,
- a calendar block says "study" but reality diverged,
- an LMS assignment is imported without enough resource scope,
- a lecture tab stays open without active engagement,
- a provider deadline changes after an earlier sync,
- or two providers describe the same obligation differently.

This is not a reason to reject the middleware strategy. It is the reason the
adapter layer exists.

Required response:

```text
dirty provider row
  -> preserve provenance
  -> normalize to weak evidence
  -> attach trust state
  -> infer cautiously at the edge
  -> demote or ask for repair when contradictions are high
```

Forbidden response:

```text
dirty provider row
  -> treat as clean intention or execution truth
```

Lyra should absorb common provider mess through edge-case handling, confidence
demotion, stale-state checks, idle/overlong-session guards, and low-friction
repair prompts. It should not make the user manually clean every upstream
system before receiving value. Manual confirmation is reserved for cases where
the inferred consequence would affect planning, calibration, or stronger
adaptive authority.

### Passive Sensing And Digital-Phenotyping Boundary

Provider adapters, foreground activity, browser/resource events, and future
passive signals sit near the digital-phenotyping design space. Lyra may use
these traces only as bounded contextual evidence.

They must not become:

- mental-health inference,
- attention scoring,
- productivity surveillance,
- identity classification,
- competence scoring,
- or passive execution truth.

Additional rules for passive/provider-adjacent traces:

- Treat missingness as potentially informative but never as proof.
- Assume sparse behavioral traces can be identifying even when direct
  identifiers are removed.
- Preserve context boundaries: academic traces must not silently merge into
  health, identity, employment, or institutional-risk claims.
- Require explicit successor governance before any passive signal enters
  clean-data calibration.

## 4. Required Primitives

Adapters must translate into these provider-blind primitives where applicable:

```text
provider_connection
external_obligation
academic_asset
activity_event
execution_event
outcome_trace
outcome
exposure
trust_state
provenance
authority_level
redaction_status
idempotency_key
```

Provider imports usually create external obligations or weak activity traces.
They do not create planning calibration unless the user accepted or confirmed an
intention.

Pressure-map and analytics consumers must branch on provider-blind fields such
as `source_class`, `evidence_class`, `trust_state`, `authority_level`, and
`redaction_status`. Provider labels such as Moodle or Baseet may remain in
adapter UI/display mapping, but they must not become core pressure, Cortex,
ClaimCompiler, or clean-data admission branches.

## 5. Provider Failure Invariant

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

## 6. Adapter Acceptance Checklist

Freeze boundary: this checklist applies only after a new provider adapter has
been explicitly approved by current authority. It is not permission to start or
ship a new adapter during the freeze.

A new provider adapter is incomplete unless it has:

- normalized DTO or equivalent mapping,
- user-id scoping at persistence and read time,
- dirty-input confidence/demotion rules for stale, overlong, contradictory, or
  ambiguous provider rows,
- redaction tests for raw URLs, tokens, OAuth payloads, and provider secrets,
- trust-state copy,
- provider outage degradation tests,
- clean-data exclusion tests for provider-bound rows,
- exposure registration for any provider-native suggestion,
- and a browser/API smoke path proving another user cannot see imported data.

## 7. Forbidden Shortcuts

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
