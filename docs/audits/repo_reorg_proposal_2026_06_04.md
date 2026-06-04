# Repo Reorganization Proposal - 2026-06-04

Status: audit proposal only.  
May authorize code: false.  
No files should be moved by this report alone.

## Goal

Make the repo easier to reason about without expanding doctrine.

Target shape:

```text
docs/
  README.md                  # doc map and read order
  authority/ or root active  # active governance and contracts
  product/                   # current product loop/surfaces
  providers/                 # provider adapter contracts and primitives
  research/                  # active research contracts/registers
  parked/                    # future memory, no implementation authority
  presentations/             # derivative external materials
  incidents/                 # postmortems and operational history
  design_patterns/           # historical/pattern guidance, indexed
archive/
  README.md                  # archive is non-authoritative
LyraOS/
  ignored local vault        # explicitly not canonical repo truth
```

Do not do this as a mass move. Use banners and indexes first.

## Reorg Wave A - Index Before Moving

Add:

- `docs/README.md`
- `docs/tightened_docs/README.md`
- `docs/parked/README.md`
- `docs/design_patterns/README.md`
- `docs/incidents/README.md`
- `docs/presentations/README.md`

Each index should answer:

- What is this folder for?
- Can files here authorize code?
- Which files are current?
- Which files are historical?
- What supersedes what?

## Reorg Wave B - Authority Banners

Add frontmatter or top banners to high-confusion docs:

- `docs/building_phases.md`
- `docs/AGENT_HANDOFF.md`
- `docs/parked_ideas.md`
- `docs/deadline_mechanism_design.md`
- `docs/academic_execution_substrate.md`
- `docs/academic_asset_velocity_and_evidence_fusion_plan.md`
- `archive/appstore/summary_of_app.md`
- `frontend/public/lyraos.md`
- `frontend/public/llms.txt`

Use the metadata vocabulary already defined in `docs/AUTHORITY.md`:

```yaml
authority: canonical | active-contract | implementation-plan | concept-note | external-orientation | historical | parked
may_authorize_code: true | false
runtime_owner: backend | frontend | docs | operator | none
supersedes:
superseded_by:
```

## Reorg Wave C - Public Product Facts

Create one source for current product facts.

Candidate:

```text
docs/product/current_product_facts.md
```

It should define:

- current cohort/status;
- current core loop;
- current surfaces;
- confirmation boundaries;
- provider boundaries;
- no passive surveillance;
- what is implemented vs parked.

Derivative docs:

- `README.md`
- `frontend/public/lyraos.md`
- `frontend/public/llms.txt`
- `docs/external_review_quickstart.md`
- `docs/professor_review_packet.md`

These should include freshness dates and point back to the product facts source.

## Reorg Wave D - Provider Primitive Registry

Create a small provider primitive registry before expanding integrations.

Candidate:

```text
docs/providers/provider_primitive_registry.md
```

Include:

- `external_obligation`
- `scheduled_block`
- `recurring_commitment`
- `structured_asset`
- `task_candidate`
- `completion_candidate`
- `availability_constraint`
- `confirmation`

This registry should not authorize new providers. It only prevents future docs
from inventing provider-specific truth semantics.

## Reorg Wave E - Parked Consolidation

Consolidate parked material under `docs/parked/`.

Actions:

- Make `docs/parked/future_implementation_index.md` the sole parked index.
- Move or banner root parked docs:
  - `docs/parked_ideas.md`
  - `docs/parked_governance_specs.md`
  - `docs/insight_mechanisms_post_retention.md`
- Remove active-sounding language from parked containers.
- Require promotion criteria for every parked idea.

## Merge / Archive / Park Recommendations

| Item | Recommendation | Rationale |
|---|---|---|
| `docs/building_phases.md` | historical banner | stale roadmap with active-sounding language |
| `docs/AGENT_HANDOFF.md` | revise or subordinate | stale agent instructions |
| `archive/appstore/summary_of_app.md` | promote as dated snapshot or demote all citations | archive/current contradiction |
| `frontend/public/lyraos.md` and `llms.txt` | derivative external orientation | public copy must not outrun product truth |
| `docs/academic_pressure_map_contract.md` | keep active but domain-specific | academic module, not global product frame |
| `docs/academic_execution_substrate.md` | rewrite or constrain | hidden/passive measurement language |
| `docs/import_integrations_capability_map.md` | historical/superseded for truth semantics | VEVENT 1:1 task mapping conflicts with current boundary |
| `docs/moodle_lms_integration.md` | revise provider truth wording | Moodle status must be candidate evidence |
| `docs/parked_ideas.md` | move/replace with pointers | parked file leaks active intent |
| ignored `LyraOS/` vault | declare external/local | avoid shadow authority |

## Do Not Expand List

Do not expand these during cleanup:

- no new ontology for every doc type;
- no schema or runtime implementation;
- no passive/browser-extension tracking;
- no provider adapter implementation;
- no notification adaptation system;
- no formal research validation framework beyond parked docs;
- no fragmentation/switching score;
- no archetype identity UI;
- no institutional monitoring language.

## Minimal `docs/README.md` Outline

```markdown
# LyraOS Docs Map

## Current Product Loop

brain dump -> bind to existing obligations -> pressure/occupancy map
-> confirmed task/recovery creation -> session tracking -> recovery/insights

## Authority Ladder

1. MANIFESTO latest current governance amendments
2. docs/AUTHORITY.md
3. docs/current_transition_state.md
4. active contracts
5. implementation plans
6. external orientation
7. parked/historical/archive

## Active Contracts

...

## Product Surfaces

...

## Provider And Integration Boundaries

...

## Research And Measurement Integrity

...

## Parked Future Work

PARKED is memory, not backlog.

## Historical / Archive

Historical context only.
```

## Success Criteria

The cleanup works if a future agent can answer these in under five minutes:

- What is Lyra's current product loop?
- Which docs can authorize code?
- Which docs are parked?
- Which public docs are derivative?
- Can provider data mark a task complete?
- Can passive capture run now?
- Can context switching become a score?
- Which doc wins when docs conflict?

Expected answer to the last question:

```text
The newest active authority doc wins, but historical sections never override
current Manifesto/AUTHORITY/Cortex/provider/exposure boundaries.
```

