# LyraOS Layered Epistemic Architecture

**Status:** Canonical architecture note.
**Created:** 2026-05-12.
**Purpose:** Define how LyraOS data layers feed each other without collapsing
different kinds of truth into one system. This document is implementation
guidance for future product, research, analytics, inference, and documentation
changes.

LyraOS is not one undifferentiated "AI productivity" layer. It is a layered
behavioral calibration system. Each layer has its own truth status, provenance,
allowed consumers, and failure modes.

The goal is not to prevent inference. The goal is to make inference traceable.
Every new feature should answer:

1. What layer does this belong to?
2. What code or table is the source of truth?
3. What layers may consume it?
4. What interpretations are forbidden?
5. What user exposure does it create?

If a change cannot answer these questions, it is not ready to become canonical.

## Authority And Scope

This document is the canonical epistemic architecture note. It clarifies how
LyraOS should classify, route, and interpret data.

It does not authorize new schema, UI, predictors, adaptive inference,
personalized outputs, or user-facing claims by itself. Those still require the
appropriate product-research contract, implementation plan, tests, and exposure
review.

When this document conflicts with a narrower contract, the narrower contract
wins until an explicit decision updates both documents.

Current implementation caveat:

- Exposure Ledger v0 exists in code, but coverage is partial.
- Legacy `ReflectionViewLog` remains an exposure bridge for existing mirrors and
  nudges.
- A surface is not baseline-safe merely because this document says it should
  route through the Exposure Ledger. It is baseline-safe only when the actual
  code path records exposure and downstream learning calls exposure checks.

## Epistemic Operating Discipline

The architecture must defend itself when the operator is tired, distracted,
scaling, or absent. Core safeguards are not advisory style preferences; they
are kernel rules for preserving measurement validity under pressure.

Hard kernel rules:

- request identity and scope must resolve before product behavior is read or
  written,
- output surfaces must be registered before they render,
- every output surface must declare a `truth_class`,
- user-facing output must go through the authorized emission path,
- frontend requests must never override backend suppression,
- unregistered, unknown, or under-specified surfaces fail closed.

Kernel complexity admission rule:

Kernel complexity may grow only when all three conditions are true:

1. a recurring integrity failure exists,
2. operational discipline has already proved insufficient,
3. the new mechanism reduces ambiguity more than it increases cognitive load.

Preferred escalation ladder:

```text
manual note
  -> runbook
  -> script
  -> test
  -> CI gate
  -> runtime enforcement
```

The kernel should defend identity, topology, truth class, projection, exposure,
and authorized emission. The periphery should stay soft: trace readbacks,
factual reminders, temporary adapters, and low-risk product ergonomics should
not inherit heavy ceremony unless their epistemic risk justifies it.

The periphery should stay pragmatic. Strictness scales with epistemic risk:

- trace outputs may use a light contract,
- metric outputs need declared inputs and sign conventions,
- interpretations and interventions need thresholds, provenance, exposure, and
  fallback behavior,
- identity-level or self-model claims are nearly locked down.

The architecture is valuable only while it stays fed by real product traces,
retention outcomes, behavior quality, and longitudinal signal accumulation.
Ontology and governance are tools for protecting the instrument, not substitutes
for evidence.

## Truth-Layer Vocabulary Compatibility

Older LyraOS prompts and notes use this vocabulary:

| Older vocabulary | This document | Meaning |
| --- | --- | --- |
| Layer A - Observed Trace | Layer A - Observed Behavior | Immutable instrumentation and operational traces. |
| Layer B - Inference Trace | Layer B - Behavioral Metrics | Derived arithmetic/statistical structure over declared inputs. |
| Layer C - Interpretation Layer | Layer C - Interpretive Models | Probabilistic or heuristic meaning hypotheses. |
| Layer D - User Narrative | Layer D - Self-Reported Priors + Narrative Corrections | Subjective reports, priors, corrections, and retroactive narrative. |

The main refinement is that this document separates derived metrics from
interpretive models. A duration delta is not an inference about the user; it is
a metric. A behavioral explanation built from that delta is an interpretation.

---

## 1. Code Sources Of Truth

This document is grounded in current code, not only desired architecture.

Primary code anchors:

- `backend/app/db/models.py`: database models and schema-level comments.
- `backend/app/services/bias_factor_service.py`: current personal/prior
  duration calibration blend.
- `backend/app/services/exposure_ledger.py`: exposure contamination checks and
  baseline-clean gating.
- `backend/app/services/output_surfaces.py`: registered output-surface
  emission and legacy exposure adapter writes.
- `backend/app/services/archetype_service.py`: survey scoring and survey-derived
  profile assignment.

Supporting implementation anchors:

- `backend/app/services/stopwatch_manager.py`: stopwatch lifecycle, pause-aware
  execution duration, stop-time mirrors.
- `backend/app/services/task_manager.py`: task lifecycle, first-task stamps,
  deadline binding, retroactive creation, correction writes.
- `backend/app/api/v1/endpoints/users.py`: survey submission, survey skip,
  user profile state.
- `backend/app/api/v1/endpoints/analytics.py`: current analytics and user-facing
  insight endpoints.
- `backend/app/workers/jobs/reminders.py`: scheduled task reminders.
- `backend/app/core/exposure_horizon_policies.json`: contamination horizons.
- `backend/app/core/output_surface_registry.json`: runtime surface registry,
  including `truth_class`, `usage_class`, clean profile, thresholds, fallback,
  and legacy-adapter declarations.

When code and this document disagree, the next change must either update the
code or update this document with an explicit decision note.

Known implementation caveats:

- `/v1/analytics/insights` is a legacy output surface until it declares layer
  inputs, clean-data profile, thresholds, copy level, and exposure behavior.
- `/v1/analytics/bias_factor/lookup` is the production calibration lookup path
  and uses the blended service with exposure-aware gating.
- `/v1/analytics/bias_factor` is diagnostic/raw unless a successor contract
  explicitly makes it a user-facing calibration claim.
- Archetype/proximity endpoints may compute Layer C values, but user-facing
  display requires thresholds, uncertainty, and exposure handling.

---

## 2. Layer A: Observed Behavior

Layer A is the immutable trace substrate: what the system directly observed or
recorded as an event in operation.

Layer A answers: **What happened according to instrumentation?**

Current Layer A sources:

- `Task`: planned task records, lifecycle state, planned timestamps, planned
  duration, category, source, deadline binding, creation time.
- `StopwatchSession`: real-time execution session boundaries and pause-adjusted
  stopwatch context.
- `PauseEvent`: real-time pause and resume row/timestamps. Pause reason and
  initiator are Layer D self-reported annotations attached to the row, not
  independently observed cognitive state.
- `Deadline`: deadline object state, due timestamp, imported source, completed
  and missed timestamps.
- `DeadlineCompletionEvent`: append-only deadline-resolution event such as
  manual done, Moodle submission, backfill, or retroactive task completion.
- `ExternalEventOutcome`: explicit user attendance marking for imported
  external calendar events.
- `JarvisInvocation`: audit record of agent tool calls, especially queued and
  confirmed writes.

Layer A rules:

- Do not overwrite raw observed timestamps to satisfy later narrative edits.
- Do not let inferred state mutate Layer A.
- Do not let user narrative corrections pretend to be original observation.
- Do not treat externally imported timestamps as native execution behavior.
- Do not interpret a lifecycle state as psychological meaning.

Examples:

- A task planned for 18:00 with `planned_duration_minutes=45` is Layer A.
- A stopwatch start and stop producing 67 active minutes is Layer A.
- A Moodle submission timestamp is Layer A as an external submission trace, not
  as proof of human execution time.
- A pause row with `self_reported_retroactively=false` is eligible for real-time
  pause-process analysis. A retroactive pause confirmation is not the same
  truth class.

Layer A is the anchor layer. Every higher layer must be explainable back to it
or explicitly marked as self-report, interpretation, or output exposure.

---

## 3. Layer B: Behavioral Metrics

Layer B is derived arithmetic or statistical structure over Layer A and
declared Layer D annotations.

Layer B answers: **What measurable structure can be computed from the traces?**

Current Layer B examples:

- `initiation_delay_minutes`: difference between planned start and actual start.
- `executed_duration_minutes`: active execution duration.
- `duration_delta_minutes`: legacy sign convention, `planned - executed`.
- `execution_multiplier`: canonical Cortex ratio, `executed / planned`.
- `active_delta_minutes`: canonical Cortex minute delta, `executed - planned`.
- `pause_count`: number of pauses attached to a task/session.
- pause duration and recovery latency.
- `delay_minutes` on deadline outcomes and completion events.
- `discrepancy_score`: absolute difference between readiness and reflection.
- `signed_discrepancy`: post-task reflection minus pre-task readiness.
- aggregate counts such as completed tasks, skipped tasks, friction events,
  first-task/funnel timestamps, and completion behavior counts.

Layer B rules:

- Always declare the input profile. Examples: raw observed values,
  effective corrected values, measured execution, planning calibration, pause
  process, deadline completion behavior.
- Metrics are not explanations. A delay is not procrastination. A high pause
  count is not distraction. An overrun is not incompetence.
- Keep sign conventions explicit. Legacy `duration_delta_minutes` is
  `planned - executed`; Cortex minute deltas use `executed - planned`.
- Preserve unknowns. Do not convert missing values into neutral defaults.
- Do not mix retroactive, external, observed, and corrected values without
  declaring provenance.

Layer B may feed Layer C only when it carries:

- clean-data profile,
- provenance,
- sample count or uncertainty,
- exposure contamination state where relevant.

---

## 4. Layer C: Interpretive Models

Layer C contains probabilistic, heuristic, or model-based interpretations of
Layer B.

Layer C answers: **What might the measurable structure imply?**

Layer C is never canonical truth. It is a hypothesis layer.

Current Layer C examples:

- `bias_factor_final` from `bias_factor_service.blend()`.
- personal duration calibration cells.
- research-prior and survey-profile-prior blending.
- behavioral archetype proximity from trace evidence.
- pause prediction and resume prediction systems.
- deadline-shape analytics.
- future pattern mirrors.
- insight generators in `analytics.py`.

Layer C rules:

- Use clean-data helpers for learning paths. Current code uses
  `baseline_clean_task()` in `bias_factor_service.blend()`.
- Treat survey-derived profile data as a weak prior, not as evidence that the
  user behaves that way.
- Treat outputs as interventions once shown to users.
- Include confidence, sample count, provenance, and time window when surfacing
  interpretations.
- Do not create identity labels from low-N evidence.
- Do not persist latent labels as if observed.

Layer C implementation contract:

Any model, mirror, proximity score, insight, or personalized output must
declare before shipping:

- minimum eligible sample count,
- time window,
- clean-data profile,
- provenance inclusions and exclusions,
- exposure category and signal targets,
- confidence or uncertainty calculation,
- falsifier or revisit condition,
- fallback behavior when evidence is insufficient,
- copy level: trace readback, low-confidence pattern, or interpretation.

Default safety thresholds until a narrower contract replaces them:

- `0` executed sessions: no behavioral claim.
- `1-2` eligible sessions: trace readback only.
- `3-5` eligible sessions: low-confidence descriptive comparison only.
- `10+` eligible sessions in the relevant slice: candidate repeated-pattern
  mirror.
- `30+` eligible sessions in the relevant slice: candidate stable calibration
  or model evaluation, still not identity truth.

These defaults are guardrails, not promises. A high-risk surface can require a
higher threshold, and sparse or contaminated data can still suppress output.

Forbidden Layer C collapses:

- "The user reported procrastination" -> "the user procrastinates."
- "A task overran" -> "the task was friction."
- "High reflection" -> "the task produced focus."
- "Behavioral proximity is high" -> "the user is this archetype."
- "The model predicted a pause" -> "the pause was caused by the predicted
  mechanism."

Good Layer C language:

- "This pattern resembles..."
- "In this window..."
- "Based on N eligible sessions..."
- "This is an interpretation, not a fact."
- "The data is not strong enough yet."

Bad Layer C language:

- "You are..."
- "Your type is..."
- "You always..."
- "This proves..."
- "Lyra knows..."

---

## 5. Layer D: Self-Reported Priors + Narrative Corrections

Layer D contains user-provided subjective information and retroactive narrative
edits.

Layer D answers: **What does the user say, believe, remember, or correct?**

Current Layer D sources:

- onboarding survey answers.
- `ArchetypeAssignment.raw_responses`.
- survey skip/default assignment.
- `pre_task_readiness`.
- `post_task_reflection`.
- `task_completion_percentage`.
- pause reason and pause initiator, because they are user-classified event
  descriptions even when attached to a real-time event.
- retroactive task creation.
- retroactive pause confirmation.
- `TaskExecutionCorrection`.
- self-reported deadline done when the timestamp is the click time or a
  retroactive report.

Layer D rules:

- Layer D may annotate Layer A, but must not rewrite it.
- Layer D may feed Layer C only as a weak prior, correction, or comparison
  signal.
- Layer D must never be treated as observed behavior.
- Layer D must preserve provenance: self-reported, retroactive, corrected,
  skipped, or unknown.
- Layer D is allowed to contradict Layer A. Those contradictions are valuable
  signals, but they are not license to collapse the layers.

Example:

The user forgets to stop a timer and later corrects the end time.

- Original stopwatch start/stop is Layer A.
- `TaskExecutionCorrection` is Layer D.
- A read-time effective duration may be Layer B if explicitly labeled as
  correction-adjusted.
- A future inference that uses corrected duration must declare whether it used
  raw observed duration or Layer-D-adjusted effective duration.

This distinction matters. Human memory is useful, but it is not instrumentation.

---

## 6. Survey Profile Prior Vs Behavioral Proximity

Existing code uses the term `archetype`. This document splits the concept into
two epistemic meanings.

### Survey Profile Prior

Survey Profile Prior is self-report-derived.

Code anchors:

- `backend/app/services/archetype_service.py`
- `backend/app/api/v1/endpoints/users.py`
- `ArchetypeAssignment`
- `User.archetype_id`

Role:

- cold-start initialization,
- weak personalization prior,
- early duration calibration blend,
- research hypothesis about whether self-report improves early calibration.

Limits:

- not observed behavior,
- not an identity truth,
- not proof of future behavior,
- not valid user-facing behavioral evidence by itself.

### Behavioral Proximity

Behavioral Proximity is trace-derived dynamic similarity.

Code anchors:

- archetype proximity analytics endpoints,
- observed task and execution traces,
- exposure-gated baseline evidence.

Role:

- compare recent trace patterns to existing profile shapes,
- detect divergence between self-report prior and behavior,
- support future interpretation when enough clean data exists.

Limits:

- not identity,
- not destiny,
- not stable at low sample counts,
- not a replacement for Layer A evidence.

### Naming Rule

Existing code and API names may keep `archetype` for compatibility.

New docs, future UI copy, and research notes should prefer:

- "Survey Profile Prior" for self-report-derived cold-start state.
- "Behavioral Proximity" for trace-derived similarity.

Marketing may use "archetype" carefully, but research and internal
architecture must not let the word imply essential identity.

---

## 7. Correction Sidecar Contract

`TaskExecutionCorrection` is a Layer D correction sidecar.

It does not live in Layer A.

It exists because users forget to stop timers, misremember stops, or repair
execution records after the fact. That makes it valuable for product usability
and descriptive history, but not equal to raw observation.

Rules:

- Raw task and stopwatch timestamps remain the original observed trace.
- Correction rows are append-only narrative repairs.
- Corrected/effective values are read-time projections.
- Analytics consumers must declare which value class they consume:
  - raw observed,
  - correction-adjusted effective,
  - excluded due to correction,
  - diagnostic-only.
- Clean research baselines should exclude correction-adjusted rows unless the
  profile explicitly allows them.
- VT-17 and pause/resume training must not treat correction-generated timing as
  observed pause/resume behavior.

Allowed consumers:

- user-facing history that wants to show the repaired duration,
- operator diagnostics,
- correction-rate analytics,
- product-quality metrics around forgotten timers.

Forbidden consumers unless explicitly justified:

- clean measured execution baselines,
- pause/resume predictor training,
- claims about natural behavior timing,
- low-N behavioral mirrors.

---

## 8. Cold Start Contract

Cold start is the state where the user has little or no Layer A behavioral
evidence.

In current alpha data, many users die before their first executed session. That
makes cold start the highest-risk area for both retention and epistemic drift.

At zero executed sessions:

- Layer A contains planning traces if the user created tasks.
- Layer A contains no observed execution behavior yet.
- Layer D may contain survey answers and subjective self-report.
- Layer C must not make behavioral claims.

Allowed at zero sessions:

- create tasks from brain dump,
- show scheduled task facts,
- send plain task reminders,
- use Survey Profile Prior for initialization or internal cold-start scheduling,
- say "Your planned task is waiting",
- say "Reminder: Physics Assignment - planned for today at 6:00 PM."

Forbidden at zero sessions:

- "You tend to..."
- "You usually..."
- "Your pattern is..."
- identity labels,
- confidence mirrors,
- behavioral archetype claims,
- model claims based only on survey answers,
- pressure-performance claims based only on self-report.

At one to three executed sessions:

- trace mirrors may describe the current session or compare exact prior
  sessions.
- pattern mirrors must remain absent unless they meet a declared threshold.
- copy should use witnessed arithmetic, not identity or explanation.

Allowed early trace mirror:

> Planned 45 min, worked 67 active min, paused once.

Forbidden early pattern mirror:

> You are an overrunner under pressure.

Cold-start principle:

The system may help the user reach the first trace, but it must not pretend it
has observed behavior before behavior exists.

---

## 9. Output Surface + Contamination Boundary

This is not a data layer. It is a cross-cutting boundary between internal data
and user perception.

It covers:

- task reminder emails,
- in-app reminders,
- micro-mirrors,
- calibration nudges,
- pause/resume prediction banners,
- deadline insights,
- archetype/proximity displays,
- dashboard cards,
- JARVIS interpretations,
- any future personalized output.

Once shown to a user, an output may change the behavior it measures. Therefore
outputs must be treated as interventions unless explicitly proven otherwise.

Boundary rules:

- Every interpretive output must have exposure logging or a documented reason
  why it is exempt.
- Outputs feed the Exposure Ledger, not Layer A.
- Future learning and inference paths must call target-specific exposure checks
  before treating downstream behavior as baseline-clean.
- Exposure states `UNKNOWN`, `EXPOSED`, and `INTERVENTION` fail closed for
  baseline learning unless a successor clean-data profile explicitly permits
  stratified use.
- Plain factual reminders still affect behavior, but they do not carry
  behavioral inference.
- User engagement with outputs is not proof that the output was true.
- A frontend request never overrides backend suppression.
- A registered surface is not render-safe unless its runtime checks pass.

Runtime fail-closed precedence:

1. request identity and scope must resolve cleanly,
2. consumer usage class must be allowed,
3. mixed-row input must resolve to an explicit read projection,
4. the surface must be registered with a declared `truth_class`,
5. clean-data profile, threshold, and time-window checks must pass,
6. exposure state gates baseline learning: `UNKNOWN`, `EXPOSED`, and
   `INTERVENTION` block clean learning unless a profile explicitly permits
   stratified use,
7. only then may generator or render logic run,
8. frontend requests never override backend suppression.

Output surface `truth_class` values:

- `trace`: exact readback of observed or declared facts,
- `metric`: derived arithmetic or statistical structure,
- `interpretation`: probabilistic or heuristic hypothesis,
- `intervention`: output intended to change user planning, recovery, or action,
- `diagnostic_only`: operator/internal readout not safe for user-facing product
  claims.

Registered output surfaces must declare:

- `surface_id`,
- `truth_class`,
- `usage_class`,
- `channel`,
- `exposure_category`,
- `signal_targets`,
- `clean_profile`,
- `min_n`,
- `time_window`,
- `fallback_mode`,
- `operator_only`,
- `legacy_adapter`,
- `render_policy_version`.

Registry ownership rule:

- New user-facing or behavior-shaping output surfaces must be added to
  `backend/app/core/output_surface_registry.json` before they render.
- Runtime emission must go through `backend/app/services/output_surfaces.py`.
- Direct writes to `ExposureDecisionEvent`, `ExposureRenderEvent`,
  `SuppressionEvent`, or legacy `ReflectionViewLog` are allowed only inside the
  exposure ledger implementation, the output-surface emitter, migrations, or
  explicit tests.
- Legacy adapters are temporary compatibility bridges. Any surface with
  `legacy_adapter` must have parity tests or diagnostics until the adapter is
  removed.
- Missing registry entries, missing projections, missing exposure writes, or
  failed render logging suppress the output in non-diagnostic paths.

Current implementation note:

- Existing `ReflectionViewLog` rows are a legacy exposure signal for mirrors and
  nudges.
- `ExposureDecisionEvent` and `ExposureRenderEvent` are the v0 target shape, but
  current alpha data may have zero rows in those tables.
- Until full dual-write coverage exists, consumers must treat missing exposure
  state as `UNKNOWN`, not `NONE`.

Current code anchors:

- `ReflectionViewLog`: legacy impression/view/dismiss history for mirrors and
  nudges.
- `ExposureDecisionEvent`: exposure eligibility and decision atom.
- `ExposureRenderEvent`: rendered output snapshot.
- `SuppressionEvent`: eligible output withheld from the user.
- `ExposurePolicyEffectLog`: diagnostic snapshot of policy effects.
- `exposure_horizon_policies.json`: contamination target and horizon policy.

Output examples:

- Email reminder: continuity surface. It may say scheduled task facts only.
- Micro-mirror: descriptive trace readback. It must not become an identity
  claim.
- Calibration nudge: planning intervention. It must be logged and excluded from
  clean planning baselines where policy says so.
- Archetype proximity: meta-inference. It has high identity risk and must be
  framed with dynamic, low-claim language.

---

## 10. Allowed Feed Directions

Allowed normal flow:

```text
Layer A observed traces
  -> Layer B behavioral metrics
  -> Layer C interpretive models
  -> Output Surface + Contamination Boundary
  -> Exposure Ledger
  -> future clean-data filtering
```

Allowed self-report flow:

```text
Layer D self-report / corrections
  -> weak prior, annotation, or comparison signal
  -> Layer C only with provenance and uncertainty
```

Allowed contradiction flow:

```text
Layer D says "I work well under pressure"
Layer A/B show late completions, high pause frequency, poor reflection
Layer C may infer contradiction as a hypothesis
Output may surface it only when threshold, confidence, and exposure rules pass
```

Forbidden flow:

```text
Layer D self-report
  -> Layer A observed truth
```

Forbidden flow:

```text
Layer C interpretation
  -> Layer A mutation
```

Forbidden flow:

```text
Output engagement
  -> proof that the output was correct
```

Forbidden flow:

```text
Survey Profile Prior
  -> user-facing behavioral claim before execution evidence
```

---

## 11. Contradiction Handling

Contradictions between layers are expected and informative.

Disagreement between survey priors, observed traces, derived metrics, and
interpretive models should be treated as signal, not architectural failure.
LyraOS becomes useful when it can preserve disagreement long enough to learn
from it.

Examples:

- Survey Profile Prior says the user works well under pressure, but deadline
  traces show late completion plus poor post-task reflection.
- Readiness is low before a task, but the execution trace is clean and the
  reflection is high afterward.
- Behavioral Proximity diverges from the survey-derived profile after enough
  clean observed sessions.
- A correction sidecar repairs user-facing history while raw observation still
  shows a forgotten timer failure mode.

Contradiction rules:

- Do not "resolve" disagreement by overwriting the weaker-looking layer.
- Preserve both sides with provenance.
- Treat contradiction as a candidate hypothesis, not proof.
- Surface contradictions to users only after thresholds, confidence, and
  exposure rules pass.
- Prefer "your traces differ from your starting profile here" over identity
  language.

---

## 12. Clean-Data And Provenance Requirements

Any analysis, model, or output must declare:

- layer inputs,
- clean-data profile,
- provenance classes,
- excluded classes,
- exposure policy,
- unknown handling,
- confidence threshold,
- sample count,
- allowed consumers.

### Clean-Data Profile Registry

Cortex/product-research profiles currently recognized by architecture:

- `measured_execution`: clean stopwatch-derived execution evidence.
- `planning_calibration`: clean rows eligible for planning estimate
  calibration.
- `pause_process`: pause/resume rows eligible for pause-process analysis.
- `descriptive_history`: product history valid for user display but not
  necessarily valid for learning.

Additional product or diagnostic profiles may exist, but they are not clean
research baselines until a successor contract says so:

- `deadline_completion_behavior`: append-only deadline-resolution behavior.

If a new profile is introduced, the owning document must state its source rows,
provenance inclusions, exclusions, exposure policy, and allowed consumers.

### Usage Class Registry

`usage_class` is separate from clean-data profile. It says what kind of consumer
is allowed to read or emit a projection.

Current usage classes:

- `product`: normal user-facing product behavior.
- `research`: product-research analysis or model evaluation.
- `diagnostic_only`: operator or internal investigation.
- `not_applicable`: no learning or user-facing output path.

Moving `diagnostic_only` and `not_applicable` out of clean-data profiles matters
because they are consumer permissions, not evidence quality.

### Two-Axis Contract

`truth_layer` and `provenance_class` are independent dimensions.

Examples:

- A `PauseEvent.paused_at_utc` timestamp can be Layer A with `observed`
  provenance, while the attached pause reason is Layer D with
  `self_reported` provenance.
- A Moodle submission timestamp can be Layer A with `external_import`
  provenance.
- A correction-adjusted duration can be Layer B with a Layer D repair
  dependency.

Do not encode provenance as the layer, and do not infer layer from provenance.

### Mixed-Row Resolution

Composite rows must not be consumed directly by learning paths. Consumers must
read an explicit projection:

- analytics reads the projection chosen by its declared clean-data profile,
- product UI reads `descriptive_history` by default unless the screen is
  research or diagnostic,
- training and clean baselines read only profile-approved projections.

Named projection classes:

- `raw_observed`,
- `correction_adjusted_effective`,
- `external_submission_trace`,
- `repair_prompt_result`,
- `diagnostic_projection`.

Common provenance classes in current architecture:

- `observed`: directly measured by the system.
- `inferred`: system-generated estimate with uncertainty.
- `self_reported`: explicit user input.
- `retroactive`: user input after the fact.
- `external_import`: imported from Moodle, Google Calendar, or similar.
- `system_recovered`: system repair of missing lifecycle events.

Compatibility note: older drafts may say `user_reported`. Treat it as an alias
for `self_reported` in prose, but new code and docs should prefer
`self_reported` unless the database field already uses another value.

Important distinctions:

- User readiness is self-reported, not observed cognitive readiness.
- User reflection is self-reported, not observed focus or quality.
- Moodle submission is external submission trace, not execution trace.
- Retroactive task creation is useful history, not native stopwatch evidence.
- Correction-adjusted duration is effective product history, not raw observed
  timing.

Unknown propagation rule:

If the system cannot prove provenance, exposure state, or input layer, it should
prefer `UNKNOWN`, exclusion, or no output over a neutral default.

Operator/runtime exclusion rule:

JARVIS, OpenClaw, vault synthesis, and operator orchestration traces are not
product-research inputs by default. They may be audited as operator-runtime
diagnostics, but they must not train or validate user-behavior claims unless a
successor contract explicitly admits them.

Repair-prompt routing rule:

Anomaly detection may emit a repair prompt as an `intervention`. User
confirmation or denial lands in Layer D. Any `system_recovered` state remains
distinct from observed truth and must be projected separately before analytics,
UI, or training consumes it.

Evaluation versioning rule:

Any persisted, exported, or research-cited artifact that depends on Cortex
semantics should record `cortex_schema_version_at_evaluation` or an equivalent
version field. Without versioning, later changes can make historical metrics
look comparable when they were computed under different rules.

---

## 13. Layer Interaction Examples

### Brain Dump

Brain dump is cognitive unloading and task creation.

Flow:

```text
User text
  -> parsed task candidates
  -> Task rows
  -> Today tab
```

Layer status:

- raw user text: Layer D,
- created task plan: Layer A planning trace,
- parse confidence or deadline match: Layer C/derived suggestion depending on
  source,
- any user-facing parse suggestion: Output Surface + Contamination Boundary.

Forbidden interpretation:

- Brain dump content is not proof of ability, avoidance, personality, or future
  completion behavior.

### Survey

Survey is self-report prior creation.

Flow:

```text
Survey answers
  -> Survey Profile Prior
  -> cold-start blend
  -> later weakened or contradicted by observed behavior
```

Layer status:

- survey answers: Layer D,
- assigned profile prior: Layer C derived from Layer D,
- blended calibration: Layer C,
- future behavior: Layer A/B.

Forbidden interpretation:

- Survey assignment is not observed behavior.
- Survey assignment is not identity truth.

### Stopwatch Execution

Stopwatch is observed execution trace.

Flow:

```text
start/stop/pause/resume
  -> Task + StopwatchSession + PauseEvent
  -> active duration, deltas, pause counts
  -> calibration and mirrors
```

Layer status:

- start/stop/pause timestamps: Layer A,
- active duration and deltas: Layer B,
- calibration interpretation: Layer C,
- stop-time mirror: Output Surface + Contamination Boundary.

### Forgotten Timer Correction

Forgotten stop is a trace plus narrative repair.

Flow:

```text
original stopwatch trace
  -> TaskExecutionCorrection
  -> effective duration projection
```

Layer status:

- original trace: Layer A,
- correction sidecar: Layer D,
- effective duration: Layer B projection with Layer D provenance.

Forbidden interpretation:

- Do not treat the corrected timestamp as if it was system-observed.

### Deadline Completion

Deadline completion is deadline-resolution behavior.

Flow:

```text
manual done or external submission
  -> DeadlineCompletionEvent
  -> completed_after_due / delay_minutes
  -> deadline completion analytics
```

Layer status:

- manual click time: Layer A user action plus self-reported semantics,
- Moodle timestamp: Layer A external import,
- delay metrics: Layer B,
- late-completion behavior patterns: Layer C only after thresholds.

Forbidden interpretation:

- Completion is not always submission.
- Submission is not always execution.

### Email Reminder

Email reminder is continuity restoration, not insight.

Allowed copy:

- "Reminder: Physics Assignment - planned for today at 6:00 PM."
- "Your planned task is waiting in LyraOS."
- "You scheduled 'Neuromatch lecture review' for tonight."

Forbidden copy:

- "You tend to miss evening tasks."
- "People like you underestimate study work."
- "Your procrastination pattern is starting."

Layer status:

- email content: Output Surface + Contamination Boundary,
- exposure log: exposure system,
- later behavior: potentially contaminated for reminder-targeted outcomes.

---

## 14. Documentation Rule For Future Changes

Every durable product, research, model, schema, or output change must add or
update documentation.

Minimum documentation must state:

- what phenomenon is represented,
- where it lives in the layer stack,
- whether it creates a new canonical representation,
- what existing code or table owns it,
- how it feeds other layers,
- how provenance is preserved,
- how exposure is logged or why it is not applicable,
- what must not be inferred from it.

If a code change adds a new data path but no documentation, the change is
incomplete.

---

## 15. Structured Decision Template

Use this template for future architecture, research, product, and model
decisions.

```markdown
## Decision: [short title]

**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Deferred | Rejected | Superseded

### Decision / Idea
[What is being added, changed, removed, or deferred?]

### Layer Touched
[Layer A / Layer B / Layer C / Layer D / Output Surface + Contamination Boundary]

### Code Source Of Truth
[Exact model, service, endpoint, worker, or frontend surface]

### Phenomenon Represented
[What real-world phenomenon this represents]

### Provenance Class
[observed / inferred / self_reported / retroactive / external_import / system_recovered / unknown]

### Truth Class
[trace / metric / interpretation / intervention / diagnostic_only]

### Usage Class
[product / research / diagnostic_only / not_applicable]

### Projection Class
[raw_observed / correction_adjusted_effective / external_submission_trace / repair_prompt_result / diagnostic_projection]

### Feed Direction
[Which layer feeds which other layer?]

### Clean-Data Profile
[measured_execution / planning_calibration / pause_process / descriptive_history / deadline_completion_behavior]

### Output / Exposure Impact
[Does the user see it? What target can it contaminate? What exposure category?]

### Allowed Consumers
[Which analytics, models, endpoints, or UI surfaces may consume this]

### Forbidden Interpretations
[What this must never be treated as]

### Revisit Condition
[What evidence, sample count, failure mode, or phase change should trigger review]

### Complexity Admission
[What recurring integrity failure justifies this? Why was manual/runbook/process
discipline insufficient? Why does the mechanism reduce ambiguity more than it
adds cognitive load? What rung is this on the ladder: manual / runbook / script
/ test / CI / runtime enforcement?]

### Rollout Checklist
[dual-write coverage / legacy-adapter coverage / current-data eligibility / unknown-rate visibility / fail-closed tests / operator-only fallback / topology verification if browser evidence is used]
```

---

## 16. Current Alpha Data Applicability

This architecture defines how LyraOS should infer behavior when evidence
exists. It does not imply that current alpha data supports every future
inference surface.

Architecture validity is not earned by adding more ontology. It is earned when
the product produces enough real, consented, low-friction traces for the
ontology to constrain actual decisions. Architecture work must therefore keep
checking retention, trace volume, exposure coverage, and longitudinal signal
accumulation. A beautiful registry with sparse data is still underfed.

Before shipping a Layer C output, run a current-data eligibility scan:

- how many users have enough clean rows,
- how many rows remain after provenance and exposure exclusions,
- whether evidence exists in the relevant time window,
- whether the output would be trace readback, low-confidence pattern, or
  interpretation,
- whether the output would mostly apply to the operator rather than real alpha
  users.

At sparse data levels, LyraOS may still return value through:

- task creation and scheduled-task facts,
- plain reminders,
- exact trace readbacks after a session,
- one-session or two-session comparisons,
- diagnostic/operator-only dashboards.

Sparse data does not yet support broad cohort-level behavioral claims,
deadline-behavior inference without completion events, correction-behavior
inference without corrections, or identity/proximity claims without declared
thresholds.

---

## 17. Current Canonical Summary

Current stable interpretation:

- Brain dump = cognitive unloading and planning trace creation.
- Survey = self-reported Survey Profile Prior.
- Execution traces = observed behavior.
- Corrections = Layer D narrative annotations on observed traces.
- Metrics = derived structure over declared inputs.
- Inference = probabilistic interpretation, never truth.
- Mirrors = descriptive outputs gated by evidence and exposure policy.
- Email = continuity reminder only.
- Exposure Ledger = firewall between user-facing output and future baseline
  learning.

The system becomes intelligent by resolving contradictions between layers, not
by allowing one layer to dominate the rest.

Self-report provides priors.
Observed traces provide anchors.
Metrics provide structure.
Inference provides hypotheses.
Outputs create exposure.
Contradictions update understanding.

The layers must continuously negotiate reality without merging into one truth.
