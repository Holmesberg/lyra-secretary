---
type: architecture
status: active
confidence: high
created: 2026-05-12
updated: 2026-05-12
last_reviewed: 2026-05-12
source_refs:
  - docs/layered_epistemic_architecture.md
  - backend/app/db/models.py
  - backend/app/services/bias_factor_service.py
  - backend/app/services/exposure_ledger.py
  - backend/app/services/archetype_service.py
related:
  - "[[LyraOS System Map]]"
  - "[[Epistemic Core]]"
  - "[[Measurement Validity]]"
  - "[[Measurement Validity Map]]"
  - "[[Data Flow Map]]"
  - "[[Research Layer Map]]"
  - "[[Product Layer Map]]"
  - "[[Cortex]]"
  - "[[Exposure Ledger]]"
  - "[[Clean Data Profile]]"
  - "[[Baseline Cleanliness]]"
  - "[[Observed vs Derived vs Inferred]]"
  - "[[Exposure Contamination]]"
  - "[[Fail-Closed Unknown]]"
  - "[[Self Model]]"
data_class: internal_architecture
---

# Layered Epistemic Architecture

This is the routing center for how LyraOS turns product behavior into research-grade inference without collapsing different truth classes into one story.

[[Measurement Validity]] remains the abstract principle. This note is the operational center of gravity: it tells each signal where it lives, what may consume it, and what must never be inferred from it.

## Canonical Route

```text
Layer A observed behavior
-> Layer B behavioral metrics
-> Layer C interpretive models
-> Output Surface + Contamination Boundary
-> Exposure Ledger
-> future clean-data filtering
```

Self-report and correction route:

```text
Layer D self-report / narrative correction
-> weak prior, annotation, or comparison signal
-> Layer C only with provenance and uncertainty
```

## Runtime Precedence

The runtime path fails closed in this order:

1. identity/scope resolves cleanly,
2. consumer `usage_class` is allowed,
3. mixed-row input resolves to an explicit projection,
4. output surface is registered with `truth_class`,
5. clean profile, threshold, and window pass,
6. exposure state permits learning or rendering,
7. generator/render logic runs,
8. frontend request may display only what backend permits.

`truth_class` values are `trace`, `metric`, `interpretation`,
`intervention`, and `diagnostic_only`.

## Epistemic Operating Discipline

The architecture must defend itself when the operator is tired, distracted,
scaling, or absent. Core safeguards are kernel rules:

- identity and scope resolve before product behavior is read or written,
- output surfaces are registered before render,
- every surface declares `truth_class`,
- output goes through the authorized emission path,
- frontend requests never override backend suppression,
- unregistered, unknown, or under-specified surfaces fail closed.

## Complexity Admission Rule

Kernel complexity may grow only when all three conditions are true:

1. a recurring integrity failure exists,
2. operational discipline already proved insufficient,
3. the mechanism reduces ambiguity more than it increases cognitive load.

Escalation should prefer:

```text
manual
-> runbook
-> script
-> test
-> CI
-> runtime enforcement
```

Hard kernel, soft periphery. Identity, topology, truth class, projection,
exposure, and authorized emission belong in the kernel. Trace readbacks,
factual reminders, temporary adapters, and low-risk product ergonomics stay
lighter unless their epistemic risk justifies more ceremony.

Strictness scales with epistemic risk. Trace outputs can carry a light
contract. Metric outputs need declared inputs and sign conventions.
Interpretations and interventions need thresholds, provenance, exposure, and
fallback behavior. Identity-level claims are nearly locked down.

Ontology and governance are tools for protecting real product traces,
retention, behavior quality, and longitudinal signal accumulation. They are not
substitutes for evidence.

## Layer Roles

| Layer | Role | Example source | Forbidden collapse |
| --- | --- | --- | --- |
| Layer A | Observed behavior | `Task`, `StopwatchSession`, `PauseEvent` timestamp, `DeadlineCompletionEvent` | Do not rewrite observed traces to match later narrative. |
| Layer B | Behavioral metrics | initiation delay, active duration, execution multiplier, deadline delay | Do not treat metrics as explanations. |
| Layer C | Interpretive models | `bias_factor_final`, Behavioral Proximity, future pattern mirrors | Do not persist interpretations as identity truth. |
| Layer D | Self-reported priors and narrative corrections | survey answers, readiness/reflection, `TaskExecutionCorrection` | Do not treat self-report as observed behavior. |

## Center-Of-Gravity Function

This note connects:

- [[Cortex]]: computes and filters metrics without mutating raw truth.
- [[Exposure Ledger]]: prevents user-visible outputs from becoming invisible baseline contamination.
- [[Clean Data Profile]]: defines which rows are valid for which inference purpose.
- [[Observed vs Derived vs Inferred]]: keeps trace, metric, and hypothesis separate.
- [[Fail-Closed Unknown]]: blocks missing context from becoming neutral.
- [[Self Model]]: watches when LyraOS begins changing what it thinks it is.
- [[Feedback Surfaces]]: routes mirrors, reminders, and nudges through contamination boundaries.
- [[Measurement Validity Map]]: preserves the broader validity stack.

## Current Data Stress Test - 2026-05-12

Live DB audit against the architecture:

- Total users: `10`.
- Non-operator users: `9`.
- Non-operator users with onboarding completed and at least one task: `7`.
- Non-operator users with any measured executed session: `3`.
- Non-operator users with a measured executed session in the last 14 days: `2`.
- Non-operator average measured sessions: `2.0`.
- Non-operator average measured sessions in the last 14 days: `0.56`.
- Non-operator users with `>=3` measured sessions: `2`.
- Non-operator users with `>=10` measured sessions: `1`.
- Non-operator users with `>=8` readiness/reflection pairs: `1`.
- Deadline completion events: `0`.
- Task execution corrections: `0`.
- Legacy `ReflectionViewLog` rows: `110`.
- v0 `ExposureDecisionEvent` rows: `0`.
- v0 `ExposureRenderEvent` rows: `0`.

Interpretation:

- Current data supports plain task reminders, scheduled-task facts, trace readbacks, and exact one-session/two-session comparisons.
- Current data does not yet support broad cohort-level behavioral inference.
- Deadline completion behavior cannot be inferred yet because there are no `DeadlineCompletionEvent` rows.
- Forgotten-timer correction behavior cannot be inferred yet because there are no `TaskExecutionCorrection` rows.
- Pattern mirrors are mostly operator-supported right now; alpha-user evidence remains sparse.
- Exposure Ledger v0 exists as a target boundary, but current output coverage is still mostly legacy `ReflectionViewLog`.

## Auditor Result

Docs/research-side review:

- Coherent architecture.
- Needs narrow authority language so it does not accidentally authorize new user-facing claims.
- Must preserve `self_reported` vs observed provenance.
- Must define thresholds, falsifiers, and clean-data profiles before Layer C outputs.

Code/feasibility-side review:

- Feasible with current code anchors.
- Current data is too sparse for broad behavioral inference.
- `/v1/analytics/insights` remains a legacy surface until it declares layers, thresholds, clean-data profile, and exposure behavior.
- Exposure Ledger v0 models and services exist, but current alpha rows show the v0 render/decision path is not yet populated.

## Forbidden Collapses

- Survey Profile Prior -> observed behavior.
- Correction sidecar -> raw stopwatch truth.
- Metric -> psychological explanation.
- Behavioral Proximity -> identity label.
- Output engagement -> proof that the output was correct.
- Missing exposure state -> baseline clean.

## Design Consequence

LyraOS should become intelligent by preserving contradictions long enough to learn from them.

Contradiction between self-report, observed traces, derived metrics, and interpretive models is not failure. It is often the signal.

The architecture must stay fed by real traces. Registry completeness,
ontology, and governance are only valuable when they protect actual product
use, retention, and longitudinal signal accumulation.

## Related Tensions

- [[Tension - Helpfulness vs Contamination]]
- [[Tension - Automation vs Provenance]]
- [[Tension - Product vs Research Velocity]]
- [[Tension - Frictionless UX vs Measurable Behavior]]
- [[Tension - Policy Simplicity vs Contamination Fidelity]]

## Related Decisions

- [[Decision - Exposure Ledger Fails Closed]]
- [[Decision - Cortex Is Read-Only]]
- [[Decision - Repair Prompts Are Interventions]]
- [[Decision - Vault Stores Understanding Not Truth]]

## Related Emergent Patterns

- [[Feedback Surfaces Are Also Contamination Surfaces]]
- [[Exposure Ledger as Causal Firewall]]
- [[Policy Becomes Invisible Truth]]
- [[Unknown Must Remain Structurally Expensive]]
