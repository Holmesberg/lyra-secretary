# Current Transition State

**Date:** 2026-05-20
**Status:** Active implementation orientation for the evidence-packet branch.

This document resolves phase-authority drift for the current implementation
pass. It does not authorize new inference, user-facing claims, adaptive
scheduling, AI synthesis, or schema expansion.

---

## Active Branch Frame

The active implementation branch is:

```text
feature/evidence-packet-claim-compiler
```

The branch scope is Phase 0+1 only:

```text
raw traces -> EvidencePacket -> ClaimCompiler -> existing registered surface
```

This is a semantics-preserving refactor. It should make existing behavioral
claims easier to inspect and govern, not create stronger claims.

---

## Governing Documents

Use these documents as the current authority chain:

1. `MANIFESTO.md` - highest-level product/research doctrine and kill criteria.
2. `docs/cortex_contract_v0.md` - observed/derived/latent boundaries,
   canonical metrics, clean-data profiles, and Cortex phase rules.
3. `docs/cortex_product_research_contract_v0.md` - user-burden, product vs
   research separation, and low-friction instrumentation contract.
4. `docs/AGENT_HANDOFF.md` - agent onboarding and operator-only inference
   boundaries.
5. `docs/research_mapping.md` - explanatory claim map for current support vs
   speculation.
6. `docs/cross_domain_breakthrough_audit_2026_05_20.md` - literature
   compression and breakthrough map; not research validation.
7. `docs/tightened_docs/15_long_term_repo_strategy.md` and
   `docs/tightened_docs/17_immediate_freeze_targets.md` - semantic-entropy and
   freeze-gate constraints.
8. `docs/architecture_freeze_priority_hold_2026_05_20.md` - temporary
   priority hold for the evidence/synthesis breakthrough; preserve it for
   later, but do not implement it during this branch.

`docs/building_phases.md` remains useful historical/product roadmap context,
but it is stale April phase planning and is not the only active phase
authority for May 2026 Cortex/evidence work.

---

## Current Implementation Rule

Phase 0+1 may:

- centralize evidence metadata that is already implicit in analytics outputs,
- compile existing deterministic claims from explicit evidence packets,
- preserve current API response shapes,
- add tests that prevent claim inflation,
- and clarify documentation lineage.

Phase 0+1 must not:

- add new user-facing analytics claims,
- add new behavioral metrics or latent labels,
- add new public endpoints,
- call NVIDIA/Kimi or any hosted LLM,
- implement cascade alerts,
- implement adaptive scheduling,
- change clean-data semantics,
- or create new user-burden inputs.

---

## Deferred Work

The following remain later phases:

- dormant decision-point registry for cascade/sequence disruption,
- NVIDIA/Kimi rate-budget enforcement before any synthesis path,
- AI synthesis over evidence packets,
- public cascade intervention surfaces,
- and any stronger adaptive authority.

Those phases require separate implementation plans and must re-check exposure,
clean-data, and output-surface gates before code lands.

The temporary priority hold in
`docs/architecture_freeze_priority_hold_2026_05_20.md` is the current reminder
that AI synthesis and public cascade intervention remain later, not hidden
Phase 1 scope.

---

## Wave 3 Deletion And Parking Ledger

EvidencePacket remains the class name for branch continuity, but it is no
longer allowed to become a provider DTO, output-surface grammar, or future
AI-synthesis container.

### Kept In EvidencePacket

| Field | Why it stays now |
| --- | --- |
| `packet_id` | Stable audit handle for compiled claims. |
| `clean_profile` | Suppresses missing clean-data admission. |
| `eligible_sample_count` | Suppresses under-sampled claims with `min_n_required`. |
| `min_n_required` | Declares the sample floor for the packet. |
| `observed_metrics` | Carries sanitized scalar analytics evidence already present in insight candidates. |
| `source_refs` | Minimal non-provider-specific provenance: `type`, `id`, `surface_id`. |
| `prohibited_claims` | Blocks claim tags that would overstate authority. |
| `suppression_reason` | Carries explicit suppression from upstream gates. |

### Deleted Or Moved Out Of EvidencePacket

| Field | Status | Reason | Reintroduction condition |
| --- | --- | --- | --- |
| `source_surface_id` | Deleted as duplicate. | `source_refs[*].surface_id` already carries the provenance handle. | Only reintroduce if a separate packet-level surface identity is proven non-duplicative by a failing trace/debug test. |
| `signal_family` | Deleted. | Hardcoded taxonomy with no Phase 1 decision effect. | Only reintroduce when multiple signal families drive different gates, wording, or suppression. |
| `truth_class` | Moved to output-surface metadata. | Publication truth belongs to registered surfaces, not packet grammar. | Do not reintroduce to EvidencePacket. Add or revise output-surface registry metadata instead. |
| `confidence_tier` | Deleted. | Claim confidence is computed by deterministic synthesis logic; a packet copy creates a second source of truth. | Only reintroduce if packet-level confidence directly changes suppression or public wording. |
| `allowed_claims` | Deleted. | It looked like an allowlist but was not enforced. False assurance is worse than absence. | Only reintroduce as an enforced positive gate with tests showing a claim is blocked without it. |

### Parked

| Concept | Why parked | Revisit condition |
| --- | --- | --- |
| `competing_hypotheses` | Epistemically useful later, but decorative in Phase 1 because it did not change wording, confidence, or suppression. | Revisit when deterministic claim wording or suppression explicitly weakens claims in the presence of alternatives. |
| Rich evidence/provenance records | Valid future need, but unsafe inside `observed_metrics` as a raw data bag. | Revisit with a typed evidence/audit store and redaction rules, not by expanding EvidencePacket. |

`observed_metrics` is intentionally narrow: scalar `insight_id`,
`data_points`, `confidence`, `strength`, and sanitized `facts` only. It must not
carry provider raw payloads, URLs, tokens, resource bodies, OAuth data,
Baseet-specific rows, Moodle blobs, latent labels, or moralized terms.

---

## Wave 4 Deletion And Parking Ledger

Exposure render snapshots are not public payload archives. They are durable
audit records, so they should store the smallest safe proof of what was shown,
not every piece of copy and provider-derived detail the user saw.

### Removed From Long-Lived Exposure Snapshots

| Surface | Removed | Why | Reintroduction condition |
| --- | --- | --- | --- |
| `analytics.insights` | Full public insight response JSON. | It included observation copy and could accidentally retain internal/debug fields if the translator changed. | Only store richer payloads in a typed audit store with explicit retention and redaction rules. |
| `analytics.insights` | Evidence packet internals. | Packet internals are claim-governance data, not public render content. | Store only safe packet IDs/source refs unless a typed audit reader needs more. |
| `academic.pressure_map` | Assignment/deadline titles in exposure snapshots. | Provider-derived titles are useful in the response but should not become durable exposure exhaust by default. | Reintroduce only with a surface-specific retention justification. |
| `academic.pressure_map` | Recovery copy, coverage-question text, compression details, and item warnings in exposure snapshots. | These can contain provider-derived titles or user-salient context. Counts and action types are enough for render/audit proof. | Reintroduce only through a redacted summary schema. |

### Kept In Exposure Snapshots

| Surface | Kept | Why it stays |
| --- | --- | --- |
| `analytics.insights` | Surface metadata, rendered insight IDs, suppressed generator IDs, sample counts, and safe audit envelopes. | This proves the rendered set and its claim lineage without persisting copy or packet bodies. |
| `academic.pressure_map` | Surface role, horizon, item counts, pressure/trust/complexity counts, recovery action types, coverage-question count, estimate range, and source counts. | This preserves operational auditability while avoiding durable provider-content retention. |

### Parked

| Concept | Why parked | Revisit condition |
| --- | --- | --- |
| Full render-content retention | Useful for exact replay/debugging, but too broad for behavioral/provider-derived surfaces. | Revisit after defining per-surface retention policy, redaction class, and operator access controls. |
| Rich evidence audit store | Needed eventually for forensics and research validation. | Implement separately from public payloads and exposure render snapshots, with typed fields and retention rules. |

---

## Wave 5 Deletion And Parking Ledger

Baseet and future providers must enter through provider-neutral seams, not by
teaching Pressure Map or ClaimCompiler to understand every provider dialect.

### Removed Or Renamed From Pressure Map Core

| Concept | Status | Why | Reintroduction condition |
| --- | --- | --- | --- |
| `moodle_deadlines` | Renamed to `external_obligation_count`. | Moodle is one provider, not a substrate category. | Do not reintroduce to core schemas; provider display names belong at adapter/UI edges. |
| `native_deadlines` | Renamed to `native_obligation_count`. | Pressure Map reasons about obligations, not provider-specific deadline dialects. | Only add provider-specific counts in a provider-native/admin view. |
| Raw `external_source` as item `source` | Replaced with provider-blind `source`, `source_class`, `evidence_class`, `provider_kind`, `raw_authority_level`, and `redaction_status`. | Core pressure logic should branch on evidence authority and provenance class, not provider string names. | Provider labels may be used for display only after adapter redaction/provenance rules are explicit. |
| Public Baseet-specific methodology copy | Replaced with provider-boundary wording. | Baseet readiness is an internal seam, not a user-facing claim. | Reintroduce only on a Baseet-native adapter/sync surface. |

### Kept

| Concept | Why it stays |
| --- | --- |
| `provider_kind` | Kept as provenance/display metadata, not as clean-data or claim authority. |
| Recovery options on Pressure Map | They remain low-authority suggestions requiring explicit user action. |
| Moodle fixtures in tests | They still simulate an existing provider, but tests assert provider-neutral output contracts. |

### Parked

| Concept | Why parked | Revisit condition |
| --- | --- | --- |
| Full provider connection abstraction | Useful before live Baseet scale, but no migration is needed for this seam pass. | Revisit when a second provider must persist connections or sync state. |
| Provider-native pressure cards | Allowed at the edge, but not required for current pressure-map containment. | Revisit with Baseet live integration and UI copy review. |

---

## Wave 6 Authority Ledger

Pressure Map stays smart, but its authority is now explicit:

```text
surface_role: diagnostic_planning_surface
authority_rung: suggestion
mutation_permission: explicit_user_confirmation_required
```

### Allowed

| Capability | Why it stays |
| --- | --- |
| Pressure clusters | Helps the user see where the week compresses. |
| Visible load ranges | Preserves useful planning intelligence without fake precision. |
| Recovery options | Keeps the surface actionable rather than an anxiety visualization. |
| Trust states and coverage questions | Makes uncertainty visible before planning. |

### Denied

| Authority | Status | Reason |
| --- | --- | --- |
| Automatic task creation | Denied. | Recovery options require explicit user action. |
| Automatic calendar mutation | Denied. | Pressure Map may suggest schedule repair, not mutate time. |
| Student-risk scoring | Denied. | Pressure is a planning surface, not institutional risk classification. |
| Learning/mastery inference | Denied. | Provider/deadline structure does not prove learning or competence. |
| Clean behavioral calibration from provider data | Denied. | Provider-derived pressure may guide planning, but it does not enter clean execution evidence. |

### Parked

| Concept | Why parked | Revisit condition |
| --- | --- | --- |
| One-click plan execution | Useful product path, but it crosses from suggestion into mutation. | Revisit with explicit confirmation flow, exposure tracking, and rollback semantics. |
| Provider-fed calibration | Not admissible during Phase 1. | Revisit only after provider data has clean-data admission rules and contradiction handling. |
