# 08 Dead Theory Registry

**Purpose:** Track unused, dormant, superseded, dangerous, or unresolved theory.

## Registry

| Item | Evidence | Classification | Rationale | Action |
| --- | --- | --- | --- | --- |
| TruthGap scalar | not implemented in code; appears only in current formalization discussion and Cortex forbidden list | dormant/speculative | Conflicting definitions existed; not safe as single scalar | archive as concept; split into prediction error and self-report calibration later |
| `prior_sigma` | schema field and used by `archetype_proximity_service.py`, not Rule 13 blend | unresolved | Not dead globally, but disconnected from `bias_factor_final` | document as proximity-only until Phase 2 variance model |
| `llm_priority` | data inventory marks dark/retire; task has `llm_priority` | dangerous/dormant | Priority column does not appear as canonical task field | freeze writer unless current UI proves use |
| Old `duration_delta_minutes` as core metric | active in analytics/UI | superseded for Cortex | Sign conflicts with `active_delta_minutes` | keep legacy, forbid new Cortex use |
| `discrepancy_score` name | active Task property | conflicting | Means self-report shift, not plan/execution gap | keep field, avoid expanding name |
| Valence classes as outcome truth | active inference | dangerous if reified | Flow/friction are latent hypotheses | keep operator/research, do not persist as fact |
| `bias_factor` name | active API/product alias | legacy | Canonical Cortex term is execution multiplier | keep alias, document deprecation path later |
| Insight confidence `low/medium/high` | active analytics/frontend | conflicting | Calibration contract uses cold/tentative/confirmed | freeze expansion; migrate terminology when safe |
| Archetype identity labels | active frontend | dangerous | Can become identity claims | keep with caps/gates; audit copy |
| JARVIS pattern proposals | active operator tooling | speculative | LLM-generated hypotheses can sediment | require hypothesis log promotion/rejection |
| `docs/inference_engine_architecture.md` Phase 3 draft | docs active, code partial | unresolved | Some architecture exists; user-facing carriers deferred | keep, update when inference expands |
| `docs/parked_ideas.md` | large idea backlog | dormant/speculative | Valuable but not canonical | archive-like; never use as implementation truth |
| Archive migration SQL | archive | legacy | manual Supabase history | keep archive, do not execute without migration check |
| Notebooks analytics | notebook | legacy/prototype | exploratory; may encode old assumptions | archive or label exploratory |

## Dead Theory Test

A concept is dead or dangerous when:

- it has a name but no current owner,
- it has fields but no validated consumer,
- it appears in docs but not code,
- code implements it but docs no longer define it,
- it uses psychological language without measurement support,
- it cannot be falsified with current observables.

## Immediate Findings

1. The repo contains more theory than active implementation.
2. Some "dead" items are not removable because they preserve research lineage.
3. The right action is not deletion first. It is classification, owner assignment,
   and archival policy.
