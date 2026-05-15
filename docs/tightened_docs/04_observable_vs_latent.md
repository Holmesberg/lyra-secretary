# 04 Observable Vs Latent

**Purpose:** Identify where the repo risks treating hypotheses as facts.

## Classification Rules

| Class | Definition | Examples |
| --- | --- | --- |
| observed | emitted by instrumentation | timestamps, task state, pause rows |
| self_reported | user-entered subjective report | readiness, reflection, completion percentage, pause reason |
| derived | computed from observables | deltas, ratios, aggregates, confidence tiers |
| inferred | heuristic/statistical interpretation | valence classes, deadline matches, bias factor lookup |
| latent | hidden construct not directly measured | flow, friction, cognitive load, calibration, self-model error |
| speculative | theory with no stable implementation | TruthGap, execution quality score |

## High-Risk Collapses

### Readiness input -> actual readiness

`pre_task_readiness` is an ordinal self-report. It is not a direct measurement
of capacity. Frontend copy and docs sometimes use "readiness" as shorthand.

**Risk:** future inference treats a 1-5 slider as a psychometric measurement.

**Mitigation:** use `self_assessed_readiness` in Cortex-facing docs and APIs.

### Reflection input -> focus or quality

`post_task_reflection` is user-reported after execution. UI labels include
"focus" in places. This is not direct focus measurement.

**Risk:** high reflection during overrun can be mislabeled as "flow" without
independent evidence.

**Mitigation:** treat as `self_reported_reflection`; never as quality truth.

### Valence class -> observed task property

`inference_engine.classify_task_valence()` returns `flow`, `friction`,
`scope_creep`, `under_plan`, `neutral`. These are deterministic outputs, but
the constructs are latent.

**Risk:** JARVIS or UI says "this was flow" as fact.

**Mitigation:** persist no valence label as truth; if displayed, phrase as
"this pattern looked like..." with clean-data profile and confidence.

### Bullet growth -> scope expansion

`scope_bullet_count_at_plan` and `scope_bullet_count_at_execute` are observed
counts. Scope growth is inferred. More bullets can mean decomposition, not more
work.

**Risk:** scope topology becomes a false mediator.

**Mitigation:** Cortex contract already marks topology as hypothesis.

### Bias factor -> personal law

`bias_factor_final` is a blend of population/archetype prior and personal
sum-ratio. Low-n values are not stable self-knowledge.

**Risk:** user internalizes a low-n multiplier as identity.

**Mitigation:** calibration contract confidence tiers; Cortex open debt on low-n
shrinkage.

### Archetype posterior -> identity

`archetype_proximity_service.py` computes posterior-like scores from task
history using priors and `prior_sigma`.

**Risk:** labels like Procrastinator/Sprinter can become identity claims.

**Mitigation:** frontend has display caps and pre-reveal gates, but the naming
remains semantically loaded.

## Places To Audit Before User-Facing Expansion

- `frontend/components/archetype-proximity-display.tsx`
- `frontend/components/archetype-profile-section.tsx`
- `frontend/components/tutorial-overlay.tsx`
- `frontend/app/(app)/insights/page.tsx`
- `backend/app/api/v1/endpoints/analytics.py`
- `backend/app/services/jarvis_tools.py`
- `backend/app/services/inference_engine.py`

## Positive Patterns Already Present

- `PauseEvent.self_reported_retroactively` separates retroactive confirmation.
- `ReflectionViewLog.event_class` separates impression vs telemetry.
- `llm_parser.py` stores LLM suggestions separately from canonical deadline
  binding.
- Cortex v0 forbids latent persistence.

## Required Review Question

For every behavioral claim, ask:

> Is this a value the system observed, a value the user reported, a value the
> system derived, or a latent interpretation?

If the answer is mixed, the claim is not ready.
