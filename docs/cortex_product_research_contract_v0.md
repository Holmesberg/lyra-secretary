# Cortex Product-Research Contract v0

**Status:** Active boundary contract.

**Purpose:** Define how LyraOS can operate as a low-friction product while
remaining a research-grade behavioral measurement system.

This contract does not authorize new inference, schema, predictors, or UI. It
defines the boundary between product behavior and research interpretation.

**Manifesto relationship:** this contract refines `MANIFESTO.md`; it does not
supersede it. Changes to product/research boundaries, exposure policy,
output-surface governance, or user-burden doctrine must update the manifesto or
explicitly document why no manifesto update is needed.

---

## 1. System Definition

LyraOS is a controlled observational system embedded in a product.

It is not pure research software and it is not a generic productivity app. It
has two coupled objectives:

1. preserve scientific validity of behavioral inference
2. preserve retention and low-friction execution under a fixed user-burden
   surface

The system objective is:

```text
maximize information gain per unit user friction
```

This means inference may become richer only when it is paid for by passive
signals, derived metrics, better uncertainty modeling, or clearer clean-data
profiles. It must not be paid for by casually adding user prompts.

LyraOS is not primarily an AI-powered productivity system. Its user-facing
research core is rule-governed, probabilistic, inspectable, longitudinal, and
epistemically constrained. AI systems may support enrichment, operator
orchestration, or interface assistance, but they must not become hidden
authorities over behavioral truth.

The stronger framing is:

```text
a behavioral measurement instrument with a productivity interface
```

The core system accumulates evidence, detects patterns probabilistically, and
progressively earns stronger inference rights. It must explicitly resist fake
intelligence, opaque personalization, and black-box confidence theater.

See `docs/behavioral_instrumentation_doctrine.md` for the doctrine note that
expands this principle.

---

## 2. Core Separation Principle

Product layer produces behavior.

Research layer interprets behavior.

Neither layer may define the other's semantics.

The product layer is judged by whether users can plan, execute, recover, and
return with minimal cognitive overhead.

The research layer is judged by whether its claims remain observable,
reproducible, uncertainty-aware, and falsifiable.

---

## 3. Fixed Observation Surface

The current user-burden surface is frozen by default.

Allowed existing user-burden inputs:

- task title and task text
- planned time or deadline when supplied by the user
- timer start, pause, resume, stop
- pause reason when already part of the current flow
- pre-task readiness where already part of the current flow
- post-task reflection where already part of the current flow
- completion percentage where already part of the current flow

Forbidden by default:

- new required user inputs for research
- new subjective rating scales
- new questionnaires
- new required post-task fields
- new identity/personality labels
- prompts whose only purpose is model enrichment

Exception rule:

A new user-burden variable requires a successor contract or explicit amendment
that states:

1. what invariant or identifiability gap cannot be solved passively
2. expected user-friction cost
3. retention risk
4. clean-data profile affected
5. what will be removed, shortened, or simplified to keep total burden stable
6. how the variable can be sunset if it fails validation

If this cannot be answered, the variable is rejected.

User attention is scarce scientific capital. Every prompt is both a product
friction cost and a potential measurement intervention. Ambiguity must not be
solved by defaulting to more questions; the preferred direction is sparse
explicit input plus dense passive structure.

Missingness is part of the behavioral topology. Tasks not started, ignored
prompts, absent readiness, skipped reflections, delayed initiation, and
unconfirmed repair candidates may be informative, but they must remain
provenance-aware absences rather than being converted into neutral defaults or
observed truth.

---

## 4. Product Layer Contract

### 4.1 Objective

The product layer minimizes friction while preserving behavioral observability.

It optimizes for:

- task execution flow
- usability stability
- retention through clarity
- low cognitive overhead
- deterministic state transitions
- fast interaction feedback

It does not optimize for research richness directly.

### 4.2 Product May

The product layer may:

- collect passive instrumentation emitted by normal use
- store user-provided task, timer, pause, reflection, and deadline inputs
- execute deterministic workflows
- emit raw event logs
- reduce latency
- simplify screens
- remove unnecessary prompts
- add one-click recovery affordances when they reduce user friction and preserve
  provenance

Missed deadlines may be marked completed directly from the overdue surface. This
is a product recovery affordance, not a claim that the deadline was completed on
time. Research code must use due time and completion time, not the current state
alone, when distinguishing late completion from on-time completion.

### 4.3 Product Must Not

The product layer must not:

- add required user inputs for research convenience
- expose latent constructs as observed facts
- display inferred psychological states as truth
- reshape UI to improve research signal quality at the expense of user flow
- introduce experimental prompts without exposure/intervention tagging
- optimize behavior to make the model look more accurate

### 4.4 Product Stability Rule

User interaction schema may change only when the primary justification is user
task completion, accessibility, latency, clarity, or bug repair.

Research value alone is insufficient.

### 4.5 Retrospective Done Affordance

The product may let a user mark an overdue PLANNED or SKIPPED task as done
without reopening the task or requiring additional fields.

Rules:

- It must not create a measured stopwatch trace.
- It must stamp `initiation_status='retroactive'`.
- It must remain excluded from Cortex measured-execution and planning-
  calibration clean-data profiles.
- It must not collect new required readiness, reflection, duration, or scope
  inputs.
- It may use the planned start/end as a retrospective placeholder only because
  this is a product recovery action, not research evidence.

Rationale: the user already expressed the semantic outcome ("done"). Forcing
the task back to PLANNED before completion adds friction without improving
measurement validity.

---

## 5. Research Layer Contract

### 5.1 Objective

The research layer infers structure from observed behavior under strict
identifiability constraints.

It optimizes for:

- measurement validity
- calibration modeling
- topology hypotheses
- prediction error estimation
- uncertainty tracking
- reproducibility
- falsifiability

### 5.2 Research May

The research layer may:

- compute derived metrics at read time
- classify hypotheses with explicit `unknown` fallback
- compare clean-data profiles
- estimate uncertainty
- propose falsifiable hypotheses
- analyze passive signals
- model exposure effects once the exposure ledger exists

### 5.3 Research Must Not

The research layer must not:

- treat derived metrics as ground truth
- persist latent variables as observed facts
- treat self-report as psychological truth
- merge exposed/intervened behavior with naturalistic data
- mix minute, ratio, and log spaces in one equation
- convert unknowns into neutral defaults
- require product friction for speculative model gain
- convert self-reported readiness by time of day into ability, capacity,
  cognition, focus, mastery, or identity claims

### 5.4 Identity Rule

No inference output may be treated as a stable user identity.

All research outputs are time-local, context-bound hypotheses unless validated
by a later contract.

Readiness-by-time-window outputs are allowed only as planning-context
hypotheses, for example: "In rated sessions, afternoon starts landed closer to
plan." They must not be rendered as "your best brain time", "when you are most
functional", or any equivalent stable trait.

Archetype outputs are especially constrained. They may function as cold-start
priors or similarity hypotheses, but they must not be rendered or consumed as
personality truth. As personal longitudinal traces accumulate, user-specific
evidence must weaken, reinforce, or override archetype priors.

---

## 6. Shared Data Contract

The shared artifact between product and research is the event stream.

Minimum envelope follows `docs/cortex_contract_v0.md`:

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

Payload may contain:

- raw observed fields
- timestamps
- user inputs
- system events

Payload must not contain:

- `execution_multiplier`
- `log_execution_multiplier`
- flow, friction, quality, readiness-state, or cognitive-load labels
- latent constructs
- aggregated predictions

Derived metrics are recomputed from raw events and evaluation version.

The shared event envelope carries provenance. Output surfaces additionally
declare `truth_class` because a rendered claim can be a trace, metric,
interpretation, intervention, or diagnostic readout. `truth_class` is not a
provenance class and must not be inferred from provenance.

---

## 7. Passive Signal Expansion

Passive signal extraction may expand if it does not increase user burden.

Allowed passive/internal expansion:

- timestamps
- state transitions
- pause/resume topology
- latency measurement
- existing-field missingness
- deadline linkage already implied by existing workflows
- read-time derived metrics
- clean-data profile labels
- evaluation-version stamps

### 7.1 Interruption Metrics

Execution measurement must stay clean:

- `Execution Time` is active work time.
- `Session Span` is the observed stopwatch span, including pauses.
- `Pause Overhead` is bounded interruption/recovery gap evidence from clean
  closed sessions, including zero-pause sessions.
- `Occupancy Time` is the product-facing planning footprint:
  `Execution Time + bounded Pause Overhead`.
- `Execution Efficiency` is `Execution Time / Session Span`.
- `Recovery Friction` is the typical pause-to-resume duration from clean
  pause events.

`Task.executed_duration_minutes`, `bias_factor_final`, and calibration outcome
rows remain active execution measurements. Pause overhead may inform planning
windows, insights, micro-mirrors, nudges, and resume continuity prompts, but it
must not be folded into clean execution calibration.

Not allowed without successor contract:

- new required manual fields
- new subjective scales
- new check-ins
- new questionnaires
- new model-training prompts

---

## 8. Observability Repair

Manual lifecycle tracking is high-value instrumentation, but it is not
perfect ground truth when it depends on continuous human attention under
cognitive load.

The product may detect likely missing lifecycle events only as observability
repair. This means inference may notice possible gaps in instrumentation, but
must not silently write inferred state as measured truth.

Allowed repair targets:

- possible forgotten timer start
- possible forgotten pause
- possible forgotten resume
- possible forgotten stop
- possible overdue task state repair

Allowed detection sources:

- existing task lifecycle state
- planned task timing and overdue state
- active stopwatch or pause state
- existing pause/resume prediction signals
- app interaction timestamps already emitted by normal use
- existing operator-only tooling signals for operator sessions only

Repair prompts are allowed only when all of the following hold:

- the prompt is optional and low-friction
- the prompt asks about a specific missing transition, not a new subjective
  variable
- the proposed transition is labeled as inferred until the user confirms it
- denial or dismissal is preserved as signal, not treated as user failure
- the prompt itself is exposure/intervention state for later analysis
- the prompt passes the repair interruption budget below

### 8.1 Repair Interruption Budget

Repair prompts are interventions. They spend user attention and can become
cognitive noise if they fire too eagerly.

Default behavior is silent candidate logging, not immediate questioning. A
suspected missing transition should remain a candidate with explicit
uncertainty until the system has enough confidence, timing urgency, and user
context to justify interruption.

Interruption tiers:

- Low confidence: log the candidate silently as `unknown`; do not prompt.
- Medium confidence: batch the candidate into a later recovery review or
  natural transition moment.
- High confidence: prompt only if waiting risks meaningful data loss,
  operational confusion, or continuity breakage.

Prompt throttling rules:

- Batch nearby repair candidates instead of asking repeatedly.
- Prefer natural transition boundaries over interrupting active work.
- Use cooldowns after dismissal, denial, or repeated ignored prompts.
- Treat prompt frequency as product friction and research contamination.
- Preserve `unknown` if the user does not answer.

Repair prompts must not:

- create a new required user input surface
- ask for a new rating scale
- silently infer duration as observed truth
- backfill measured execution rows as if they were real-time observed timers
- train adaptive metrics unless a successor contract defines the clean-data
  profile and exposure handling
- become a stream of repeated questions that the user learns to ignore

Confirmed repairs may support product continuity, but they are not equivalent
to real-time observed transitions. Cortex-certified analysis must preserve the
repair provenance and exclude repaired durations from `measured_execution` and
`planning_calibration` unless a successor contract explicitly defines a
validated repaired-data profile.

Rationale: the system should not assume humans are reliable instrumentation
devices during deep, fragmented work. The correct upgrade is not more tracking
burden; it is human-in-the-loop repair for missing instrumentation.

---

## 9. Retention As Research Constraint

Retention is not a vanity metric in this system.

It is the condition that makes longitudinal behavioral inference possible.

Constraint hierarchy:

1. user retention: data existence
2. friction minimization: data quality
3. identifiability: scientific validity
4. inference expansion: research depth

If inference depth harms retention or increases required friction, inference
depth loses unless a successor contract explicitly justifies the trade.

---

## 10. Exposure Separation

Any prediction, nudge, insight, or behavioral reflection shown to the user is an
intervention candidate.

Research must not treat post-exposure behavior as naturalistic observation
unless exposure is explicitly modeled.

Minimum inference-time exposure classes:

- `observed_no_exposure`
- `observed_exposed_prediction`
- `observed_intervention`
- `observed_exposure_unknown`

Until Phase 1 exposure ledger exists, exposed and unknown-exposure rows must not
silently update adaptive learning metrics.

### 10.1 Exposure Ledger v0

Exposure Ledger v0 is a causal firewall and replay boundary. It is not an
attribution engine, behavioral profiler, influence optimizer, or proof that an
exposure caused later behavior.

The ledger answers one narrow question:

```text
Can this measurement still be interpreted as baseline under the current
exposure horizon policy?
```

Baseline cleanliness is not the default. A row becomes baseline-clean only when
exposure context was evaluated and returned `NONE` for the relevant signal
target. `UNKNOWN`, `EXPOSED`, and `INTERVENTION` are fail-closed states for
baseline learning unless a successor contract explicitly defines a stratified
analysis profile.

`clean` means:

```text
no detected exposure within the current policy-defined contamination horizon
```

It does not mean true, uncontaminated in all possible ways, or immune to ambient
measurement effects.

Minimum `is_exposed` contract:

```text
is_exposed(user_id, event_time, signal_target, horizon_policy_version)
  -> ExposureContaminationResult
```

The result must include:

- `state`: `NONE | EXPOSED | INTERVENTION | UNKNOWN`
- `exposure_ids`
- `exposure_categories`
- `signal_target`
- `checked_window_start`
- `checked_window_end`
- `horizon_policy_version`
- `unknown_reason`
- `policy_effect_reason`

`NONE` requires proof that the exposure ledger, suppression layer, legacy
exposure adapters, and horizon policy were all checked. Missing ledger state
must return `UNKNOWN`, never `NONE`.

Minimum v0 event atoms:

- `exposure_decision_event`: candidate generation, eligibility, suppression,
  delay, failure, or show decision.
- `exposure_render_event`: exact user-visible stimulus, including rendered
  content snapshot and hash.
- `suppression_event`: eligible exposure withheld from the user and why.

Deferred atoms:

- attention proxies
- temporal associations

The deferred temporal association atom must not be named response linkage or
described as causal evidence.

Existing partial exposure sources are legacy inputs to the gate, not obsolete
tables:

- `ReflectionViewLog`
- `CalibrationNudgeEvent`
- `PausePredictionLog`
- `ResumePredictionLog`

No physical backfill is required for v0. Historical coverage may be adapter-
based and must preserve source uncertainty.

`repair_prompt` means a system prompt asking the user to confirm or deny a
suspected missing lifecycle transition. It is both a user-facing exposure and a
measurement repair attempt, so it must preserve repair provenance and obey the
repair interruption budget.

OpenClaw remains operator-only. OpenClaw agent output, operator orchestration,
and local runtime traces are not Lyra product research data unless a successor
contract explicitly admits operator-session analysis.

### 10.2 Runtime Surface Registry And Precedence

Every product or research output surface that can shape user behavior must be
registered before render. The registry source of truth is
`backend/app/core/output_surface_registry.json`; runtime writes go through
`backend/app/services/output_surfaces.py`.

Required surface fields:

- `surface_id`
- `truth_class`
- `usage_class`
- `channel`
- `exposure_category`
- `signal_targets`
- `clean_profile`
- `min_n`
- `time_window`
- `fallback_mode`
- `operator_only`
- `legacy_adapter`
- `render_policy_version`

Runtime precedence is fail-closed:

1. request identity/scope must resolve cleanly,
2. consumer `usage_class` must be allowed,
3. mixed-row input must resolve to an explicit projection,
4. the surface must be registered with `truth_class`,
5. clean profile, threshold, and time-window checks must pass,
6. `UNKNOWN`, `EXPOSED`, and `INTERVENTION` block clean learning unless a
   profile explicitly permits stratified use,
7. generator/render logic may run only after those checks,
8. frontend requests never override backend suppression.

No-direct-emission rule:

- User-facing or behavior-shaping outputs must emit through
  `backend/app/services/output_surfaces.py`.
- Direct event writes are reserved for the exposure ledger implementation,
  the output-surface emitter, migrations, and explicit tests.
- Dual-write legacy adapters must be treated as temporary compatibility
  bridges with parity tests or diagnostics; divergence is a product-research
  integrity bug, not just telemetry drift.

### 10.3 Mixed-Row Read Resolution

Product UI reads `descriptive_history` by default unless the surface is
research or diagnostic. Analytics reads the projection selected by the
declared clean-data profile. Training and clean baselines read only
profile-approved projections.

Projection classes:

- `raw_observed`
- `correction_adjusted_effective`
- `external_submission_trace`
- `repair_prompt_result`
- `diagnostic_projection`

### 10.4 Horizon Policy Auditability

The horizon policy is a hypothesis about contamination, not contamination
itself. The exposure gate must therefore remain auditable as an instrument.

`exposure_policy_effect_log` is diagnostic meta-instrumentation only. It is not
behavioral telemetry and must not become an inference input. It exists to
answer whether the current policy is making coherent baseline decisions over
time.

Minimum snapshot fields:

- `policy_version`
- `exposure_category`
- `signal_target`
- `state_distribution_counts`
- `unknown_rate`
- `ledger_incomplete_rate`

Required interpretation:

- high `UNKNOWN` means the gate cannot safely certify baseline data
- high `ledger_incomplete_rate` means the ledger chain is structurally weak
- high `EXPOSED` rate may mean true contamination or an over-broad horizon
- high `NONE` rate is not proof of truth; it is only no detected exposure under
  the current policy

---

## 11. Product-Research Flow Direction

Strict flow:

```text
User -> Product Layer -> Event Stream -> Research Layer -> Hypotheses
```

Reverse flow is forbidden unless a hypothesis is promoted into product logic
through a deterministic rule with:

- invariant tests
- clean-data profile
- exposure plan
- user-facing copy review
- rollback path

---

## 12. Forbidden System Behaviors

Cortex Product-Research work must not:

- optimize user behavior directly
- introduce hidden user-burden variables
- create a productivity, quality, worth, or performance score
- present latent states as facts
- present context-switch topology as causal proof of failure, avoidance,
  focus loss, motivation, or cognitive state
- use research needs to justify friction creep
- learn from its own interventions without exposure modeling
- describe self-report as measured cognition
- add UI prompts because a model wants cleaner data
- silently convert inferred missing transitions into observed lifecycle events

---

## 13. Review Checklist

Before any product or research change touching Cortex-adjacent behavior:

- Does this add a required user input?
- Does this increase the time or cognitive load needed to complete a task?
- Is the added signal passive, derived, or user-burdening?
- If user-burdening, what existing burden is being removed?
- Does this expose a claim that future learning will consume?
- If this consumes baseline data, did it call exposure context and fail closed
  on `UNKNOWN`, `EXPOSED`, or `INTERVENTION`?
- Does this preserve unknown propagation?
- Does this preserve clean-data profile declarations?
- If this uses context-switch, interruption, or parked-work topology, does it
  preserve the distinction between correlation and cause?
- Does every user-facing output surface declare `truth_class`, `usage_class`,
  fallback mode, threshold, and exposure targets?
- Does mixed-row consumption use an explicit projection class?
- Does render failure fail closed instead of letting the frontend display an
  unlogged output?
- Does this keep product behavior stable while research evolves?
- Does this treat retention as a research precondition rather than product
  polish?
- If this repairs missing lifecycle state, does it preserve repair provenance
  and exclude repaired durations from default measured-execution learning?
- If this asks a repair question, does it obey confidence thresholds,
  batching, cooldowns, and silent logging below threshold?

If any answer is unclear, mark uncertainty and do not smooth it into certainty.

---

## 14. Final Principle

Cortex does not learn from users by making them change.

Cortex learns about users while keeping the product surface stable, low-friction,
and honest about uncertainty.
