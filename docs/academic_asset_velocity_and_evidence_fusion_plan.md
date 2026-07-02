# Academic Asset Velocity And Evidence Fusion Plan

**Status:** Architecture-freeze planning document. Do not implement during the
current freeze unless the freeze decision is explicitly reopened.
**Created:** 2026-05-19.
**Scope:** Future Academic Pressure Map estimates, passive/explicit evidence
fusion, contradiction scoring, and surveillance-hallucination safeguards.
**Implementation state:** Not implemented. This document records the target
architecture and the gap against current code.

Freeze boundary: this document identifies parked future ownership only. It does
not authorize passive telemetry, evidence-tier schema work, runtime AI
synthesis, new user-facing insights, behavior-transition equations, new
provider adapters, or automatic interventions during the architecture freeze.
Implementation phases and data-model sketches below are parked target
architecture, not current runtime permission.

This plan is subordinate to:

- `MANIFESTO.md`
- `docs/academic_pressure_map_contract.md`
- `docs/academic_execution_substrate.md`
- `docs/product_research_assumption_register.md`
- `docs/drift_rollup_contract.md`
- `docs/stale_session_recovery_policy.md`

## 1. Captured Decisions

This section records the actual architecture/product/research decisions behind
this plan so they are not lost as "interesting ideas" during the freeze.

### 1.1 Freeze Decision

- Do not implement asset-velocity estimates during the current architecture
  freeze.
- Do not implement passive telemetry during the current architecture freeze.
- Do not add evidence-tier tables during the current architecture freeze.
- Do not promote cohort-derived academic workload estimates as current product
  claims.
- Document the target architecture now, then implement later in bounded phases.

### 1.2 Current-Code Reality Decision

- Treat the current pressure map as `heuristic_v1`, not as a calibrated
  behavioral model.
- Static type priors and title/category heuristics are acceptable Day-0
  pressure-map scaffolding only.
- Current code does not yet support lecture/tutorial/lab asset counts,
  asset-level execution binding, passive evidence fusion, or cohort workload
  rollups.

### 1.3 Product Direction Decision

- Explicit timers are useful, but should not remain the entire execution
  substrate.
- Students will often forget to stop, pause, or maintain timers correctly.
- Future LyraOS should move from **timer absolutism** to
  **evidence-weighted behavioral inference**.
- Explicit tracking should become one evidence channel among several, not the
  single truth authority.

### 1.4 Passive Tracking Decision

- Passive tracking may be used more than earlier docs implied, but only as
  contextual evidence with consent, provenance, confidence, and revocability.
- Passive activity is not execution truth.
- Passive activity may support continuity, repair prompts, and lower-friction
  UX.
- Passive-only rows must not enter clean calibration without accepted or
  confirmed intention and explicit governance.

### 1.5 Surveillance Hallucination Decision

- The new existential measurement threat is **surveillance hallucination**:

```text
false semantic certainty from partial passive traces.
```

- Examples include:
  - `tab open = studying`
  - `calendar block = execution`
  - `LMS completion = learning`
  - `browser activity = engagement`
  - `idle = distraction`
- The system must downgrade, ask, or preserve uncertainty instead of converting
  weak passive traces into confident semantic claims.

### 1.6 Contradictory Signals Decision

- Contradictory signals are not merely data-quality failures.
- Contradiction can be more informative than self-report alone.
- The system should preserve disagreement between intention, explicit timer,
  passive context, self-report, outcome, and exposure state.
- High contradiction should demote clean-data eligibility and create a
  diagnostic feature, not force a winner.

### 1.7 Self-Report Decision

- Self-report is evidence, not truth authority.
- Readiness, reflection, and duration estimates remain useful.
- Their most useful role may be in contradiction with traces, not as standalone
  ground truth.
- Contradiction must not be framed as lying or moral failure.

### 1.8 Academic Asset Velocity Decision

- Academic pressure estimates should eventually use resource structure:
  recording duration, slide count, page count, problem count, lab/tutorial type,
  and course/domain.
- The cold-start estimate should use aggregate clean execution history for the
  same canonical asset when enough cohort evidence exists.
- The first mathematical shape is:

```text
X_i = structural complexity prior from asset features
V_i = trimmed_mean(T_clean_user_asset / X_i)
expected_minutes_i = X_i * V_i
```

- Expose ranges, not exact values.
- Use robust statistics such as median, p25/p75, trimmed mean, and small-N
  suppression.

### 1.9 Duration Provenance Decision

- If Lyra suggests a duration and the user accepts it unchanged, that is not the
  same evidence as an independent user estimate.
- Future task/plan rows need duration provenance before system priors are used
  in planning.
- Unedited system suggestions must be excluded from pure user-estimate
  calibration.

### 1.10 Clean Cohort Rollup Decision

- Cohort asset velocity must be computed from clean/high-confidence rows only.
- Auto-closed, orphan-repaired, retroactive, corrected, system-error, or
  quality-flagged sessions must not enter clean asset-velocity estimates.
- Passive rows may become descriptive or candidate evidence, but not clean
  cohort velocity until a later explicit confirmation rule exists.

### 1.11 Computation Strategy Decision

- Do not compute cohort asset velocity dynamically during pressure-map request
  handling.
- Use async/materialized rollups with versioning, source high-water marks,
  clean-profile labels, and minimum-N privacy thresholds.
- Pressure-map reads should consume aggregate rollups, not scan raw cohort
  traces live.

### 1.12 University/Institution Decision

- Universities are unlikely to accept broad passive tracking.
- The acceptable framing is student-owned, opt-in, scoped,
  privacy-preserving academic activity signals that reduce manual logging
  burden.
- No raw URLs, tokens, screenshots, keystroke content, private browsing, or
  individual professor/admin monitoring.
- Institution-facing outputs should be aggregate only, with minimum-N privacy
  thresholds.

### 1.13 Domain Semantics Decision

- Execution primitives may generalize, but domain interpretation cannot be
  flat.
- Lectures, tutorials, labs, meetings, dev sessions, and gym sessions have
  different behavioral concurrency rules.
- Future provider/domain adapters should preserve local semantics at the edge
  while normalizing into provider-blind substrate primitives.

### 1.14 User Agency Decision

- Lyra is not designed to create dependency.
- Adaptive feedback should support calibration and eventual release, not make
  users reliant on Lyra as an external regulator.
- Evidence fusion and passive assistance must preserve user correction,
  uncertainty, and low-authority interpretation.

### 1.15 Non-Decision / Open Research Questions

The following are intentionally unresolved:

- exact minimum cohort thresholds,
- contradiction-score thresholds,
- whether evidence tiers are immutable or correction-revisable,
- whether domain weights are manually governed first or learned later,
- what passive signals universities will accept,
- and whether passive context improves prediction without increasing distrust.

## 2. Current Implemented Baseline

The current Academic Pressure Map is `heuristic_v1`.

Implemented today:

- Static obligation-type priors in `backend/app/services/academic_pressure.py`.
- Title/category heuristics for low/medium/high complexity.
- Rounded low/high ranges, not exact predictions.
- Warnings that estimates are visible-structure priors, not calibrated personal
  predictions.
- Methodology copy saying personal timer traces may override priors after enough
  evidence.
- Clean execution filters in Cortex that exclude auto-closed, flagged,
  retroactive, corrected, and system-error sessions.
- `Deadline` rows for due items and provider imports.
- `StopwatchSession` rows for explicit execution traces.
- `DeadlineCompletionEvent` rows for completion/submission traces, explicitly
  not stopwatch execution traces.

Not implemented today:

- Canonical academic asset rows.
- Lecture/tutorial/lab/resource metadata such as recording duration, slide
  count, page count, problem count, or lab type.
- Stable asset identity across users/providers.
- Asset-to-task execution binding.
- Cohort asset-duration rollups.
- `duration_source` provenance on planned durations.
- Evidence tiers such as passive context, explicit clean execution, or
  contradictory evidence.
- Passive telemetry ingestion.
- Passive execution confidence.
- Explicit execution confidence beyond clean-data filters.
- Self-report reliability weighting.
- Bayesian or probabilistic hidden-state inference.
- Contradiction-score computation.

The existing code therefore supports the governance philosophy, but not the
asset-velocity or evidence-fusion substrate yet.

## 3. Product Problem

Students may forget to start, pause, or stop explicit timers. A product that
requires perfect timer hygiene will create friction and lose longitudinal
continuity.

At the same time, passive tracking can create false certainty:

```text
tab open = studying
calendar block = execution
LMS completion = learning
browser activity = engagement
idle = distraction
```

This failure mode is called **surveillance hallucination**:

```text
false semantic certainty from partial passive traces.
```

LyraOS should therefore move away from timer absolutism and toward
evidence-weighted behavioral inference:

```text
accepted intention
  + explicit execution traces
  + passive contextual evidence
  + self-report/reflection
  + correction history
  + exposure state
  -> confidence-bounded interpretation
```

No single channel is truth authority.

## 4. Academic Asset Velocity Model

The Academic Pressure Map cold-start problem:

```text
How long should Lyra initially estimate a lecture, tutorial, lab, assignment,
or study resource will take before the student has personal history?
```

The future answer should be a layered fallback:

1. User override.
2. Personal clean history for the same asset or resource class.
3. Cohort clean history for the same canonical asset.
4. Cohort clean history for the same course/resource-type/bin.
5. Current static `_TYPE_PRIORS`.

### 4.1 Canonical Asset Features

Each academic asset should eventually have a normalized feature vector:

```text
x_i = [
  video_minutes,
  slide_count,
  page_count,
  problem_count,
  lab_flag,
  tutorial_flag,
  assessment_flag,
  course_domain,
  provider_source,
]
```

The first version can use a simple interpretable linear prior:

```text
X_i =
  alpha_domain * video_minutes
  + beta_domain * slide_count
  + gamma_domain * page_count
  + delta_domain * problem_count
  + resource_type_adjustment
```

`X_i` is not true effort. It is a structural complexity prior.

Domain-specific weights are necessary because:

- lecture recordings are not tutorials,
- tutorials are not labs,
- lab sessions are not exams,
- engineering slides are not humanities readings,
- and meetings are not lectures.

### 4.2 Cohort Human Velocity

For a canonical asset `i`, compute only from clean/high-confidence execution
rows:

```text
V_i = trimmed_mean(T_clean_user_asset / X_i, trim=0.10)
```

Where:

- `T_clean_user_asset` is observed execution duration linked to the asset.
- Rows with `auto_closed=True` are excluded.
- Rows with `data_quality_flag IS NOT NULL` are excluded.
- Retroactive/system-error/corrected rows are excluded from clean estimates.
- Passive-only rows do not enter clean velocity unless later promoted by an
  explicit confirmation rule.

Then:

```text
expected_minutes_i = X_i * V_i
```

Expose this as a range, not a point estimate:

```text
p25_minutes <= expected_minutes_i <= p75_minutes
```

Use minimum cohort thresholds before showing cohort-derived estimates.

### 4.3 Small-N And Privacy Rules

Do not show or use cohort priors unless:

- minimum clean row count is met,
- minimum distinct-user count is met,
- outliers are trimmed or winsorized,
- raw user traces are not exposed,
- course/provider identifiers are normalized or redacted as required,
- and the estimate is labeled as a cohort prior, not truth.

## 5. Evidence Channels

Let the unobserved human execution state at time `t` be:

```text
Z_t in {
  planned_not_started,
  executing,
  interrupted,
  idle,
  abandoned,
  completed,
  recovered,
  unknown
}
```

Lyra observes noisy channels:

```text
I_t = explicit intention
E_t = explicit execution tracking
P_t = passive contextual activity
R_t = self-report / reflection
O_t = outcome / correction
X_t = exposure state
```

Each channel emits:

```text
p_channel(Z_t)
```

and has a reliability weight:

```text
w_channel in [0, 1]
```

The system should not immediately choose a winner when channels disagree.
Disagreement is itself a behavioral feature.

## 6. Channel Confidence

### 6.1 Explicit Intention Confidence

High when:

- the user accepted a plan before the execution window,
- the task has a stable deadline or obligation binding,
- the plan was not system-suggested without provenance,
- and the planned duration source is recorded.

Low when:

- intention is inferred,
- the plan was imported but never accepted,
- or duration was system-suggested and accepted unchanged without provenance.

### 6.2 Explicit Execution Confidence

Explicit timer rows are not automatically clean.

Future `explicit_execution_confidence` should be high when:

- manual start exists,
- manual stop exists,
- session is closed,
- `auto_closed=False`,
- `data_quality_flag IS NULL`,
- no orphan repair was needed,
- pause data is internally consistent,
- and duration is plausible.

It should be force-demoted when:

- `auto_closed=True`,
- orphan task recovery occurred,
- session was repaired after a stale state,
- task was retroactive,
- task was corrected,
- or timer state and task state disagree.

### 6.3 Passive Execution Confidence

Passive activity is contextual evidence, not truth.

Future `passive_execution_confidence` may use:

```text
PEC =
  resource_match
  * focus_ratio
  * activity_continuity
  * idle_penalty
  * ambiguity_penalty
  * consent_scope
```

Examples:

- Foreground LMS lecture page, video progress, active scroll, matched accepted
  intention: medium/high passive confidence.
- Lecture tab open in the background for three hours: low passive confidence.
- Unmapped activity outside the consent scope: zero admissible confidence.

### 6.4 Self-Report Reliability

Self-report is evidence, not truth authority.

Future `self_report_reliability` should consider:

- time elapsed after task,
- deadline pressure,
- cascade context,
- outcome valence,
- repeated contradiction with traces,
- and whether the user edited or corrected the reflection later.

Contradictions between self-report and traces should not be treated as lying.
They may indicate scope inflation, memory reconstruction, hidden complexity,
perfectionism, or low metacognitive visibility.

## 7. Contradiction Score

A contradiction occurs when high-confidence channels imply incompatible states.

For channels `a` and `b`:

```text
C_ab(t) =
  w_a * w_b * distance(p_a(Z_t), p_b(Z_t))
```

The first implementation should prefer simple bounded distances over complex
models:

```text
distance = L1 or L2 distribution distance
```

Later research versions may compare KL divergence, Jensen-Shannon divergence,
or learned calibration functions.

For a task/window:

```text
C_window = weighted_mean(C_ab(t) over channel pairs and time windows)
```

High contradiction should:

- demote clean-data eligibility,
- preserve the window as descriptive history,
- trigger low-friction repair/correction prompts only under cooldown rules,
- and store the contradiction as a useful feature.

High contradiction should not:

- silently pick passive tracking over the user,
- silently pick self-report over telemetry,
- assign identity labels,
- or enter planning calibration as clean truth.

## 8. Evidence Tiers

Future rows should be classified into an evidence tier.

| Tier | Meaning | Calibration use |
| --- | --- | --- |
| `tier_0_unknown` | No reliable inference. | Excluded. |
| `tier_1_passive_context` | Passive activity only. | Descriptive only. |
| `tier_2_passive_matched_obligation` | Passive activity matches an imported or canonical obligation. | Descriptive; repair prompts allowed. |
| `tier_3_intention_plus_passive` | Accepted intention plus supporting passive context. | Candidate; needs explicit confirmation for clean calibration. |
| `tier_4_clean_explicit_execution` | Clean manual execution trace. | Eligible for measured execution. |
| `tier_5_multi_signal_confirmed` | Clean explicit trace plus passive/outcome/reflection agreement. | Strongest eligible evidence. |
| `tier_x_contradictory` | Channels disagree materially. | Diagnostic/descriptive; excluded from clean calibration. |

This hierarchy protects both UX and science:

- passive tracking can reduce manual friction,
- explicit timers can remain valuable,
- forgotten stops do not poison the model,
- and surveillance hallucination is contained.

## 9. Provider And University Boundary

Universities are unlikely to accept broad passive surveillance.

The institutionally viable version is:

```text
student-owned, opt-in, scoped, privacy-preserving academic activity signals
used to reduce manual logging burden.
```

Rules:

- No hidden screenshots.
- No keystroke content.
- No private browsing capture.
- No raw URLs or tokens in logs.
- No individual professor/admin monitoring dashboard.
- No institution-facing individual execution scores.
- No provider completion equals learning claim.
- Individual corrections and deletion rights remain first-class.
- Aggregates only after privacy and minimum-N thresholds.

Passive data should ideally be normalized locally before backend ingestion:

```text
raw local signal -> scoped structural indicator -> backend evidence event
```

Example:

```text
is_active_academic_resource = true
resource_match = canonical_asset_id
foreground_seconds = 420
idle_seconds = 30
raw_url = never sent
```

## 10. Data Model Plan

Future tables/fields should be introduced only after the architecture freeze.

### 10.1 AcademicAsset

Potential fields:

- `asset_id`
- `provider`
- `provider_asset_key_hash`
- `course_key_hash`
- `resource_type`
- `title_hash` or safe normalized title
- `video_minutes`
- `slide_count`
- `page_count`
- `problem_count`
- `lab_flag`
- `metadata_provenance`
- `metadata_confidence`
- `created_at`
- `updated_at`

### 10.2 TaskAssetBinding

Potential fields:

- `task_id`
- `asset_id`
- `binding_source`
- `binding_confidence`
- `accepted_by_user_at`
- `voided_at`

### 10.3 AcademicAssetVelocityRollup

Potential fields:

- `asset_id`
- `rollup_version`
- `clean_profile`
- `n_clean_rows`
- `n_distinct_users`
- `trimmed_mean_minutes`
- `median_minutes`
- `p25_minutes`
- `p75_minutes`
- `complexity_score`
- `velocity_multiplier`
- `computed_at`
- `source_high_water_mark`
- `eligible_for_pressure_map`

### 10.4 Duration Provenance

Task or plan rows need duration provenance before system estimates become
user-facing priors:

- `duration_source`
- `duration_suggested_low_minutes`
- `duration_suggested_high_minutes`
- `duration_user_edited`
- `duration_accepted_at`
- `duration_estimate_version`

Suggested `duration_source` values:

- `user_entered`
- `system_static_prior`
- `system_asset_structure_prior`
- `system_cohort_asset_prior`
- `system_personal_history_prior`
- `provider_imported`
- `retroactive_user_reported`

Rows accepted unchanged from system suggestions are epistemically different
from independent user estimates.

## 11. Computation Plan

Do not compute cohort velocity dynamically inside the pressure-map request.

Use an async/materialized rollup:

```text
clean execution rows
  -> asset bindings
  -> asset velocity worker
  -> versioned rollup table
  -> pressure map reads aggregate rollup
```

Reasons:

- pressure map latency must stay low,
- cohort aggregation must preserve privacy thresholds,
- rollups need versioning and source high-water marks,
- clean-data profile must be explicit,
- and user-facing estimates should not run expensive historical queries.

## 12. Implementation Phases

### Phase 0 - Documentation And Freeze

- Keep this document as planning only.
- Do not add new tables during the current freeze.
- Do not add passive telemetry during the current freeze.
- Do not promote cohort duration estimates as product claims.

### Phase 1 - Asset Identity

- Add canonical academic asset model.
- Add provider adapter mapping from Moodle/Baseet resources to assets.
- Store only safe metadata and hashes.
- Add tests for user scoping, provider leakage, and raw URL/token redaction.

### Phase 2 - Asset Metadata

- Capture recording duration, slide count, page count, problem count, and
  resource type where provider data supports it.
- Mark metadata provenance and confidence.
- Keep missing metadata as explicit unknowns, not zeros.

### Phase 3 - Task Asset Binding

- Bind user tasks to academic assets with confidence and user confirmation.
- Avoid treating provider structure as execution truth.
- Add repair UI for wrong bindings.

### Phase 4 - Duration Provenance

- Add duration-source fields.
- Separate user-entered estimates from system-suggested accepted estimates.
- Exclude unchanged system suggestions from pure user-estimate calibration.

### Phase 5 - Cohort Rollup

- Add versioned asset velocity rollup.
- Compute from clean explicit rows only at first.
- Enforce minimum row/user thresholds.
- Use robust statistics: median, p25/p75, trimmed mean.

### Phase 6 - Pressure Map Integration

- Update pressure map fallback chain.
- Show ranges and estimate provenance.
- Preserve low-authority, non-judgmental copy.
- Keep static priors as fallback.

### Phase 7 - Evidence Tiers

- Add evidence-tier classification.
- Start with explicit clean execution and contradictory/repaired states.
- Keep passive tiers dormant until passive capture exists.

### Phase 8 - Passive Context Layer

- Add opt-in, scoped passive context only after privacy review.
- Normalize raw local activity to structural indicators before backend ingestion.
- Keep passive-only rows out of clean calibration.

### Phase 9 - Contradiction Scoring

- Compute simple contradiction scores from channel distributions.
- Store contradiction as a feature.
- Demote high-contradiction windows from clean calibration.
- Add repair prompts with cooldown and low-authority copy.

### Phase 10 - Research Validation

- Compare:
  - static priors,
  - asset-structure priors,
  - cohort asset priors,
  - personal-history priors,
  - and evidence-tier-aware estimates.
- Validate whether passive context improves prediction without increasing
  surveillance hallucination or user distrust.

## 13. Test Plan

Future tests should cover:

- asset metadata redaction,
- provider-specific leakage prevention,
- canonical asset identity across users,
- user-scoped task-asset binding,
- clean execution filter reuse,
- auto-closed sessions excluded from asset velocity,
- corrected/retroactive sessions excluded from clean velocity,
- minimum-N cohort suppression,
- rollup versioning and high-water marks,
- pressure-map fallback order,
- duration-source provenance,
- unchanged system estimates excluded from pure user-estimate calibration,
- evidence-tier demotion for contradictory rows,
- passive-only rows excluded from clean calibration,
- and user-facing copy avoiding exact-hour or judgment claims.

## 14. Open Questions

- What minimum `n_clean_rows` and `n_distinct_users` should activate cohort
  asset priors?
- Should domain weights be manually governed at first or learned after cohort
  scale?
- Should asset velocity be course-specific, institution-specific, or global
  with domain/institution random effects later?
- How should user edits to system-suggested durations update personal history
  without contaminating pure estimate-error research?
- What passive signals, if any, can universities accept under opt-in and
  student-owned governance?
- What contradiction threshold should route a row to `tier_x_contradictory`?
- Should evidence tiers be immutable at task close, or can user corrections
  revise the tier while preserving the original tier as history?

## 15. Non-Goals

This plan does not authorize:

- hidden surveillance,
- professor/admin individual monitoring,
- passive-only learning claims,
- exact-hour predictions,
- productivity scoring,
- identity labels,
- BCI integration,
- institutional deployment,
- or clean-data admission from passive activity without confirmed intention and
  explicit governance.
