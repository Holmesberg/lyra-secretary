# Cortex Contract v0

**Status:** Canonicalization contract. No schema migration, predictor, UI surface,
personalization, or psychological inference is authorized by this document.

**Purpose:** Freeze the measurement vocabulary and scientific safety rails for
Cortex Core v0 before any implementation expands the inference layer.

This document is an instrument contract, not a feature spec. It defines what Lyra
may treat as observed, what must remain derived, what is latent, and which
transformations are forbidden because they would corrupt measurement validity.

Structural refactor sequencing is governed by
`docs/cortex_refactor_guardrails.md`.

---

## 1. Phase Boundary

### Phase 0: Canonicalization

This is the current phase.

Allowed work:

- Canonical metric definitions
- Invariant validators
- Clean-data filters
- Event provenance rules
- Topology classification semantics
- Naming policy
- Derived metric views or read-time projections

Forbidden work:

- Inferring psychology
- Optimizing behavior
- Aggressive personalization
- Exposure/adaptation inference
- New user-facing claims
- New schema fields without invariant justification

Documentation rule:

- Every Cortex change must document the measurement contract it touches, the
  invariant it relies on, the clean-data profile it uses, and any uncertainty it
  leaves unresolved.
- If a change adds code but no documentation, the change is incomplete.

### Later Phases

Phase 1 is the exposure ledger: what the user saw, when, with what strength,
confidence, and delivery mode.

Phase 2 is adaptive inference: only after drift tracking, exposure tracking, and
variance tracking exist.

---

## 2. Canonical Variables

These are the only canonical Cortex duration variables.

| Symbol | Canonical name | Definition | Measurement space |
| --- | --- | --- | --- |
| `P` | `planned_active_minutes` | Planned active work duration | minutes |
| `E` | `executed_active_minutes` | Executed active work duration, excluding paused time | minutes |
| `W` | `wall_clock_elapsed_minutes` | End-to-end wall-clock elapsed time | minutes |
| `B` | `paused_minutes` | Total paused time | minutes |
| `m` | `execution_multiplier` | `E / P` | ratio |
| `z` | `log_execution_multiplier` | `log(E / P)` | log-ratio |
| `active_delta_minutes` | `active_delta_minutes` | `E - P` | minutes |
| `wall_delta_minutes` | `wall_delta_minutes` | `W - P` | minutes |

Interpretation:

- `execution_multiplier > 1`: execution ran longer than planned.
- `execution_multiplier = 1`: execution matched plan.
- `execution_multiplier < 1`: execution ran shorter than planned.
- `log_execution_multiplier = 0`: execution matched plan.
- Positive `log_execution_multiplier`: overrun.
- Negative `log_execution_multiplier`: underrun.

`P` must be greater than zero before computing ratio or log-ratio metrics. If
`P <= 0`, the derived metric is undefined and must be marked unknown.

---

## 3. Naming Policy

`execution_multiplier` is the canonical Cortex name for `E / P`.

`log_execution_multiplier` is the canonical statistical form.

`bias_factor` remains a legacy/product alias for execution multiplier where it
already exists in APIs, docs, or user-facing logic. Do not silently rename
existing public fields. New Cortex code should use the canonical name and may
include the legacy alias for backward compatibility.

`duration_delta_minutes` remains the legacy Lyra property with the existing sign
convention:

```text
duration_delta_minutes = planned - executed
positive = finished early
negative = took longer than planned
```

New Cortex code must not use `duration_delta_minutes` as the primary model
input. Convert explicitly to `active_delta_minutes = executed - planned` when a
minute-space Cortex model is required.

---

## 4. Observable, Derived, Latent

### Observed

Observed values are emitted by system instrumentation or direct user input.
They are not automatically true about psychology.

Examples:

- Timestamps
- Planned duration
- Executed duration
- Wall-clock duration
- Pause events
- Pause reasons
- Pause initiator
- Readiness input
- Reflection input
- Completion percentage input
- Deadline outcomes

### Derived

Derived values are computed from observed values. They must not be persisted as
ground truth.

Examples:

- Ratios
- Log-ratios
- Minute deltas
- Aggregates
- Confidence tiers
- Classification outputs
- Clean-data inclusion flags

### Latent

Latent constructs are hypotheses about hidden state. They must never be stored or
described as observed truth.

Examples:

- Flow
- Friction
- Cognitive load
- Execution quality
- Readiness state
- Calibration
- Self-model error
- Momentum
- Avoidance
- Recovery capacity

Hard rule: a latent label may only appear as an inferred hypothesis with
provenance, uncertainty, and a clean-data profile. It must never overwrite raw
observables.

---

## 5. Clean-Data Profiles

Every Cortex analysis must declare exactly one clean-data profile. If no profile
matches, the analysis is invalid.

### `measured_execution`

Use for measured plan-vs-execution calculations.

Include only rows where:

- Task state is `EXECUTED`
- `voided_at IS NULL`
- `initiation_status != 'system_error'`
- `initiation_status != 'retroactive'`
- `executed_duration_minutes IS NOT NULL`
- `planned_duration_minutes >= 5`

### `planning_calibration`

Use for estimating personal planning calibration.

Includes all `measured_execution` requirements, plus:

- Exclude tasks bound to externally imported deadlines.
- Tasks with no deadline binding remain eligible.

Rationale: externally imported deadlines constrain the time slot from outside
Lyra, so they mix user planning with external scheduling pressure.

### `pause_process`

Use for pause timing, pause reason, interruption, and recovery analysis.

Include only rows where:

- Pause row is real-time captured, not retroactive confirmation.
- `PauseEvent.self_reported_retroactively IS FALSE`
- Parent task is not voided.
- Joined `StopwatchSession.data_quality_flag IS NULL`
- Pause event has the fields required by the analysis.

Rationale: `data_quality_flag` is about pause metadata contamination, not all
duration data. It is mandatory for pause-process analysis.

### `descriptive_history`

Use for timelines, user history, export, and non-learning summaries.

May include retroactive rows, recovered rows, and externally imported context,
but must preserve provenance and must not update learning metrics.

---

## 6. Provenance Semantics

Every Cortex event or projection must carry provenance. If provenance is not
known, mark it `unknown`. Do not infer it.

| Provenance | Meaning |
| --- | --- |
| `observed` | Emitted by system instrumentation during normal use |
| `self_reported` | User-entered subjective report |
| `derived` | Computed from observables |
| `retroactive` | Reconstructed after the fact |
| `external_import` | Sourced from outside Lyra |
| `system_recovered` | Created or corrected by recovery jobs |
| `unknown` | Not identifiable from available data |

Unknown is a valid value. Guessing is not.

---

## 7. Topology Semantics

Topology labels describe task-execution shape. They are classification
hypotheses, not ground truth.

| Topology | Meaning | Minimum evidence |
| --- | --- | --- |
| `bounded` | Task has stable intended scope | No explicit expansion or fragmentation signal |
| `expanding` | Task scope grew during execution | Explicit scope signal, such as `scope_outcome = 'expanded'` or measured bullet-count growth |
| `fragmented` | Execution materially shaped by pauses or interruptions | Pause/interruption topology crosses an analysis-defined threshold |
| `biological` | Sleep, meal, body-process, or other biological task | Category or explicit task-mode evidence |
| `unknown` | Evidence is insufficient | Default fallback |

Rules:

- `unknown` is the default topology.
- Do not infer topology from task title alone unless the classifier declares that
  title-derived topology is heuristic and uncertain.
- `biological` tasks are excluded from cognitive calibration by default.
- `expanding` requires explicit scope evidence. Overrun alone is not scope
  expansion.
- `fragmented` requires pause or interruption structure. Pause count alone is a
  weak signal unless the analysis defines the threshold.

---

## 8. Minimal Cortex Event Envelope

Cortex Core v0 should project existing rows into this envelope when it needs a
shared event representation. This is a read-time contract over existing data, not
a new table requirement.

Exactly ten top-level fields:

```json
{
  "event_id": "string",
  "source": "string",
  "source_id": "string",
  "user_id": "string",
  "task_id": "string | null",
  "event_type": "string",
  "occurred_at": "iso-8601",
  "provenance": "observed | self_reported | derived | retroactive | external_import | system_recovered | unknown",
  "exposure_state": "none | exposed | intervention | unknown",
  "payload": {}
}
```

Envelope rules:

- `payload` contains copied observed fields only.
- Derived metrics must be computed from the envelope, not stored inside it.
- Latent labels must not appear in `payload`.
- If exposure state is unavailable, use `unknown`, not `none`.
- `event_id` must be deterministic if generated from an existing row.

---

## 9. Evaluation Versioning

Cortex projections must identify the contract version used to interpret raw
events.

`cortex_schema_version_at_evaluation` is an evaluation-time stamp, not a storage
version. It answers: "Which Cortex contract interpreted this row into metrics,
profiles, topology, and provenance?"

Rules:

- The stamp is required on diagnostics, exports, and any persisted research
  artifact produced from Cortex-derived projections.
- The stamp must not imply the underlying event was originally collected under
  that version.
- When a contract changes interpretation semantics, old events may be
  re-evaluated, but the output must carry the new evaluation version.
- Never compare Cortex-derived aggregates across evaluation versions without
  declaring the version boundary.

Current value: `cortex_contract_v0`.

---

## 10. Unknown Propagation

`unknown` is not neutral, bounded, zero, average, or missing-at-random.

Unknown values must survive projection and aggregation unless the analysis
explicitly declares a resolution rule.

Forbidden silent conversions:

- `unknown -> 0`
- `unknown -> neutral`
- `unknown -> bounded`
- `unknown -> average`
- `unknown -> clean`
- `unknown -> no exposure`

Allowed handling:

- preserve `unknown`
- exclude with a declared clean-data profile
- report an `unknown_count`
- resolve with an explicit rule documented next to the analysis

If unknowns are excluded, the denominator must say so.

---

## 11. Read-Only Cortex Boundary

Cortex Core v0 is physically a read-time projection layer.

Rules:

- Cortex modules must not call `db.add`, `db.delete`, `db.commit`,
  `db.flush`, mutation managers, Redis write methods, Notion clients, or
  notification senders.
- Cortex modules may read ORM rows and return derived projections.
- Cortex modules may raise invariant errors.
- Cortex modules must not repair data.

If an invariant violation requires data repair, the repair belongs in a
service, worker, or migration with its own documentation and tests.

---

## 12. Metric Immutability

Derived metrics are functions of raw observables only.

Rules:

- A derived metric must not depend on another derived metric unless the contract
  defines that dependency as a named transformation.
- A learning metric must not consume user-facing formatted copy.
- A learning metric must not consume a prior model output as if it were a raw
  event.
- Derived metrics must be recomputable from raw rows plus the evaluation
  version.

This prevents recursive amplification where one model's output becomes another
model's ground truth.

---

## 13. Inference Isolation

Inference may consume raw event rows, Cortex projections, and declared
clean-data profiles. It must not consume service-layer caches or UI state as
behavioral truth.

Rules:

- Inference code must not read Redis stopwatch/cache keys as training data.
- Inference code must not depend on TaskManager or StopwatchManager behavior
  except through persisted observables.
- Service-layer state may trigger an operational action, but not become
  evidence in a learning metric unless it is persisted with provenance.

---

## 14. Dependency Direction

Cortex refactors must preserve an acyclic dependency direction.

Allowed direction:

```text
api -> services -> cortex
api -> inference
workers -> services
workers -> inference
inference -> cortex
cortex -> db/models + core/utils only
```

Forbidden return paths:

```text
cortex -> services
cortex -> inference
inference -> services
inference -> api
services -> api
```

Import checks are not enough; CI must eventually enforce a dependency DAG over
module imports so indirect loops fail too.

---

## 15. Exposure Split At Inference Time

Exposure state must be available at the point of inference, not only at event
capture.

Minimum inference-time exposure classes:

- `observed_no_exposure`
- `observed_exposed_prediction`
- `observed_intervention`
- `observed_exposure_unknown`

Until Phase 1 exposure ledger exists, adaptive inference must not treat exposed
or unknown-exposure behavior as naturalistic training data by default.

---

## 16. Forbidden Transformations

These transformations are forbidden in Cortex code and Cortex-certified
analytics.

### 16.1 `planned / executed` for Cortex inference

Use `executed / planned`. The inverse silently flips the meaning of overrun and
underrun.

### 16.2 `1 / execution_multiplier`

This recreates the inversion problem and can reward pathological overruns in
quality-like formulas.

### 16.3 Mixed measurement spaces

Do not mix raw minutes, ratios, and logs in one model equation. A model must
choose its space:

- minute-space for additive human-readable time attribution
- ratio-space for direct multipliers
- log-ratio-space for statistical residuals and multiplicative factors

### 16.4 Single productivity score

No unified productivity, performance, worth, or quality score.

Lyra models calibration, topology, adaptation, and prediction error. It does not
score human worth.

### 16.5 Latent persistence

Do not persist `flow`, `friction`, `cognitive_load`, `execution_quality`,
`readiness_state`, `calibration`, or `self_model_error` as observed facts.

### 16.6 Reflection as truth

Readiness and reflection are self-report inputs. They are not direct measures of
focus, quality, cognition, or flow.

### 16.7 Silent intervention mixing

Do not analyze exposed or nudged behavior as naturalistic observation unless the
analysis explicitly conditions on exposure state.

### 16.8 Schema mutation without invariant justification

No new field is allowed unless the implementation states which invariant is
impossible without that field. If the invariant can be preserved by read-time
projection over existing rows, reject the field.

---

## 17. Review Criteria

Any Cortex v0 implementation must pass these checks before it is treated as
Cortex-certified:

- Every canonical variable has one definition and one sign convention.
- Every analysis declares a clean-data profile.
- Unknown provenance remains unknown.
- Derived metrics are computed, not persisted as truth.
- Latent constructs are hypotheses, not observables.
- Topology labels have an `unknown` fallback.
- Ratio orientation tests prove `E / P` is canonical.
- Log symmetry tests prove equal inverse multipliers have equal-magnitude,
  opposite-sign `z` values.
- Retroactive rows do not update learning metrics.
- Exposure/adaptation claims are absent from v0.
- Unknown values propagate or are excluded with declared denominator semantics.
- Cortex projections carry `cortex_schema_version_at_evaluation` where exported
  or persisted for research.
- Cortex modules remain read-only.
- Dependency DAG checks prevent Cortex/inference return paths into services.

---

## 18. Implementation Status And Follow-On Work

Implemented in Cortex Core v0:

1. `backend/app/services/cortex.py` computes canonical variables from existing
   rows at read time.
2. `backend/tests/test_cortex_contract_v0.py` covers ratio orientation, log
   symmetry, clean-data exclusions, unknown-default behavior, payload
   restrictions, operator-only diagnostics, and cross-user non-leak behavior.
3. `GET /v1/analytics/cortex/diagnostics` exposes an operator-only diagnostic
   projection. It is not a user-facing surface and must not be placed on
   first-paint render paths.

Still deferred:

1. Defer exposure ledger to Phase 1.
2. Defer adaptive inference, readiness curves, prediction error, and response
   typology to Phase 2.
3. Defer any schema migration until the invariant that requires it is stated in
   this contract or a successor contract.
4. Add guardrail tests for read-only Cortex, dependency DAG direction,
   unknown propagation, and evaluation-version stamping before structural
   module moves continue.

---

## 19. Open Epistemic Debt

This contract is a containment layer. It does not validate the behavioral model
or retire older heuristic systems. The following risks are intentionally visible
and must not be smoothed over in future Cortex work.

### 19.1 Exposure state is underspecified

The v0 envelope uses `none | exposed | intervention | unknown` only because v0
does not perform exposure/adaptation inference.

Phase 1 will likely need finer distinctions, such as:

- user saw an insight
- user acknowledged it
- user engaged with it
- user behaviorally acted on it
- user received repeated exposure
- user ignored it
- user suppressed or avoided it

Until then, exposure claims must stay coarse and conservative.

### 19.2 Topology can become semantic drift

Topology labels must describe execution-shape geometry, not psychology or
personality. In particular, `fragmented` means the execution trace was materially
shaped by pauses or interruptions. It does not mean scattered, unfocused,
undisciplined, or cognitively weak.

### 19.3 Self-report scale semantics can drift

Readiness and reflection are self-report inputs. Their meaning can drift across
users, cohorts, cultures, interventions, and time. Future code should prefer
explicit names such as `self_assessed_readiness` when adding new Cortex-facing
interfaces. Existing field names remain legacy and must be interpreted through
this contract.

### 19.4 Low-n shrinkage is not Bayesian evidence

The existing `personal_weight = min(1.0, n / 30)` rule is a sample-count
interpolation heuristic, not a Bayesian posterior. At `n = 1`, empirical
variance is not identifiable. Phase 2 work must either model prior variance and
stationarity explicitly or avoid presenting low-n values as posterior certainty.

### 19.5 Pause confidence uses an unresolved scale constant

Existing pause prediction code uses an absolute timing scale such as `stdev / 30`
in confidence logic. That denominator is a modeling assumption. It is not
certified by this contract and may be wrong across long tasks, short tasks, and
different topology classes.

### 19.6 `prior_sigma` is ghost ontology until activated or retired

`Archetype.prior_sigma` exists in schema and some proximity logic, but it is not
part of the canonical Cortex v0 metric layer. Phase 2 must either activate it as
a real uncertainty parameter or explicitly deprecate it in the modeling
contract.

### 19.7 Delta sign conventions now coexist

`duration_delta_minutes = planned - executed` remains a legacy Lyra convention.
`active_delta_minutes = executed - planned` is the Cortex minute-space
convention. Both exist for compatibility, but any new Cortex analysis must use
the Cortex sign convention explicitly. A future migration should define a
deprecation path for the legacy sign convention before it reaches new inference
code.

### 19.8 Scope evidence is not validated truth

Bullet-count growth can indicate scope expansion, but it can also indicate
decomposition, cognitive unloading, planning clarification, or formatting drift.
It is evidence for a topology hypothesis only. It is not a direct measurement of
scope growth.
