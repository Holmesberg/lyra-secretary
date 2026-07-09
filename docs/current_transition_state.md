# Current Transition State

**Date:** 2026-07-01
**Status:** Active implementation orientation for the freeze-closure and safe
refactor cycle.

This document resolves phase-authority drift for the current stabilization
pass. It does not authorize new inference, user-facing claims, adaptive
scheduling, AI synthesis, schema expansion, provider adapters, or marketing
cohort expansion.

---

## Active Branch Frame

The active implementation branch is:

```text
wave-5-sovereignty-integrity-cycle
```

The branch scope is freeze-closure only:

```text
measurement forensics -> operator truth -> regression gates -> small safe seams
```

The objective of every wave is to reduce uncertainty before reducing
complexity. Complexity reduction is only performed when supported by
independent evidence, reversible seams, and mechanically enforced authority
boundaries.

This is a semantics-preserving stabilization/refactor pass. It should make
existing behavior easier to verify and maintain, not create stronger claims,
new surfaces, or new runtime authority.

Current sequence:

1. E0 exposure forensics and repair ledger.
2. R2 operator cockpit trusted/red-for-real.
3. S1c hardening into gates.
4. R5a stale docs and authority cleanup before further extraction.
5. R3/R4 behavior-preserving extraction in small reversible seams, only while
   those seams reduce operational danger.
6. R5b public proof/runtime runbooks.
7. R6 final cohort proof or controlled evidence-collection alpha.
8. Post-freeze computation planning only after R6.

No backend god-module extraction should begin while `/operator` has unresolved
exposure blockers. A cockpit may be implementation-green while cohort-yellow
for real-data gaps; do not weaken denominators to force cohort-green.

Do not continue opportunistic cleanup indefinitely. If three consecutive
frontend/backend seams only reduce apparent surface area and do not reduce
operational danger, stop R3/R4 refactoring and move to public proof, users, or
S1c hardening.

Do not perform additional brand/domain migration in this cycle. The current
runtime host compatibility remains parked until a separate topology/domain plan
is explicitly authorized.

---

## Governing Documents

Use these documents as the current authority chain:

1. `docs/AUTHORITY.md` - cross-repo authority hierarchy.
2. `docs/single_authority_contract.md` - one owner per truth class, mutation
   path, and claim path.
3. `docs/operator_dashboard_contract.md` - implementation-green vs
   cohort-green and cockpit readiness semantics.
4. `docs/runbooks/post_wave_dogfood_loop.md` - reusable browser/API/export
   verification loop plus optional CI/CD proof collection after push.
5. `docs/registries/refactor_stabilization_ledger.md` - wave/seam audit
   trail, browser artifacts, rollback notes, and issue references.
6. `docs/audits/e0_exposure_forensics_2026_07_01.md` - E0 row-level exposure
   forensics and repair evidence.
7. `docs/audits/refactor_spaghetti_audit_2026_06_29.md` - documentation-only
   ordering input for stabilization work.
8. `MANIFESTO.md` - highest-level product/research doctrine and kill criteria.
9. `docs/cortex_contract_v0.md` - observed/derived/latent boundaries,
   canonical metrics, clean-data profiles, and Cortex phase rules.
10. `docs/cortex_product_research_contract_v0.md` - user-burden, product vs
   research separation, and low-friction instrumentation contract.
11. `docs/architecture_freeze_priority_hold_2026_05_20.md` - active freeze
   boundary for evidence/synthesis ideas; preserve later, do not implement now.
12. `docs/research_mapping.md` - explanatory claim map for current support vs
   speculation.
13. `docs/cross_domain_breakthrough_audit_2026_05_20.md` - literature
   compression and breakthrough map; not research validation.
14. `docs/tightened_docs/15_long_term_repo_strategy.md` and
   `docs/tightened_docs/17_immediate_freeze_targets.md` - semantic-entropy and
   freeze-gate constraints.

`docs/building_phases.md` remains useful historical/product roadmap context,
but it is stale April phase planning and is not current implementation
authority.

`docs/AGENT_HANDOFF.md` remains historical onboarding context only. It cannot
authorize JARVIS work, OpenClaw runtime mutation, AI synthesis, provider
adapters, passive tracking, new insight surfaces, or behavior-transition
equations.

The following documents are explicitly historical, parked, or subordinate
during the current freeze-closure pass. Active-sounding text inside them,
including "ship", "allowed", "approved", schema sketches, passive tracking,
AI/synthesis, provider adapters, insight surfaces, or behavior equations,
cannot authorize runtime work unless promoted by the authority chain above:

- `docs/building_phases.md`
- `docs/phase_6_architecture_backlog.md`
- `docs/deadline_mechanism_design.md`
- `docs/academic_execution_substrate.md`
- `docs/academic_asset_velocity_and_evidence_fusion_plan.md`
- `docs/core_product_loop_wave_plan.md`
- `docs/AGENT_HANDOFF.md`
- `docs/provider_adapter_contract.md`

---

## Current Implementation Rule

The current freeze-closure pass may:

- perform evidence-backed production forensics only with redacted artifacts and
  explicit ledger notes,
- preserve current API response shapes and user-facing behavior,
- add characterization tests and browser/API/export verification,
- collect CI/CD proof after pushed seams or record why no matching CI run
  exists,
- extract small behavior-preserving seams behind compatibility shims,
- promote stable, allowlisted scans into hard gates,
- file and close GitHub issues for product, verifier, topology, authority,
  documentation, and measurement bugs,
- and clarify documentation lineage when stale docs could authorize wrong
  runtime behavior.

The current freeze-closure pass must not:

- add new user-facing analytics claims,
- add new behavioral metrics or latent labels,
- add new public endpoints,
- call NVIDIA/Kimi or any hosted LLM,
- implement cascade alerts,
- implement adaptive scheduling,
- change clean-data semantics,
- create new user-burden inputs,
- introduce schema migrations without explicit user approval,
- wire OpenClaw/GPT into product runtime,
- add new provider adapters,
- add passive tracking,
- or weaken operator denominators to force a green readiness state.

Browser screenshots explain failures but do not prove behavior. Canonical proof
comes from backend state, exported evidence, operator invariants, and browser
behavior. Verifier bugs are first-class bugs and must be classified before
assuming the product is broken.

## Operational Danger Score

The target "danger 3-4/10" is operational, not intuitive. A seam reduces danger
only if it improves at least one of these observable properties:

- Breakage observability: a failing behavior becomes caught by a standard
  verification run, targeted test, static scan, or operator invariant.
- Reversibility: rollback is smaller, documented, and does not require
  production data repair.
- Authority clarity: a mutation, exposure, provider, claim, or clean-data path
  has one clearer owner and fewer bypasses.
- Measurement integrity: exposure, clean-data, provenance, or output-surface
  semantics become harder to misread or overclaim.
- Runtime proof: local-current, hosted-public, CI/CD, or dogfood proof becomes
  more current, less ambiguous, or more complete.

Danger is allowed to be scored at 3-4 only when all of these are true:

- `/operator` is implementation-green, with no implementation blockers.
- `exposure_without_render_count` is zero for actionable render-required
  surfaces.
- Operator read-only proof has zero DB/API/Redis count diffs.
- S1c hard gates pass for the touched surface.
- CI passes on the exact pushed SHA.
- Hosted-public proof is current, or deployment lag is explicitly classified.
- Known high-risk findings are closed or parked with owner, test, artifact, and
  rollback note.
- New seams are producing danger reduction, not only cosmetic line-count or
  file-count reduction.

Cosmetic-only seams include renames, move-only splits, helper extraction, or
surface-area reduction that does not change any proof, gate, ownership,
rollback boundary, issue state, or runtime observability. Record each seam's
danger delta in the stabilization ledger. Three consecutive cosmetic-only seams
means stop refactoring and switch to public proof, users, or S1c hardening.

---

## Deferred Work

The following remain later phases and require a new explicit plan:

- Admission/Coverage Gate, Execution Drift Decomposition, Re-entry Resolution
  Survival, and Pressure-to-Execution Funnel beyond operator diagnostics.
- AI synthesis over evidence packets or OpenClaw/GPT product wiring.
- Public cascade intervention surfaces.
- Behavior-transition runtime equations.
- New provider adapters or passive tracking.
- Any stronger adaptive authority or cohort expansion beyond controlled
  evidence collection.

If implementation-green is true and the only cohort blocker is insufficient
real data, Lyra may enter controlled evidence-collection alpha: limited trusted
users, explicit research/dogfood status, no marketing, and no strong claims.

---

## Historical Evidence-Packet Ledgers

The remaining Wave 3-6 ledgers below are retained as historical branch context.
They do not supersede the current freeze-closure sequence above.

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

---

## Parked Governance Ledger

Waves 7-11 are preserved as parked pressure memory in
`docs/parked_governance_specs.md`.

They are not implementation authority for this branch. They document future
seams for agent authority, repair quarantine, test taxonomy, public copy
alignment, and global enforcement checks, but no runtime machinery should be
added from those waves until a current boundary failure promotes one of them.

### Parked

| Wave | Status | Promotion condition |
| --- | --- | --- |
| Wave 7: Agent / JARVIS / OpenClaw authority | Parked. | Promote only if a mutation-capable agent flow or confirmation path creates a current authority risk. |
| Wave 8: Repair jobs and mutation quarantine | Parked. | Promote only if repair-derived state can enter clean analytics or public evidence without an admission rule. |
| Wave 9: Test suite as membrane system | Parked. | Promote only if tests block boundary simplification by preserving decorative internals. |
| Wave 10: Public / AI-readable copy alignment | Parked. | Promote only if public or AI-readable copy implies authority the runtime does not have. |
| Wave 11: Global enforcement checks | Parked. | Promote only after a real boundary regression proves prose invariants are not enough. |
