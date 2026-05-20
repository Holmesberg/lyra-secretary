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
