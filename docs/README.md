# LyraOS Documentation Map

**Status:** Active documentation entrypoint for freeze-closure and safe
refactor work.

This file exists to keep current authority separate from historical context.
If another document conflicts with this map, follow `docs/AUTHORITY.md` and
`docs/current_transition_state.md` first.

## Active Authority Chain

Read these first for implementation work:

1. `docs/AUTHORITY.md` - canonical cross-repo authority hierarchy and standing
   freeze doctrine.
2. `docs/current_transition_state.md` - active freeze-closure sequence,
   danger score, and governing document order.
3. `docs/single_authority_contract.md` - one owner per truth class, mutation
   path, and claim path.
4. `docs/operator_dashboard_contract.md` - operator cockpit semantics,
   implementation/cohort readiness split, and stop/go invariants.
5. `docs/runbooks/post_wave_dogfood_loop.md` - reusable browser/API/export
   proof loop.
6. `docs/registries/refactor_stabilization_ledger.md` - seam ledger,
   artifacts, issue references, and rollback notes.

For Cortex, claim, and measurement boundaries, also read:

- `docs/cortex_contract_v0.md`
- `docs/cortex_product_research_contract_v0.md`
- `docs/claim_compiler_and_synthesis_boundary.md`
- `docs/measurement_integrity_before_agency_claims.md`

For topology, deployment, and proof safety, also read:

- `docs/deployment_architecture.md`
- `docs/registries/runtime_topology_ownership_manifest.json`
- `docs/runbooks/post_wave_dogfood_loop.md`

## Current Freeze Boundary

Freeze remains active. Do not add runtime AI synthesis,
OpenClaw-to-product GPT wiring, new user-facing insight types,
behavior-transition equations, causal pressure-return claims, productivity,
focus, motivation, or avoidance scores, passive tracking, new provider
adapters, schema migrations, public behavioral claims, or domain/rebrand work
without explicit approval and a new plan.

During freeze closure, implementation work may:

- preserve current API shapes and user-visible behavior;
- add characterization tests and static/browser/API/export verification;
- harden stable S1c gates;
- clarify stale documentation lineage;
- extract small behavior-preserving seams behind compatibility shims;
- collect CI/CD proof and record exact artifacts.

Implementation work must not weaken operator denominators, exposure/render
invariants, clean-data semantics, account-role boundaries, or cohort readiness
thresholds to force a green state.

## Documentation Lanes

### Active Contracts

Active contracts can constrain code when they are consistent with
`docs/AUTHORITY.md` and `docs/current_transition_state.md`.

Examples:

- `docs/single_authority_contract.md`
- `docs/operator_dashboard_contract.md`
- `docs/archive/legacy/provider_academic/provider_adapter_contract.md` as a historical boundary document only; it does not
  authorize new adapters during freeze
- `docs/academic_pressure_map_contract.md`
- `docs/stale_session_recovery_policy.md`
- `docs/testing_patterns.md`

### Implementation Plans And Runbooks

These can guide current work only when subordinate to the active authority
chain:

- `docs/runbooks/post_wave_dogfood_loop.md`
- `docs/archive/legacy/planning/core_product_loop_wave_plan.md` as historical/subordinate context
- `docs/architecture_freeze_priority_hold_2026_05_20.md`
- `docs/audits/refactor_spaghetti_audit_2026_06_29.md` as ordering input only

### Historical Or Parked Context

These preserve project memory but cannot authorize runtime work by themselves:

- `docs/archive/AGENT_HANDOFF.md`
- `docs/archive/legacy/planning/building_phases.md`
- `docs/archive/legacy/history/project_history.md`
- `docs/archive/legacy/history/LyraOS_evolution.md`
- `docs/archive/legacy/planning/phase_6_architecture_backlog.md`
- `docs/archive/legacy/provider_academic/deadline_mechanism_design.md`
- `docs/archive/legacy/provider_academic/academic_execution_substrate.md`
- `docs/archive/legacy/provider_academic/academic_asset_velocity_and_evidence_fusion_plan.md`
- `docs/parked_ideas.md`
- `docs/parked/`
- `archive/`

Active-sounding language inside historical or parked docs, including "ship",
"approved", schema sketches, passive tracking, AI/synthesis, new insights,
provider adapters, or behavior equations, is non-authorizing unless promoted by
the active authority chain.

## Verification Roles

`LYRA_COOKIE_ALINASSERSABRY` is the legacy env name for the operator account.
It is read-only and may verify `/operator`, topology, privacy, and readiness
only.

`LYRA_COOKIE_HOLMESBERG` is the legacy env name for the mutable dogfood
account. It may create synthetic tasks, deadlines, timers, brain dumps,
pressure-map previews, and related rows only with unique prefixes and cleanup
or void proof.

Mocked auth, API interception, seeded fixtures, and local-current proxying may
support proof only when labeled. They may not be cited as hosted-public user
proof.

## When In Doubt

If a doc, script, or route appears to authorize stronger behavior than the
active authority chain allows, treat it as stale or parked until proven
otherwise. File or update an issue when the drift can mislead future work.
