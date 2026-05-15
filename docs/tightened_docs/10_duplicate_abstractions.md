# 10 Duplicate Abstractions

**Purpose:** Identify repeated logic and recommend canonical owners.

## Duplicate Registry

| Abstraction | Duplicates | Risk | Canonical owner recommendation |
| --- | --- | --- | --- |
| time-of-day bucketing | `analytics.py`, `bias_factor_service.py`, JARVIS helpers | cell drift corrupts bias/insight comparisons | move to shared utility or Cortex metric helper |
| confidence tiers | analytics `_confidence`, bias `_confidence`, inference R2 tiers, JARVIS `_confidence_tier` | same word means different thresholds | `inference_engine.py` for user-facing; local names for heuristic scores |
| execution ratio | analytics, bias factor, Cortex, archetype proximity | sign/orientation drift | Cortex `execution_multiplier` |
| clean-data filtering | analytics queries, bias factor lookup, archetype proximity, Cortex | inconsistent exclusions | Cortex profiles; call helper queries where possible |
| valence classification | `inference_engine.py`, JARVIS imports, docs R9 | duplicate if reimplemented elsewhere | `inference_engine.py`, but label as inferred |
| deadline matching | `deadline_heuristic.py`, `llm_parser.py`, legacy parser binding | multiple confidence semantics | `deadline_heuristic.py` for deterministic; LLM stays suggestion-only |
| pause recovery analysis | pause predictor, resume predictor, JARVIS dark columns | repeated pause filtering | Cortex `pause_process` query profile |
| reflection engagement | `ReflectionViewLog` endpoint, analytics, JARVIS | exposure semantics can diverge | Exposure ledger Phase 1 owner |
| category mapping | DB seed, frontend category list, docs priors | label semantic drift | category registry doc or shared API |
| external-source exclusion | docs, deadline analytics, Cortex planning profile | missed filters contaminate H1 | Cortex profile plus tests |

## High-Risk Duplicate: JARVIS Tools

`backend/app/services/jarvis_tools.py` is 2007 lines and contains many local
aggregation functions. It is valuable operator tooling, but it is also the
largest risk for duplicate ontology and AI-generated sediment.

**Recommendation:** freeze new JARVIS analytics until shared metric/query owners
exist for any new signal.

## Migration Strategy

1. Do not extract everything immediately.
2. For each duplicate, choose an owner only when the next change touches it.
3. Add regression tests before moving logic.
4. Keep aliases in output payloads until frontend/API consumers migrate.
5. Preserve old docs as lineage but mark superseded.

## Do Not Abstract Prematurely

Some duplication is protective while semantics are unstable. Example:

- pause predictor confidence and user-facing confidence tiers should not share a
  function until their meanings are made compatible.

Traceability is more important than elegance in this phase.
