# 06 Inference Registry

**Purpose:** Map implemented inference paths, assumptions, thresholds, outputs,
and validity risks.

## Implemented Inference Paths

| Path | Inputs | Output | Method | Thresholds | Status | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| Category inference | title/description keywords | `Task.category` | symbolic keyword mapping | local lookup | active heuristic | category semantics can drift |
| Deadline heuristic | title/description + bindable deadlines | candidates, auto-bind | symbolic scoring | 0.6 score, 0.2 margin, brittle guard | active heuristic | confidence is score, not probability |
| LLM enrichment | task text + deadlines | `llm_*` suggestions | LLM + candidate ranking | 0.85/0.45 tiers | active assistive | external vendor, hallucination, not canonical |
| Bias factor cascade | executed tasks by category/time/duration | personal cell ratio | statistical aggregate | first cell with `>=3` sessions | active legacy | low-n instability |
| Bias blend | personal cell + archetype prior | `bias_factor_final` | heuristic shrinkage | `min(1,n/30)` | active legacy | called canonical in legacy, not Bayesian |
| Valence classifier | duration ratio, reflection, pauses, scope | flow/friction/etc | deterministic rules | 15%, reflection cutoffs, pause count | research-grade | latent labels can be reified |
| Disagreement classifier | readiness, reflection, ratio | disagreement type | deterministic rules | 1-5 cutoffs, 1.3x | research-grade | self-report semantics unstable |
| Pause predictor | pause history + active task | predicted pause | heuristic/statistical medians | >=7 days, >=5 samples, 2-3 min lead, confidence >=0.40 | active intervention | prediction changes future pause behavior |
| Resume predictor | pause duration history + paused session | resume banner | percentile heuristic | p75, floor, 30-min cold cap | active intervention | induced resume behavior |
| Archetype scoring | survey responses | archetype assignment | scoring rules | survey-specific | active | identity label risk |
| Archetype proximity | recent tasks + priors/sigma | posterior-like distribution | damped likelihood/softmax | bias factor cap [0.30,3.0] | active research | model assumptions strong |
| Cascade analytics | skip sequences | cascade score | aggregate probability | day/session order | active analytics | causal interpretation not proven |
| Deadline shape | deadline-bound tasks/outcomes | met/delay aggregates | reconciliation aggregates | deadline outcome rows | active analytics | external imports must be separated |
| Cortex diagnostics | task/session/pause rows | counts/exclusions/topology | read-time projection | Cortex profiles | active governance | not inference; diagnostic only |
| JARVIS pattern proposal | operator aggregate tools | hypothesis proposal | LLM synthesis | tool schema requires falsifier/general tag | operator-only | AI-generated entropy risk |

## Registered But Not Implemented

| Candidate | Inputs | Intended output | Status | Risk |
| --- | --- | --- | --- | --- |
| `description_incomplete_at_deadline` | task/deadline binding, `Deadline.due_at_utc`, task description/scope snapshot, task edit timestamps | implicit planning-depth signal | Phase 6 candidate; registered in `docs/data_utilization_inventory_2026_05_02.md` Revision 2 | description completeness is not scope truth; requires boundary snapshot and provenance |

## Inference Pretension Warnings

1. `confidence` often means sample-size tier or heuristic score. It must not be
   read as calibrated probability unless specifically validated.
2. `flow` and `friction` are deterministic pattern labels over sparse proxies.
   They do not measure hidden states.
3. `archetype_posterior` is mathematically explicit, but the label can overrun
   evidence and become identity.
4. Deadline `confidence` mixes heuristic string overlap and LLM semantic
   ranking; neither is ground truth.
5. JARVIS can summarize only exposed tool payloads. Its own prompt explicitly
   says not to speculate outside `covered_signals`; this must remain enforced.

## Operator-Only Inference

Currently operator-only:

- JARVIS chat and tools
- `GET /v1/analytics/behavioral_signature`
- Cortex diagnostics
- many dark-column analytics

Operator-only means "not safe for non-operator interpretation," not "valid."

## User-Facing Inference

Current user-facing or near-user-facing:

- `/insights`
- calibration nudges
- micro-mirrors
- pause prediction banners
- resume prediction banners
- archetype UI

These surfaces can contaminate future observations. Phase 1 exposure ledger is
required before adaptive inference learns from exposed behavior.

## Required Future Registry Fields

Every new inference must declare:

- inputs and their provenance
- clean-data profile
- output type: derived, inferred, latent hypothesis
- threshold lineage
- confidence semantics
- falsifier
- exposure sensitivity
- eligible audiences: operator-only, trusted cohort, all users
