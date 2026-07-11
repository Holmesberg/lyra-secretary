# LyraOS Final Invariant-First Core Loop Refactor Plan

---
authority: implementation-plan
may_authorize_code: true
runtime_owner: none
status: active
approved: 2026-07-11
product_name: LyraOS
rebrand_authority: none
adaptive_runtime_authority: none
ai_runtime_authority: none
schema_authority: none
experiment_authority: none
branch: refactor/freeze-closure
---

## Mission

The sovereign sequence is:

```text
make truth reliable
-> preserve cold-start behavior
-> complete capture
-> prove day-zero orientation
-> prove execution and recovery
-> cautiously increase pause-prediction opportunities
-> extract structure only when reality demands it
-> close and dogfood
```

The current loop is:

```text
consent/onboarding and cold-start prior
+ capture/import
-> pressure orientation
-> explicit plan
-> execution and bounded predictions
-> recovery
-> exposure and outcome evidence
```

This plan increases existing pause-prediction opportunities while improving
the reliability and burden controls of both pause and resume delivery. Resume
eligibility is not expanded.

No runtime AI, adaptive intervention, new prediction family, experiment
system, task graph, passive tracking, provider, schema migration, or new
behavioral claim is authorized.

## Existing-Surface Enhancement Exception

Pause-policy v2 qualifies only because pause prediction is shipped and
registered; its owner, worker, logs, and exposure surface exist; no new
construct, prediction family, schema, provider, mutation path, or claim class
is added; one policy-version rollback reverses it; burden and failure rules are
predefined; and founder approval names only this bounded enhancement.

This is not precedent for informal feature expansion. Every future exception
must independently satisfy the same test. Task-end prediction does not qualify.

## Core Invariants

- Provider/import rows are structure or candidate evidence, never execution
  truth.
- Parsing, estimates, bindings, plans, corrections, and recovery mutations
  require confirmation.
- Decision, delivery, browser render, interaction, mutation, and later outcome
  remain distinct.
- Browser render truth requires authenticated browser acknowledgement.
- `SurveyPrior` is neither identity truth nor empirically discovered cluster
  membership.
- Survey influence remains inspectable separately from personal execution
  evidence and may be contradicted, reduced, or retired without a retake.
- Current scores, prior weights, reveal gates, confidence formulas, predictor
  thresholds, and `personal_weight=min(1,n/30)` are provisional runtime
  behavior, not validated science.
- Estimates expose ranges, broad provenance, uncertainty, and editability.
- System-assisted estimates are not clean user estimates.
- One active timer is allowed; pause reason is explicit; execution excludes
  pauses; session span includes interruption.
- Recovery selection is not proof of successful recovery.
- Missing, unordered, or privacy-blocked evidence remains `UNKNOWN`.
- Visible predictions measure rhythm under LyraOS prompting, not untouched
  natural rhythm.
- Clean provenance does not make a finding true; it makes the finding
  testable. No score, prediction, policy, intervention, or model may be called
  incrementally predictive, calibrated, or improved without an appropriate
  frozen baseline, effect size, and uncertainty statement.
- The operator account remains read-only. Holmesberg mutation uses unique
  prefixes and residual cleanup proof.

## Two Independent Proof Axes

Every evidence-bearing seam must report both axes separately:

1. **Authority integrity:** who observed, proposed, selected, rendered,
   mutated, published, and may roll back.
2. **Epistemic validity:** null, comparator, effect size, uncertainty,
   stability, missingness, and transportability.

CI, provenance, holdout discipline, and exposure fidelity can make an analysis
reconstructible without showing that it beats chance or a simple rule. Neither
axis may substitute for the other.

## Prediction Classification

| Surface | Status | Treatment |
| --- | --- | --- |
| Pause prediction | Shipped | Preserve v1; add provisional founder-only v2 |
| Resume prediction | Shipped | Preserve eligibility; improve lifecycle, burden, and invalidation |
| Archetype reveal/proximity | Shipped but inconsistent | Correct threshold, copy, exposure, and contamination |
| Deterministic deadline suggestion | Shipped | Preserve confirmation, correction, dismissal, and provenance |
| Re-entry surfaces | Shipped but partial | Complete documented manual outcomes |
| Task-end prediction | Historical/unshipped | `preservation_required=false`; keep parked |
| Additional prediction families | Unshipped | Forbidden |

## Wave 0: Recover, Correct, Commit, Push

1. Create an encrypted recovery bundle outside normal staging.
2. Include binary diff, approved untracked files, base SHA, hashes, status,
   file buckets, and commit-allocation manifest.
3. Exclude secrets, cookies, databases, logs, screenshots, production data,
   caches, and generated evidence.
4. Validate restoration in a temporary worktree.
5. Commit model-runtime retirement and deterministic compatibility with tests.
6. Commit verifier, CI/CD, wrapper, and operations changes separately.
7. Commit public-copy changes separately.
8. Commit this plan, authority corrections, bounded concepts, and ledger
   updates separately.
9. Exclude the resurrected root Core Product Loop plan after preserving unique
   shipped-feature evidence for the Wave 1 registry.
10. Correct only active authority, public/AI-readable copy, and contradictions
    identified by the registry. Do not normalize historical archives.
11. Push the full checkpoint before any new refactor seam. Documentation of
    retirement may not precede the code retirement commit.
12. Collect exact-head CI and detached-checkout reconstruction proof.
13. Delete the recovery bundle after green remote CI and reconstruction, no
    later than seven days afterward.

## Wave 1: Preservation Registry And Verifier Truth

Create a registry with `shipped`, `partial`, `dead_code`, `historical`, and
`parked` states. Each row records owner, active contract, user effect, writes,
exposure class, characterization proof, browser path, and rollback.

Required coverage:

- Consent, Brain Dump onboarding, survey/skip/retake, profile reveal, New Task,
  custom categories, creation nudge, deadline binding, conflict override, and
  rapid-submit protection.
- Pulse composition, Today execution/correction, Calendar views and
  drag/resize, Deadlines, Table filtering/export/correction, and Pressure Map.
- Pause/resume predictions, retroactive confirmation, reminders, timer
  overflow, micro-mirror, calibration nudge, Insights states, and re-entry.
- Settings, Google Calendar and Moodle workflows, export/delete, account
  deletion, integration freshness, and operator boundaries.

Verifier requirements:

- Blocking browser findings force `ok=false`.
- Local S1c runs the same layer and Cortex gates as CI.
- Preserve and classify first failures before repair.
- Count differences need redacted attribution or remain unresolved.
- Historical docs can identify shipped behavior but cannot authorize work.
- Task-end prediction, tutorial revival, provider expansion, task graphs,
  passive capture, adaptive scheduling, and new dashboards remain parked.

## Wave 2: Browser-Owned Exposure Truth

Migrate one behavior-shaping family per seam:

1. Archetype proximity and Pressure Map.
2. Deadline suggestion and creation nudge.
3. Stopwatch micro-mirror and calibration output.
4. Pause/resume predictions, reminder, timer overflow, and retroactive
   confirmation.
5. Insights and re-entry surfaces touched later.

Requirements:

- Server computation creates only decision, delivery, or render-candidate
  evidence.
- Browser acknowledgement creates render truth exactly once.
- Cross-user acknowledgement fails.
- Queued but unrendered items terminate as expired, suppressed, superseded, or
  `lost_unrendered`.
- Prediction, notification, render, outcome, and mutation IDs stay correlated.
- No extraction proceeds while a touched surface can fabricate browser render.

## Wave 3: Onboarding And Cold-Start Integrity

- Characterize the real onboarding sequence before normalizing it.
- Preserve survey, skip, retake, assignment history, export/delete, and current
  duration-prior influence.
- Validate item bounds as `4xx`; make survey submission idempotent and latest
  assignment selection ordered.
- Preserve active five-session reveal behavior for compatibility and mark it
  provisional.
- Record implemented scoring ranges and thresholds accurately.
- Remove identity-style wording and raw archetype slugs from visible or stored
  Pressure Map provenance. Correct skipped-user copy.
- Prove survey assignment and behavioral proximity are separate mechanisms.
- Prove survey does not affect parsing, providers, pause/resume prediction,
  canonical task state, or execution truth.
- Preserve prior and personal contribution fields so influence is inspectable.
- Update the existing heuristic registry with provisional and transportability
  status; create no new architecture document.

## Wave 4: Capture And Route Parity

- Centralize Pulse/Today stop-result interpretation.
- Require explicit pause reasons from every route.
- Centralize invalidation for tasks, deadlines, evidence, Pressure Map,
  Calendar, Table, stopwatch, and integrations.
- Preserve New Task create/edit, Use/Keep suggestion, deadline binding,
  categories, conflicts, and double-submit protection.
- Give Pulse explicit partial-error and unavailable states.
- Preserve Brain Dump write-free parse, editable review, include/discard,
  existing-obligation binding, intentional partial success, retry, and
  duplicate protection.
- Return created, reused, rejected, and failed outcomes with direct navigation.
- Keep provider imports separately provenance-bound and idempotent.

### Capture Gate

A real five-obligation Brain Dump or import must produce inspectable accepted
items and an obvious destination without database repair. Failure redirects
the next seam to capture rather than architecture.

## Wave 5: Pressure Map And Day-Zero Value

- Correct double-counted academic and planned load.
- Preserve 1/7/14-day horizons, source/trust distinctions, uncertainty ranges,
  source summaries, safe mode, and dismiss-without-write.
- Every emitted option uses an existing canonical path or is explicitly
  diagnostic-only.
- Keep create/split as editable preview plus confirmation.
- Preserve current deterministic prior use; add no AI estimates or new prior
  influence.

### Day-Zero Gate

A new account can complete or skip the survey, import a calendar or submit a
real Brain Dump, inspect and edit estimate ranges, identify broad provenance,
understand pressure or uncertainty, open Pressure Map, take one real action,
and encounter no personal-history claim before personal history exists.

### Orientation Gate

Pressure Map must change or materially clarify one real decision. Otherwise
return to the weakest orientation behavior.

## Wave 6: Execution, Recovery, And Prediction Policy

### Execution And Recovery

- Fault-inject every stopwatch DB/Redis boundary.
- Preserve active-timer uniqueness, route parity, paused-parent continuity,
  stale resolution, and correction authority.
- Complete documented manual resume, hide, open, reschedule, shrink, split,
  done, drop, and irrelevant actions where existing authority supports them.
- Reconcile stale-policy runtime and copy.
- Do not infer motivation, focus, avoidance, or recovery success.

### Founder-Specific Pause-Policy v2

Policy v2 is founder-only dogfood calibration. It is not a cohort default,
population prior, cold-start policy, validated threshold, or student policy.
Cohort promotion requires separate replay, transportability review, burden
review, and approval.

Preserve policy v1 and all frozen VT-17 analyses. Do not relabel old rows or
use v2 to rescue v1 results.

Before replay, freeze:

- existing eligible-session inclusion and exclusion rules;
- pause-event eligibility and hit definition;
- lead-window inclusivity;
- explicit response, no-response, late pause, and lifecycle-loss treatment;
- active-use-day denominator and observed-accuracy formula;
- opportunity and burden metrics;
- baseline families, random-time sampler, simulation seed set and repetition
  count, lift metric, minimum lift, uncertainty method, and disagreement rule;
- configuration order and tie-breaking;
- chronological split and minimum sample requirements.

Frozen definitions:

- A hit is a qualifying non-retroactive pause for the same user between
  simulated firing time and `predicted_at + 15 minutes`.
- The first qualifying pause after that window but within 60 minutes is late,
  descriptive, and not a hit.
- No-response is missing interaction, not psychological rejection.
- A rendered prediction with no qualifying pause after window close is a
  behavioral miss.
- A prediction without authenticated render proof is excluded from
  visible-prompt accuracy and classified by lifecycle outcome.
- An active-use day is a local day with at least one eligible session.
- Observed accuracy is hits divided by rendered predictions with closed
  observation windows.
- Exposed and known-unexposed history are separate and non-causal reports.

### Temporal Holdout

Require at least 30 eligible founder sessions across at least 10 active-use
days. Split chronologically:

```text
earliest 70% -> calibration
latest 30% -> untouched holdout
```

The holdout needs at least nine eligible sessions across three active-use days.
Otherwise the result is inconclusive.

Using calibration data only, replay confidence floors `0.20`, `0.25`, `0.30`,
`0.35`, and `0.40` against maximum lead windows `3`, `5`, and `10` minutes.
Select the least permissive configuration yielding a median one to two
opportunities per active-use day and no more than one per session. Ties prefer
narrower lead, then higher confidence floor, then higher calibration accuracy.

Evaluate the selected configuration exactly once on untouched holdout. Do not
retune definitions, split, thresholds, or tie-breaking afterward. If holdout
is insufficient or fails burden/opportunity constraints, retain v1 or report
v2 inconclusive; do not enable visible v2.

Record scope `founder_only`, status `provisional`, transportability `unknown`,
windows, every configuration, frozen rules, selection, and holdout result.

### Baseline And Null Comparison

Passing holdout, lifecycle, and burden gates does not establish predictive
signal. Evaluate the selected v2 configuration on the untouched holdout
against comparators frozen before replay:

1. the empirical eligible-window pause base rate;
2. a fixed 30-minute rule and a calibration-period median-pause-time rule,
   each subject to the same eligibility, caps, quiet hours, and observation
   window as v2;
3. a time-matched random-firing null subject to the same session eligibility,
   cadence, cap, quiet-hour, one-prompt-per-session, and observation rules;
4. the no-prompt raw pause-timing distribution as descriptive context.

Use 10,000 random-baseline repetitions with a frozen seed list. Report hit
rate, opportunities per active-use day, prompts per session, lead time, and
false-prompt rate for v2 and every comparator. Record absolute and relative
lift, sample counts, denominator definitions, an 80% bootstrap interval for
absolute lift, and v2's empirical percentile in the random null distribution.

The strongest simple comparator governs when baselines disagree. Founder-
visible v2 may proceed only as a provisional product experiment when:

- every burden and lifecycle gate passes;
- holdout hit rate is at least 0.10 higher and at least one discrete hit better
  than the strongest simple comparator;
- v2 is at or above the 90th percentile of the frozen random null;
- the uncertainty interval is reported and is not wholly below zero;
- no metric, comparator, seed, threshold, or sample rule changes after results
  are viewed.

These are descriptive founder-dogfood gates, not conventional statistical
significance or population validation. If v2 does not outperform the strongest
simple baseline, retain v1 or disable visible prediction, keep v2 shadow-only
if diagnosis remains useful, and record `no_incremental_signal_demonstrated`.

Even after passing, the strongest allowed claim is:

> On Ali's held-out founder history, pause-policy v2 showed provisional
> incremental timing signal over predefined simple and random baselines while
> satisfying burden constraints.

Do not claim that LyraOS predicts when users pause. Cohort evidence and
transportability remain separately required.

### Visible Prediction Burden

Across pause and resume:

- no more than three rendered prompts per local day;
- no more than one pause prompt per active session;
- no more than two resume prompts per paused session;
- at least 60 minutes between resume prompts;
- at least 30 minutes between any prediction prompts;
- none from 22:00 to 08:00 local time;
- none over blocking modals or critical correction flows;
- dismissal silences that family for the session;
- snooze permits one later attempt within remaining caps;
- task/session transition invalidates queued predictions immediately.

Resume eligibility and thresholds remain unchanged.

### Misses And Continuation

Misses, late behavior, dismissal, snooze, no-response, lifecycle loss, and
successful timing remain distinct. Low hit rate may reduce policy status,
uncertainty wording, or visible delivery; it does not rewrite evidence.

If burden fails, disable visible v2 or revert to v1. Diagnostic lifecycle
evidence may remain, but visible prompts may not continue merely to collect
data. Unprompted rhythm requires a later approved schema and study plan.

### Wave 6 Gates

**Execution-recovery gate:** complete a real start/pause/resume or switch/stop
cycle and one disruption/recovery event without manual repair.

**Prediction-burden gate:** caps, spacing, quiet hours, dismissal, invalidation,
and lifecycle truth pass, and the founder does not want to disable predictions
for annoyance. Accuracy is reported but is not the sole gate.

## Wave 7: Reality-Gated Structural Repair

After founder dogfood:

- `promising`: continue only with structure required for reliability, proof,
  reversibility, or cohort operation.
- `weak`: stop extraction and return to the weakest loop stage.
- `blocked`: stop the mission and report the product blocker.
- `not_tested`: authorize no structural extraction.

Eligible seams are limited to Brain Dump orchestration, stopwatch finalization,
recovery-used task commands, Pressure Map projections, and Insights packaging
directly touched by exposure migration.

Do not split `models.py`, Calendar, Today, NewTaskModal, integrations, provider
fields, or compatibility readers merely because they are large.

## Wave 8: Post-Gate Documentation Consolidation

Begin only after Capture, Day-Zero, Orientation, Execution-Recovery,
Prediction-Burden, and Founder Product-Loop Fit have evidence.

Update existing active docs only with method-selection first refusal, no-AI
zones and authority ceilings, candidate versus canonical mutation, prediction
generation versus exposure versus outcome, SurveyPrior versus clustering,
prompted versus unprompted rhythm, and actual threshold/burden findings.

Do not create new architecture documents, runtime abstractions, provider
catalogues, business packaging plans, experiment systems, or AI catalogues.

## Wave 9: Closure And Public Proof

Run full backend tests, frontend build/typecheck, Alembic fresh-database smoke,
static authority and Cortex gates, operator read-only stress, local-current
product loop, export/delete proof, synthetic DB and Redis cleanup, exact-head
CI, and hosted-public read-only proof with expected and served frontend/backend
build IDs.

Public deployment, restart, hosted mutation, production repair, or invasive
forensics requires approval.

## Autonomous Loop And Git Hygiene

- Every seam declares owner, authority class, documented behavior, expected
  writes, user-visible change, proof tier, negative proof, rollback, and stop.
- Normal limit: one authority boundary, eight files, about 300 code lines.
- Adjacent non-blockers become issues.
- Macro-checkpoint after three related seams or 90 minutes.
- Hard stop after eight seams/eight hours, two CI repair cycles, or three
  cosmetic-only seams.
- Run full post-wave proof at macro-checkpoints, serious failures, first writer
  extraction, and PR readiness.
- Stay on `refactor/freeze-closure`.
- Stage explicit paths only; separate authority classes into reviewable
  commits; keep generated evidence and recovery material out of Git.
- Batch up to three related commits per push.
- Each pushed checkpoint must be reconstructable, mergeable, and CI-green on
  its exact SHA.
- Browser-verify behavior-affecting checkpoints comprehensively with real
  account cookies, authenticated render proof, operator read-only checks,
  Holmesberg-only mutation, and residual cleanup proof.
- Use bounded parallel agents only for non-blocking, disjoint audits or edits;
  close them when their results are integrated.
- PR creation requires clean status, current ledger/evidence, pushed commits,
  and exact-head CI.
- Merge, rebase, force-push, branch deletion, deploy, restart, production
  repair, migration, or authority transfer requires founder approval.

## Exit States

- `product_loop_usability_ready`: Capture, Day-Zero, Orientation,
  Execution-Recovery, and Prediction-Burden pass without manual repair.
- `instrumentation_ready`: zero cases classified as browser-rendered exposure
  without authenticated browser acknowledgement; delivered-but-unrendered
  records remain explicit terminal lifecycle outcomes.
- `implementation_green`: no false cockpit blockers, read diffs, cleanup
  residue, or failing touched gates; exact-head CI passes.
- `founder_product_loop_fit`: `promising`, `weak`, `blocked`, or `not_tested`.
- `promising`: voluntary use across at least three real cycles on separate
  days, one changed decision, one useful recovery, trusted execution state,
  tolerable prediction burden, and no QA-only dependence.
- `cohort_green` remains separate.
- `experimentation_ready=false`.
- Refactoring stops at operational danger 3-4/10 when no remaining seam has a
  named present benefit.

## Hard Stop

This plan authorizes only the bounded refactor and founder-only pause-policy v2
calibration above. It does not authorize adaptive intervention, randomization,
runtime AI, reasoning-adapter wiring, account linking, prompts, schema changes,
task graphs, passive tracking, automatic recovery, online learning,
ClaimCompiler meaning changes, new providers, or new behavioral claims.
