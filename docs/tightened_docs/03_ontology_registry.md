# 03 Ontology Registry

**Status:** Historical audit snapshot from 2026-05-08. Current authority lives
in `docs/AUTHORITY.md`, active contracts, and registered runtime owners.

**Purpose:** Preserve the audited names, aliases, layer ownership, and status
as they existed at review time.

## Registry

| Concept | Canonical name | Aliases | Layer | Type | Measurement space | Source files | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Planned active time | `planned_active_minutes` | `planned_duration_minutes`, `P` | instrumentation/Cortex | observed | minutes | `models.py`, `cortex.py` | canonical in Cortex, legacy DB name active |
| Executed active time | `executed_active_minutes` | `executed_duration_minutes`, `E` | instrumentation/Cortex | observed | minutes | `models.py`, `stopwatch_manager.py`, `cortex.py` | canonical in Cortex, legacy DB name active |
| Wall-clock elapsed | `wall_clock_elapsed_minutes` | `wall_clock_minutes`, `W` | instrumentation/Cortex | derived from timestamps | minutes | `StopwatchSession.wall_clock_minutes`, `cortex.py` | canonical in Cortex |
| Paused time | `paused_minutes` | `total_paused_minutes`, `B` | instrumentation/Cortex | observed/derived | minutes | `StopwatchSession`, `PauseEvent`, `cortex.py` | canonical in Cortex |
| Execution multiplier | `execution_multiplier` | `bias_factor`, `m` | derived metrics/Cortex | derived | ratio `E/P` | `cortex.py`, `bias_factor_service.py` | canonical name; `bias_factor` legacy |
| Log execution multiplier | `log_execution_multiplier` | `z` | Cortex/statistical | derived | log-ratio | `cortex.py` | canonical v0 |
| Legacy duration delta | `duration_delta_minutes` | delta | legacy analytics | derived | minutes, `planned - executed` | `models.py:270`, `analytics.py`, frontend task rows | legacy active |
| Cortex active delta | `active_delta_minutes` | none | Cortex | derived | minutes, `executed - planned` | `cortex.py`, contract | canonical v0 |
| Readiness input | `self_assessed_readiness` | `pre_task_readiness`, readiness | instrumentation | self_reported | ordinal 1-5 | `models.py`, readiness modal | legacy name active; canonical wording should include self-assessed |
| Reflection input | `self_reported_reflection` | `post_task_reflection`, focus, reflection | instrumentation | self_reported | ordinal 1-5 | `models.py`, reflection modal | legacy name active; semantic drift risk |
| Cognitive shift magnitude | `readiness_reflection_gap` | `discrepancy_score` | derived metrics | derived | ordinal difference | `models.py:284` | legacy name conflict |
| Signed cognitive shift | `signed_readiness_reflection_shift` | `signed_discrepancy` | derived metrics | derived | ordinal difference | `models.py:294` | legacy name conflict |
| Initiation delay | `initiation_delay_minutes` | start delay | instrumentation | derived from timestamps | minutes | `StopwatchManager.start` | active canonical |
| Pause event | `pause_event` | interruption row | instrumentation | observed | event | `PauseEvent`, `stopwatch_manager.py` | canonical |
| Pause reason | `pause_reason` | break reason | instrumentation | self_reported/selected | enum/string | `PauseEvent`, UI pause menu | active but semantic drift risk |
| Pause confidence | `pause_prediction_confidence` | confidence | inference | heuristic | unit interval | `pause_predictor.py` | active heuristic, not Cortex-certified |
| Resume confidence | `resume_prediction_confidence` | confidence | inference | heuristic | unit interval | `resume_predictor.py` | active heuristic |
| Flow | `flow_hypothesis` | flow | inference | latent/inferred | class label | `inference_engine.py`, `jarvis_tools.py`, docs | useful but dangerous |
| Friction | `friction_hypothesis` | friction | inference | latent/inferred | class label | `inference_engine.py`, `jarvis_tools.py`, docs | useful but dangerous |
| Scope creep | `scope_creep_hypothesis` | scope inflation, expanding topology | inference/Cortex topology | inferred | class/topology | `inference_engine.py`, `cortex.py`, scope bullet fields | conflicting evidence quality |
| Topology | `execution_topology` | bounded, expanding, fragmented, biological | Cortex | inferred hypothesis | class label | `cortex.py`, contract | canonical v0 as hypothesis only |
| Calibration | `planning_calibration` | bias, self-calibration | derived/inference | latent/derived depending use | varies | `bias_factor_service.py`, analytics, docs | overloaded; use carefully |
| TruthGap | none | truth gap | speculative | latent/speculative | conflicting | user formalization, Cortex forbidden list | not implemented; do not canonicalize yet |
| Prediction error | `prediction_error` | PE | future Cortex Phase 2 | derived/inferred | likely log-ratio residual | contract follow-on only | deferred |
| Readiness calibration error | `readiness_calibration_error` | CE | future Cortex Phase 2 | inferred | ordinal/log mapping | not implemented | deferred |
| Archetype | `archetype` | behavioral cluster | inference/exposure | survey-derived + inferred | category/posterior | `Archetype`, `ArchetypeAssignment`, proximity service | active but identity-overclaim risk |
| Archetype sigma | `prior_sigma` | sigma | inference | model parameter | ratio dispersion | `Archetype`, `archetype_proximity_service.py` | active in proximity; not used in bias blend |
| Cascade risk | `cascade_score` | skip propagation | analytics/inference | derived heuristic | probability | `analytics.py` | active heuristic |
| Recovery latency | `recovery_latency` | pause recovery | operator tooling | derived | minutes | `jarvis_tools.py`, pause/resume data | operator-only, not fully surfaced |
| Reflection exposure | `reflection_impression` | reflection view | exposure | observed intervention | event | `ReflectionViewLog` | active partial exposure ledger |
| Calibration nudge | `calibration_nudge_event` | creation nudge, stop nudge | exposure/intervention | intervention record | event | `CalibrationNudgeEvent`, `ReflectionViewLog` | active, contamination-sensitive |
| Retired model enrichment | `llm_enrichment` | semantic parser | historical integration | inferred suggestion | JSON/status | task `llm_*` fields, migrations 036/039 | retired; columns retained for lineage/export/delete only |
| JARVIS hypothesis | `jarvis_hypothesis_proposal` | pattern hypothesis | operator tooling | speculative | structured proposal | `jarvis_tools.py`, `JarvisInvocation` | operator-only |

## Lineage Findings

1. `bias_factor` is no longer mathematically vague in code: it is
   `executed / planned` in `bias_factor_service.py`, but the name remains a
   legacy/product alias. Cortex canonicalizes it as `execution_multiplier`.
2. `discrepancy` is overloaded. In `models.py`, it means readiness/reflection
   shift. In prose, it can refer to plan/execution gap. This must not be used as
   a new canonical metric name.
3. `flow`, `friction`, and `scope_creep` are implemented as deterministic
   classes, but Cortex classifies them as latent hypotheses. The code can keep
   returning them only if consumers preserve uncertainty.
4. `prior_sigma` is not dead globally. It is used by
   `archetype_proximity_service.py`, but it is not used by Rule 13
   `bias_factor_final` blending.

## Canonicalization Recommendations

- Keep DB field names for compatibility.
- Add no new concept name unless this registry is updated.
- Use Cortex names in new docs/code comments when discussing measurement:
  `execution_multiplier`, `log_execution_multiplier`,
  `self_assessed_readiness`, and `self_reported_reflection`.
- Avoid the bare word `discrepancy` in new code.
