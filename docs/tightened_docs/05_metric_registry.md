# 05 Metric Registry

**Purpose:** Formula, units, sign conventions, valid data profile, and risks.

## Canonical Cortex Metrics

| Metric | Formula | Units | Sign/convention | Valid profile | Status |
| --- | --- | --- | --- | --- | --- |
| `planned_active_minutes` | DB planned duration | minutes | positive duration | all task rows with `P > 0` | canonical |
| `executed_active_minutes` | DB executed duration | minutes | excludes pause time | `measured_execution` | canonical |
| `wall_clock_elapsed_minutes` | executed end - executed start | minutes | includes pauses | measured rows with timestamps | canonical |
| `paused_minutes` | total pause duration | minutes | non-negative | pause/session rows | canonical |
| `execution_multiplier` | `E / P` | ratio | `>1` overrun, `<1` underrun | `measured_execution` | canonical |
| `log_execution_multiplier` | `log(E / P)` | log-ratio | positive overrun, negative underrun | `measured_execution` | canonical |
| `active_delta_minutes` | `E - P` | minutes | positive overrun | `measured_execution` | canonical |
| `wall_delta_minutes` | `W - P` | minutes | positive wall overrun | measured rows with timestamps | canonical |

## Legacy Active Metrics

| Metric | Formula | Units | Risk | Owner |
| --- | --- | --- | --- | --- |
| `duration_delta_minutes` | `planned - executed` | minutes | opposite sign from Cortex active delta | `Task` property, analytics/frontend |
| `bias_factor` | `executed / planned` | ratio | name sounds moral; legacy alias | `bias_factor_service.py` |
| `bias_factor_final` | `(1-w)*archetype_prior + w*personal_ratio` | ratio | low-n heuristic; not Bayesian posterior | `bias_factor_service.blend` |
| `bias_factor_mean` | mean of per-session `executed/planned` | ratio | unweighted; differs from sum-ratio | `bias_factor_service._bias_cell` |
| `discrepancy_score` | `abs(post - pre)` | ordinal difference | ambiguous name; not duration discrepancy | `Task` property |
| `signed_discrepancy` | `post - pre` | ordinal difference | self-report shift, not objective outcome | `Task` property |
| `cascade_score` | `P(skip N+1 | skip N)` | probability | skip causality not established | `analytics.py` |
| `deadline delay_minutes` | executed end - deadline | minutes | positive miss, negative met early | `TaskDeadlineOutcome` |
| `context_switching_footprint` | derived from task switches, interruption chains, parked work, reentry latency, and bounded pause overhead | mixed summary | descriptive footprint, not causal cost | future `pause_process` / `measured_execution` profile |
| `open_thread_end_of_day_count` | parked or interrupted work still unresolved at local day end | mixed summary | recovery load indicator, not failure score | future `pause_process` / `measured_execution` profile |
| `reentry_resolution_type` | resumed, completed later, rescheduled, dropped, marked irrelevant, stale/open at day end, or auto-closed | categorical | required to know whether a switch mattered | future `pause_process` / `measured_execution` profile |
| `time_to_resolution_minutes` | time from switch/pause/miss to explicit resolution | mixed summary | censored when unresolved | future `pause_process` / `measured_execution` profile |

## Heuristic Confidence Metrics

| Metric | Formula/logic | Risk |
| --- | --- | --- |
| insight confidence | `low/medium/high` in `analytics.py` from count thresholds | conflicts with calibration contract `cold_start/tentative/confirmed` |
| R2 confidence | `cold_start/tentative/confirmed` | better governed; still count-only |
| pause confidence | `0.30 + sample + dispersion` capped at `0.95` | uses absolute dispersion scale |
| resume confidence | `MIN_CONFIDENCE + 0.02*n` capped | count-driven, weak calibration |
| deadline match confidence | heuristic/LLM score | semantic score, not probability |
| archetype posterior score | softmax over damped likelihoods | model-dependent posterior-like value, identity risk |

## Invalid Or Forbidden Transformations

- `planned / executed` for Cortex inference.
- `1 / execution_multiplier`.
- mixing raw minutes, ratios, and logs in one model equation.
- averaging raw ratios without noting task-duration weighting.
- using retroactive rows in learning metrics.
- treating confidence tier as probability.

## Contamination Risks By Metric

| Metric | Contamination risk |
| --- | --- |
| `planned_active_minutes` | user saw prior/nudge before planning; imported deadlines constrain slots |
| `executed_active_minutes` | forgotten timer, auto-close, pause deduction bugs |
| `paused_minutes` | missing pause events, retroactive confirmations, data-quality flags |
| `self_assessed_readiness` | scale drift, social desirability, system exposure |
| `self_reported_reflection` | memory reconstruction, desire to validate effort |
| `scope_bullet_count_*` | bullet decomposition vs true expansion |
| `bias_factor_final` | priors may not match task topology/category semantics |
| `archetype_proximity` | non-iid tasks, outlier winsorization, label internalization |
| `context_switching_footprint` | reverse causality, task difficulty, emergencies, overload, forgotten timers, and exposure to prior switch insights |
| `fragmentation_score` / `switching_score` | forbidden user-facing scalar; turns recoverable open-thread state into judgment |

## Required Metric Documentation

Every new metric must document:

- formula
- units
- sign convention
- clean-data profile
- aggregation rule
- excluded rows
- whether it is observed, self_reported, derived, inferred, or latent
- whether user exposure can change future values
