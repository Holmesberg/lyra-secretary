# 09 Semantic Conflicts

**Purpose:** Document conflicts without silently resolving them.

## Conflict Register

| Conflict | Locations | Nature | Severity | Recommendation |
| --- | --- | --- | --- | --- |
| `duration_delta_minutes` vs `active_delta_minutes` | `Task.duration_delta_minutes`, Cortex contract | opposite sign conventions | critical | keep legacy, use explicit conversion, future deprecation plan |
| `bias_factor` vs `execution_multiplier` | `bias_factor_service.py`, Cortex contract | same ratio, different semantic framing | high | Cortex name canonical; alias legacy |
| `discrepancy` duration vs self-report gap | models/docs/prose | one term means multiple concepts | high | ban bare `discrepancy` in new metrics |
| `confidence` as sample tier vs probability | analytics, predictors, LLM ranking | same word, different math | high | require confidence semantics field |
| `readiness` as input vs state | DB/UI/docs | self-report overloaded into capacity | high | use self-assessed wording |
| `reflection` as input vs focus/quality | DB/UI/docs | self-report overloaded into cognitive state | high | use self-reported reflection/focus only with caveat |
| `flow` as valence vs latent state | inference/docs/UI possible | deterministic class vs psychological construct | high | phrase as hypothesis |
| `scope_creep` vs `expanding` topology | inference_engine vs Cortex | related but not identical | medium/high | centralize topology vocabulary later |
| `cold_start/tentative/confirmed` vs `low/medium/high` | calibration contract vs analytics/frontend | competing confidence taxonomies | medium/high | freeze old terms; migrate by surface |
| external deadlines in planning calibration | deadline/integration docs vs older analytics | imported constraints contaminate native planning | high | use Cortex `planning_calibration` profile |
| archetype posterior vs survey archetype | archetype_service/proximity/frontend | static assignment and dynamic proximity coexist | medium/high | preserve distinction in UI/docs |
| LLM candidate confidence vs heuristic confidence | `llm_parser.py`, `deadline_heuristic.py` | different score origins | medium | do not compare as probability |

## Do Not Auto-Resolve

The following require design decisions, not mechanical rename:

- replacing `duration_delta_minutes` in public APIs
- renaming `bias_factor` in existing frontend/product copy
- changing confidence taxonomy in user-facing insights
- reclassifying `flow/friction` as topology instead of valence
- removing archetype labels

## Canonicalization Direction

Use the Cortex vocabulary for new measurement work:

- `execution_multiplier`
- `log_execution_multiplier`
- `active_delta_minutes`
- `self_assessed_readiness`
- `self_reported_reflection`
- `execution_topology`

Keep legacy aliases documented until all consumers migrate.
