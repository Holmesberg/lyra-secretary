# LyraOS Documentation Authority Map - 2026-06-04

Status: audit report only.  
May authorize code: false.  
Runtime owner: none.

## Rule

```text
The repo needs fewer active authority surfaces, not more doctrine.
```

## Canonical Authority Order

This is the recommended read order for future agents until the live docs are
cleaned up.

1. `MANIFESTO.md`
   - Use latest current governance amendments.
   - Treat older sections as historical when later amendments supersede them.
2. `docs/AUTHORITY.md`
   - Implementation-governance map.
   - Should be explicitly delegated by the Manifesto.
3. `docs/current_transition_state.md`
   - Active branch scope.
   - Needs split between authorizing and context docs.
4. Freeze constraints:
   - `docs/architecture_freeze_priority_hold_2026_05_20.md`
   - `docs/tightened_docs/15_*`
   - `docs/tightened_docs/17_*`
5. Active contracts:
   - `docs/cortex_contract_v0.md`
   - `docs/cortex_product_research_contract_v0.md`
   - `docs/provider_adapter_contract.md`
   - `docs/calibration_contract.md`
   - pressure/exposure/output/security contracts.
6. Active doctrine and assumption registers:
   - `docs/behavioral_instrumentation_doctrine.md`
   - `docs/product_research_assumption_register.md`
   - `docs/context_switching_footprint_hypothesis.md`
   - `docs/tightened_docs/*`
7. Current product-maintenance guidance:
   - `docs/core_product_loop_wave_plan.md`
   - subordinate to items 1-6.
8. External orientation:
   - `README.md`
   - `docs/external_review_quickstart.md`
   - `docs/professor_review_packet.md`
   - public AI-readable files.
9. Historical or roadmap context:
   - `docs/building_phases.md`
   - `docs/project_history.md`
   - `docs/phase_6_architecture_backlog.md`
   - old strategic decisions.
10. No implementation authority:
    - `docs/parked/*`
    - `docs/parked_ideas.md`
    - `docs/parked_governance_specs.md`
    - `archive/*`
    - ignored `LyraOS/` vault.

## Active Invariants By Classification

| Invariant | Classification | Authority Source | Allowed Use |
|---|---|---|---|
| User remains author of truth. | active doctrine | Manifesto/AUTHORITY/provider contracts | Blocks silent canonical mutation. |
| Capability is not authority. | active doctrine | AUTHORITY/Manifesto | Blocks provider/passive evidence promotion. |
| Unknown stays unknown. | active doctrine | Cortex contracts | Blocks unsupported inference. |
| Mirrors and nudges are interventions. | active doctrine | Manifesto/exposure docs | Requires exposure accounting. |
| Execution time excludes pauses. | already implemented / active doctrine | Cortex/product-research docs | Metric and UI wording. |
| Session span includes pauses. | already implemented / active doctrine | Cortex/product-research docs | Metric and UI wording. |
| Pause overhead is recovery evidence, not execution. | active doctrine | interruption metric docs | Recovery planning only. |
| Occupancy is planning footprint, not execution truth. | active doctrine | interruption metric docs | Task-window guidance. |
| Provider data is structure until confirmed. | active doctrine | provider contracts | No completion/study truth from provider alone. |
| Brain dump creates candidates until confirmed. | already implemented / active doctrine | core loop plan/runtime behavior | Product loop and browser verification. |
| Pressure map is diagnostic planning support. | already implemented / active doctrine | pressure contracts/core loop | No exact predictive claims. |
| Open threads are recovery-first. | parked hypothesis / active copy boundary | H8/open-thread parked plan | Do not ship as insight score. |
| Context switching footprint is correlation only. | parked hypothesis | H8/assumption register | No causal failure/focus claims. |
| Browser extension passive capture is postponed. | parked hypothesis | passive capture gate | No runtime work without promotion. |
| AI cold-start estimates are not calibration truth. | parked hypothesis | estimate provenance plan | No schema/runtime work without promotion. |
| Observer sovereignty remains watchlist. | concept-note | observer watchlist | No new subsystem. |
| Archetype identity labels are unsafe. | active doctrine / research risk | Manifesto VT-25, tightened docs | Avoid user-facing identity claims. |
| Fragmentation/switching scores are forbidden. | active doctrine | H8/tightened docs | Use recovery actions only. |

## Docs With Implementation Authority

Implementation authority does not mean every sentence authorizes code. It means
the doc can constrain implementation when not superseded by a higher layer.

- `docs/AUTHORITY.md`
- `docs/current_transition_state.md`, after authorizing/context split
- `docs/cortex_contract_v0.md`
- `docs/cortex_product_research_contract_v0.md`
- `docs/provider_adapter_contract.md`
- `docs/calibration_contract.md`
- `docs/behavioral_instrumentation_doctrine.md`
- `docs/product_research_assumption_register.md`
- `docs/tightened_docs/*`
- `docs/core_product_loop_wave_plan.md`, only as subordinate product-maintenance
  guidance.

## Parked Memory Only

Treat these as memory unless a new active plan promotes them:

- `docs/parked/*`
- `docs/parked_ideas.md`
- `docs/parked_governance_specs.md`
- `docs/insight_mechanisms_post_retention.md`
- `docs/phase_6_architecture_backlog.md`
- `docs/building_phases.md`, unless refreshed
- `docs/project_history.md`
- `archive/*`
- ignored `LyraOS/` vault.

## Docs Needing Frontmatter Or Banners

Priority:

1. `docs/building_phases.md`
   - mark historical/superseded.
2. `docs/AGENT_HANDOFF.md`
   - mark onboarding/context; update stale instructions.
3. `docs/parked_ideas.md`
   - mark historical/parked and remove active language.
4. `docs/deadline_mechanism_design.md`
   - mark historical/implemented foundation or active only if re-promoted.
5. `docs/academic_execution_substrate.md`
   - clarify no hidden/passive measurement authority.
6. `docs/academic_asset_velocity_and_evidence_fusion_plan.md`
   - park passive telemetry expansion.
7. `frontend/public/lyraos.md` and `frontend/public/llms.txt`
   - mark derivative external orientation with freshness date.
8. `archive/appstore/summary_of_app.md`
   - demote all active claims or promote out of archive as snapshot.

## Authority Conflicts To Resolve First

| Conflict | Risk | Resolution |
|---|---|---|
| Manifesto index vs AUTHORITY map | future agents miss live implementation constraints | Manifesto delegates live implementation map to AUTHORITY. |
| current_transition_state mixes context and authority | explanatory docs accidentally authorize work | Split sections. |
| building_phases says source of truth | stale roadmap resurrects old phases | Add historical/superseded banner. |
| parked_ideas says elevated | parked memory becomes active plan | Move/pointer or historical banner. |
| H8 forbids avoidance while H3 permits avoidance chip | sensitive copy can ship | Add H3 supersession note. |
| Moodle completion mutates deadline | provider truth violation | completion_candidate only. |
| ignored LyraOS vault has active status | untracked docs become shadow authority | canonical docs declare vault external/local. |

## Promotion Path

No parked idea should promote itself. Promotion requires:

1. Active product pressure or observed failure.
2. Explicit promotion condition satisfied.
3. New or updated active implementation plan.
4. Authority check against Manifesto/AUTHORITY/Cortex/provider/exposure docs.
5. Browser verification plan when product-facing.
6. Kill/falsification criteria if research or adaptive behavior is involved.

## Minimal Reading Path For New Agents

For code/product work:

1. `README.md`
2. `docs/AUTHORITY.md`
3. `docs/current_transition_state.md`
4. `docs/core_product_loop_wave_plan.md`
5. relevant active contract
6. relevant tests/runtime files

For research/metrics work:

1. `MANIFESTO.md` latest amendments
2. `docs/cortex_contract_v0.md`
3. `docs/cortex_product_research_contract_v0.md`
4. `docs/behavioral_instrumentation_doctrine.md`
5. `docs/product_research_assumption_register.md`
6. relevant tightened doc

For future ideas:

1. `docs/parked/future_implementation_index.md`
2. specific parked note
3. active authority check
4. no code unless explicitly promoted.

