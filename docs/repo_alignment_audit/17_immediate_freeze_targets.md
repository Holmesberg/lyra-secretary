# 17 Immediate Freeze Targets

**Purpose:** Identify modules, concepts, and heuristics that should stop growing
until validation/governance catches up.

## Module Freeze Targets

| Target | Freeze scope | Reason |
| --- | --- | --- |
| `backend/app/api/v1/endpoints/analytics.py` | no new metric families | already mixes endpoint, aggregation, inference, and user-facing insights |
| `backend/app/services/jarvis_tools.py` | no new behavioral tools without registry owner | high AI-sediment and duplicate-abstraction risk |
| `backend/app/services/inference_engine.py` | no new latent labels | valence/disagreement already need validation |
| `backend/app/services/pause_predictor.py` | no threshold tuning without pre-registration | intervention-sensitive |
| `backend/app/services/resume_predictor.py` | no threshold tuning without exposure plan | intervention-sensitive |
| `frontend/components/archetype-*` | no stronger identity copy | archetype internalization risk |
| `frontend/app/(app)/insights/page.tsx` | no new inferred claims until exposure ledger plan | user-facing contamination |
| `frontend/components/new-task-modal.tsx` | no stronger pre-task suggestions | anchors planning signal |

## Concept Freeze Targets

| Concept | Freeze reason |
| --- | --- |
| flow | latent construct currently rule-classified |
| friction | latent construct currently rule-classified |
| execution quality | would collapse independent causes into one scalar |
| TruthGap | conflicting definitions, not implemented |
| productivity score | forbidden by Cortex |
| archetype identity | high internalization risk |
| confidence | overloaded; must be typed before expansion |
| discrepancy | overloaded; avoid new uses |
| scope creep | proxy validity unresolved |
| user-burden variables | frozen unless offset by product simplification and explicit identifiability gain |

## Heuristic Freeze Targets

| Heuristic | Reason |
| --- | --- |
| `personal_weight = min(1,n/30)` | count-only, not Bayesian variance |
| pause confidence dispersion constant | scale assumption unvalidated |
| valence thresholds | latent labels and self-report dependence |
| deadline heuristic score thresholds | semantic score, not probability |
| archetype winsorization caps | model-specific; identity consequences |
| insight confidence thresholds | taxonomy conflict with R2 |

## API Freeze Targets

- Do not add new user-facing analytics endpoints before clean-data profile
  declaration.
- Do not add new reflection/telemetry types without schema docs.
- Do not add non-operator JARVIS access.
- Do not add Cortex schema fields in Phase 0.
- Do not add new required user inputs for research purposes.
- Do not add new subjective scales, questionnaires, or check-ins before a
  successor product-research contract justifies the burden.

## Structural Refactor Freeze Gate

Do not continue broad folder restructuring until these safeguards exist:

- characterization tests for representative Cortex outputs
- dependency DAG enforcement for backend layers
- centralized clean-data profile helpers
- unknown-propagation tests
- evaluation-version stamp checks
- read-only Cortex checks

Reason: moving files before semantic behavior is pinned can create clean-looking
architecture with inconsistent metric interpretation.

## What May Continue

- Bug fixes that preserve existing semantics.
- Tests that lock known behavior.
- Documentation that clarifies lineage and uncertainty.
- Read-time diagnostics that do not produce new user-facing claims.
- Cleanup that archives or labels theory without deleting research artifacts.

## Immediate Stop Condition

If a proposed change adds a psychological word, a confidence score, or a
behavioral class, pause and update the ontology registry first.
