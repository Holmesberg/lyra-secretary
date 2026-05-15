# 13 Cleanup Recommendations

**Purpose:** Classify major concepts/modules as KEEP, FREEZE, DEPRECATE, or ARCHIVE.

## KEEP

| Item | Reason | Risk | Maintenance |
| --- | --- | --- | --- |
| `Task`, `StopwatchSession`, `PauseEvent` | strongest measurement substrate | high value, high sensitivity | keep stable |
| state machine | protects measurement lifecycle | load-bearing | keep strict |
| multi-user scoping tests/layer | prevents cross-user leaks | critical | keep and extend |
| `voided_at` discipline | contamination guard | critical | keep |
| Cortex contract and tests | measurement governance | emerging | keep, document all changes |
| pause event history | high-resolution behavioral signal | strong | keep |
| deadline outcome snapshots | reproducibility | strong | keep |
| `ReflectionViewLog` | exposure substrate | incomplete but valuable | keep |

## FREEZE

| Item | Reason | Risk if expanded |
| --- | --- | --- |
| `analytics.py` monolith | too many layers in one module | duplicate metric drift |
| `jarvis_tools.py` analytics expansion | already very large | AI-generated semantic sediment |
| valence class vocabulary | latent labels not validated | ontology inflation |
| archetype label surfaces | identity overclaim risk | user internalization |
| pause/resume predictor thresholds | intervention-sensitive | self-reference loops |
| Rule 13 blend formula | pre-registered legacy | low-n overclaim if tweaked casually |
| insight confidence copy | taxonomy conflict | semantic inconsistency |

## DEPRECATE

| Item | Deprecation target | Rationale |
| --- | --- | --- |
| new uses of `duration_delta_minutes` | `active_delta_minutes` or `execution_multiplier` | sign conflict |
| bare `discrepancy` naming | explicit self-report or time gap names | ambiguity |
| `bias_factor` in new Cortex code | `execution_multiplier` | legacy alias |
| `low/medium/high` confidence in new inference | `cold_start/tentative/confirmed` or explicit score semantics | conflict |
| title-only topology inference | unknown by default | weak evidence |

## ARCHIVE

| Item | Why | Action |
| --- | --- | --- |
| old manual migration SQL | historical deployment lineage | keep in archive, do not run |
| old video scripts/product docs | not architectural truth | keep as product-history archive |
| notebooks `.venv` | environment artifact | consider removing from repo if tracked |
| one-off check scripts | useful but non-canonical | archive or label scripts as operator utilities |
| old TruthGap single-scalar formulations | conflicting theory | archive in formalization notes, not implementation |

## Do Not Delete Yet

- `prior_sigma`: active in archetype proximity.
- `llm_*` task fields: active async enrichment path.
- `ReflectionViewLog.outcome`: future exposure/intervention value.
- archive docs: useful lineage for why rules exist.

## Cleanup Priority

1. Add labels/owners before deletion.
2. Freeze high-risk expansion points.
3. Migrate names only with compatibility aliases.
4. Archive speculative theory without erasing lineage.
