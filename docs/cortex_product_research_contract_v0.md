# Cortex Product-Research Contract v0

**Status:** Active boundary contract.

**Purpose:** Define how LyraOS can operate as a low-friction product while
remaining a research-grade behavioral measurement system.

This contract does not authorize new inference, schema, predictors, or UI. It
defines the boundary between product behavior and research interpretation.

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

### 5.4 Identity Rule

No inference output may be treated as a stable user identity.

All research outputs are time-local, context-bound hypotheses unless validated
by a later contract.

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

Not allowed without successor contract:

- new required manual fields
- new subjective scales
- new check-ins
- new questionnaires
- new model-training prompts

---

## 8. Retention As Research Constraint

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

## 9. Exposure Separation

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

---

## 10. Product-Research Flow Direction

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

## 11. Forbidden System Behaviors

Cortex Product-Research work must not:

- optimize user behavior directly
- introduce hidden user-burden variables
- create a productivity, quality, worth, or performance score
- present latent states as facts
- use research needs to justify friction creep
- learn from its own interventions without exposure modeling
- describe self-report as measured cognition
- add UI prompts because a model wants cleaner data

---

## 12. Review Checklist

Before any product or research change touching Cortex-adjacent behavior:

- Does this add a required user input?
- Does this increase the time or cognitive load needed to complete a task?
- Is the added signal passive, derived, or user-burdening?
- If user-burdening, what existing burden is being removed?
- Does this expose a claim that future learning will consume?
- Does this preserve unknown propagation?
- Does this preserve clean-data profile declarations?
- Does this keep product behavior stable while research evolves?
- Does this treat retention as a research precondition rather than product
  polish?

If any answer is unclear, mark uncertainty and do not smooth it into certainty.

---

## 13. Final Principle

Cortex does not learn from users by making them change.

Cortex learns about users while keeping the product surface stable, low-friction,
and honest about uncertainty.
