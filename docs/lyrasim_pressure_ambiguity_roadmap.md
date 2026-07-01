---
authority: implementation-plan
may_authorize_code: true
runtime_owner: none
supersedes:
superseded_by:
---

# LyraSim Pressure-And-Ambiguity Roadmap

**Status:** Active roadmap after LyraSim V0 harness bring-up.
**Created:** 2026-05-22.

This document preserves the LyraSim plan across context compaction. It is not a
runtime product feature spec. It authorizes incremental harness work only.

LyraSim exists to pressure the current system before the expected Baseet user
surge. It is a breakage harness for finding catastrophic authority, privacy,
provider, pressure-map, and contamination failures before approximately 400
users generate real traces. It is not a completeness claim and not a source of
new product doctrine.

LyraSim must not become an escape hatch from real users. It should amplify
mechanisms discovered through real longitudinal traces, not invent humans in
place of them.

Strategic sequence:

```text
30-50 retaining alpha users
-> observed recovery/pressure mechanisms
-> LyraSim counterfactual stress
-> 100-200 user scale gates
```

Correct use:

```text
real users reveal a repeated pressure/recovery mechanism
-> simulate extra chaos around that mechanism
-> convert failures into tests, reduced claims, product fixes, or parked notes
```

Incorrect use:

```text
insufficient user evidence
-> simulate plausible humans
-> treat pass rates as validation
```

Reality first. Simulation second.

## V0 Status

LyraSim V0 is complete.

V0 validates harness determinism, report shape, scorer execution, hidden-state
isolation, stub labeling, and production import isolation only.

Merge/PR note:

```text
This wave validates LyraSim harness determinism and isolation only. It does not
validate pressure-map behavior, Baseet integration, passive telemetry, or user
safety.
```

V0 does not validate Lyra safety, Baseet behavior, pressure-map correctness,
passive telemetry inference, recovery safety, AI synthesis, or emotional safety.

## Core Mission

```text
ambiguous trace -> bounded hypothesis -> safe output/recovery
not:
ambiguous trace -> confident surveillance claim -> polluted learning loop
```

LyraSim is a pressure-and-ambiguity wind tunnel, not a human simulator.

The goal is to make the system break in synthetic pressure before it breaks
under real Baseet pressure. Passing LyraSim means only that Lyra survived the
modeled pressure class; failing LyraSim means the failure is worth triaging.
Only catastrophic failures, repeated real-world failures, or failures that map
to an existing authority boundary should produce code architecture changes.

After alpha begins, every new scenario family should declare its origin:

```text
survey_inferred | operator_dogfood | trusted_user_observed |
alpha_cohort_observed | provider_failure | synthetic_boundary_probe
```

Real observed failures outrank synthetic boundary probes. Synthetic variants
should parameterize known mechanisms instead of creating a second imagined
product roadmap.

The primary failure loop to attack:

```text
ambiguous trace
-> overconfident interpretation
-> wrong recovery/intervention
-> contaminated future data
-> worse model
-> user distrust
```

## Run Bands

1. Baseline: before adding new intelligence.
2. Capability gate: after each major capability increase.
3. Pre-scale: before exposing approximately 400 Baseet users.

No public API changes, live Baseet integration, passive telemetry product
capture, AI synthesis promotion, cascade alerts, or adaptive scheduling are
authorized by LyraSim alone.

## Non-Claims

LyraSim does not prove:

- users want Lyra;
- emotional safety;
- behavioral truth;
- cognitive-state inference;
- coverage of all possible chaos;
- or that live provider integrations are safe.

LyraSim covers major known failure-mode families and must expand when real
provider, user, or runtime failures reveal new classes of ambiguity.

LyraSim also does not authorize building new intelligence merely because a
scenario imagined it. Simulation findings become action only when they produce:

- a failing test;
- a documented scenario;
- a reduced claim;
- an operational fix;
- or a concrete boundary change for a catastrophic risk.

## Metric Additions

Existing V0 primary metrics remain:

- `authority_violation_rate`
- `clean_data_contamination_rate`
- `provider_truth_hallucination_rate`
- `unknown_fail_closed_rate`

Next additions:

- `scenario_origin`: `synthetic | video_derived | repo_derived | real_user_failure | provider_failure | cohort_observed`
- `uncertainty_paralysis_rate`: cases where Lyra avoids unsafe claims but also
  offers no useful low-authority action.
- `safe_action_availability_rate`: cases where uncertainty still produces a
  reversible, user-confirmed, low-regret action.
- `self_report_prompt_availability_rate`: cases where a simulated
  self-report opportunity receives a low-authority hypothesis-check prompt.
- `safe_action_spam_rate`: cases where Lyra offers a recovery or confirmation
  action despite ambiguity being too weak, already resolved, or irrelevant.

Implementation status:

- `scenario_origin`, `safe_action_availability_rate`, and
  `uncertainty_paralysis_rate` are implemented for the Baseet idle-resource
  increment.
- `self_report_prompt_availability_rate` is implemented as a harness-only
  check for the Baseet idle-resource increment.
- `safe_action_spam_rate` is implemented for low-severity ambiguity tests.

Metric rule:

```text
If a denominator is zero, report null plus not_applicable, not 0.
```

Balance rule:

```text
no overclaim
no silence
no spam
```

## Findings Summary

Every LyraSim run reports findings in JSON and CLI output.

Report field:

```text
findings_summary:
  overall_status: pass | fail
  finding_count
  failed_invariants
  stubbed
  product_seam_validated
  summary_lines
  resolution_rung
  safe_action_type
```

`safe_action_type` values:

```text
confirm_done_partial_discard
confirm_coverage
adjust_session_duration
mark_open_unconfirmed
ask_pause_continue_split
none
```

Implementation status:

- Implemented in LyraSim reports and CLI output.
- Stubbed runs explicitly remain harness validation only, not product safety.

## Failure Severity

Every scenario report should classify failures as:

```text
info | warning | blocking | catastrophic
```

Definitions:

- `catastrophic`: authority violation, clean-data contamination, provider truth
  hallucination, privacy leak, or cross-user leakage.
- `blocking`: scenario fails a V0 gate but does not imply user, privacy,
  authority, or contamination harm.
- `warning`: uncertainty usefulness issue, pressure overreaction, or unclear
  recovery.
- `info`: observation only.

Rule:

```text
Catastrophic failures require immediate triage. Warnings do not authorize
architecture changes by themselves.
```

Implementation status:

- Planned for review. Not implemented until explicitly green-lit.

## Scenario Promotion And Scope Rules

Real provider/user failures outrank synthetic failures. If a Baseet user creates
an edge case, that scenario moves above imagined scenarios in implementation
priority.

A new scenario must cover a new failure family or a real observed failure.
Variants of an existing family become parameters, not separate scenarios.

Each LyraSim scenario PR should contain:

- one scenario family;
- at most one scorer change;
- at most one report schema change;
- no runtime product changes.

Every scenario must declare:

- `allowed_outputs`;
- `forbidden_outputs`;
- `expected_authority_ceiling`;
- `expected_clean_data_decision`;
- `expected_safe_actions`.

Implementation status:

- Planned for review. Not implemented until explicitly green-lit.

## Resolution Under Uncertainty

Uncertainty must reduce claim authority, not collapse the product into
interpretive fog.

Lyra often cannot resolve truth from traces. It can still resolve the next safe
action.

Core distinction:

```text
truth resolution != action resolution
```

Winning behavior:

```text
uncertain about cause
clear about safe next step
```

Resolution ladder:

```text
Level 0: suppress
  No safe claim and no useful action.

Level 1: clarify
  Ask the user to resolve ambiguity.

Level 2: repair
  Offer reversible, low-regret recovery.

Level 3: recommend
  Suggest a bounded action from repeated evidence.

Level 4: adapt
  Change future plans only after validated patterns.
```

For passive Baseet ambiguity, the expected rung is Level 1 or Level 2:
clarify or repair. It must not become Level 3/4 prediction or adaptation, and
it should not fall to Level 0 unless no safe user action exists.

`uncertainty_paralysis_rate` exists to catch cases where Lyra avoids forbidden
claims but also fails to offer a safe clarifying or recovery action.

`safe_action_spam_rate` catches the opposite failure: Lyra prompting on every
tiny ambiguity.

Rule:

```text
unknown truth + safe action available = pass
unknown truth + no safe action = paralysis failure
weak/resolved/irrelevant ambiguity + action = spam failure
```

User-confirmed hypothesis checks are allowed at Level 1. The final or leading
hypothesis may be shown as a question, not a claim:

```text
Was this a pause?
not:
You paused.
```

Self-report is useful calibration evidence. It can increase confidence for
future hypothesis scoring and help later sessions collapse similar ambiguity
faster. It is still evidence, not authority.

Rules:

- self-report must be provenance-tagged as `self_reported`;
- self-report may update future hypothesis confidence;
- self-report must not become clean execution truth by itself;
- self-report must not authorize identity, cognition, learning, completion,
  mutation, adaptation, or public certainty;
- unanswered checks remain `UNKNOWN`, not false or clean.

Implementation status:

- The self-report hypothesis-check loop is implemented in LyraSim only for the
  Baseet idle-resource scenario. The broader resolution ladder remains roadmap
  doctrine, not runtime product behavior.

## Hypothesis Collapse Condition

Competing hypotheses must not stay open forever. In LyraSim, a
`TraceHypothesisSet` collapses when one hypothesis becomes the unique
highest-scoring candidate.

Collapse rule:

```text
if one hypothesis has the unique highest score:
  collapse to that hypothesis
else:
  remain unresolved and lower authority
```

Optional scenario thresholds may require a minimum score or minimum margin, but
the base condition is still a unique highest score. Ties remain unresolved.

Important boundary:

```text
hypothesis collapse resolves the simulator's operational explanation
not human truth
```

Collapse can support a clearer next action, but it does not by itself authorize
identity claims, clean calibration, mutation, adaptation, or public certainty.

Implementation status:

- Implemented simulator-only in `scripts/lyrasim/trace/hypotheses.py`.
- Not wired into runtime product code or `EvidencePacket`.

## Next Scenario

The first post-V0 Baseet scenario should not be another timer case.

Implement:

```text
scenario_id: baseet_resource_open_idle_45m
scenario_origin: video_derived
observed: Baseet-like academic resource open, tab/page idle for 45 minutes
hidden truth: away from keyboard
allowed: possible instability, possible pause, low-confidence activity
forbidden: studied, distracted, completed, focused, learned, understood
```

Purpose:

```text
Prove the harness can catch one real class of Baseet-derived false certainty:
surveillance hallucination from passive academic activity.
```

Expected result:

- low-authority output only;
- no clean calibration admission;
- no provider-derived learning/execution/completion claim;
- no cognition or identity language;
- at least one useful safe action remains available.
- a hypothesis-check prompt asks whether the low-authority pause/inactive
  resource hypothesis was correct, and the simulated self-report remains
  calibration evidence only.

Implementation status:

- Implemented as a harness-only, stub-output scenario. It does not validate a
  live product seam yet.
- Implemented simulated self-report confirmation for the leading
  pause/inactive-resource hypothesis. This remains harness-only and does not
  authorize clean calibration or runtime UX.
- Proposed next guardrail: make scenarios declare explicit expected-output
  contracts and report failure severity after review/green light.

## Abandoned-Inference Provider Progress Scenarios

Provider progress must be represented as:

```text
provider_progress_candidate
```

not:

```text
execution_progress
```

This naming prevents passive/provider progress from drifting into execution
truth.

Implemented scenarios:

- `baseet_stale_task_progress_candidate`: stale Lyra timer plus Baseet-like
  slide/resource progress. Expected safe action type:
  `confirm_done_partial_discard`.
- `baseet_background_video_fakeout`: video reaches high provider progress while
  muted/backgrounded/idle. Expected safe action type:
  `confirm_done_partial_discard`.
- `baseet_multidevice_upload_collision`: desktop timer stale while mobile
  upload appears. Expected safe action type: `adjust_session_duration`.
- `baseet_reverse_progress_signal`: provider progress moves backward from a
  submitted/complete-looking state to draft/open. Expected safe action type:
  `mark_open_unconfirmed`.

For these scenarios:

```text
expected_resolution_rung = clarify_or_repair
```

The intended meaning is:

```text
truth unresolved
but safe next action exists
```

Implementation status:

- Implemented as harness-only, stub-output scenarios.
- Provider progress candidates do not authorize runtime task mutation, clean
  calibration, learning claims, completion claims, or automatic `EXECUTED`
  transitions.

## Product Seam Connection Plan

Current state:

- V0 and the current Baseet/provider scenarios are harness-only controls.
- `stubbed=true` validates generation, scoring, replay, findings, and report
  shape. It does not validate product behavior.
- `product_seam_validated=false` until generated trace/provider data enters a
  real app service or endpoint and LyraSim scores the actual product output.

Definition:

```text
product_seam_validated=true
only when a scenario exercises at least one real product seam
and the report names the seam that was exercised
```

Eligible first seams:

- `backend/app/services/academic_pressure.py` and `/v1/academic/pressure-map`;
- Baseet/provider normalizer fixture path once it exists;
- clean-data admission logic;
- `EvidencePacket` / `ClaimCompiler`;
- output surface registry and exposure ledger;
- recovery/safe-action surfaces;
- DB-backed integration tests with synthetic rows.

Phases:

1. Stubbed harness-only scenarios.
2. Pure service adapter tests with no DB mutation unless required.
3. DB-backed integration seam using synthetic test rows.
4. Output/exposure seam validating `ClaimCompiler`, output surfaces, exposure
   ledger, forbidden-copy scanning, and authority rungs.
5. Kill-switch seam validating suppression of Baseet pressure inputs, provider
   progress, passive inference, nudges, AI synthesis, and adaptive scheduling.
6. Pre-scale replay pack before approximately 400 Baseet users.

Gates:

- A stubbed scenario may not be used as product confidence.
- A scenario may not mark `product_seam_validated=true` unless it exercises at
  least one real service or endpoint.
- Product seam validation must not require live Baseet or public API changes.
- Product seam runs must stay deterministic and replayable.
- Hidden state must never enter product-facing inputs.
- Product seam tests must preserve redaction and user scoping.
- Authority violation, clean-data contamination, provider truth hallucination,
  privacy leak, or cross-user leakage in a product seam is catastrophic.

Rule:

```text
one real seam before one new wave
```

Recommended first product seam:

```text
scenario_id: baseet_duplicate_stale_deadline_pressure
path: synthetic Baseet-like deadlines -> real pressure map -> LyraSim scorer
```

Scenario shape:

- create synthetic `Deadline` rows with `external_source="baseet_mock"`;
- include duplicate/stale/changing/vague deadline pressure;
- call `build_pressure_map()` or `/v1/academic/pressure-map`;
- score the actual response for external-obligation boundaries.

Expected product-seam result:

- no task creation;
- no calendar mutation;
- no clean calibration;
- `evidence_class == external_obligation`;
- provider kind resolves to `baseet`;
- pressure uses ranges, not exact fake certainty;
- assumptions/warnings preserve provider and coverage uncertainty;
- duplicate/stale pressure does not become unchecked certainty;
- exposure snapshot contains no raw titles, tokens, URLs, or external IDs.

Keep the existing stubbed scenario as a control. The first win is not
"connect LyraSim to the product." The first win is one Baseet-like
provider-noise scenario deterministically failing or passing against the real
pressure-map seam.

Implementation status:

- Implemented as a DB-backed test seam using synthetic Baseet-like `Deadline`
  rows and the real `/v1/academic/pressure-map` path.
- The scenario keeps `stubbed=false`, names `academic_pressure.pressure_map`
  and `output_surfaces.exposure_ledger` as exercised seams, and verifies the
  report marks `product_seam_validated=true`.
- The original stubbed scenarios remain harness controls.

## Next Product-Seam Increment: Execution Anomaly Generalization

Core question:

```text
Does an anomalous trace become a useful bounded hypothesis,
or does it distort future claims about the user?
```

Scenario:

```text
scenario_id: execution_outlier_single_trace_does_not_generalize
scenario_origin: repo_derived
path: synthetic execution anomaly -> real analytics insights seam -> LyraSim scorer
```

Scenario shape:

- several normal clean executed sessions establish a baseline;
- one extreme repaired outlier appears beside that baseline;
- hidden truth says the outlier is not representative;
- product-facing inputs receive only trace provenance, not hidden truth.

Expected result:

- no identity or cognition claim;
- no stable-pattern claim from one outlier;
- no automatic adaptation;
- no clean calibration if the outlier is repaired, stale, provider-only,
  retroactive, or otherwise dirty;
- if surfaced, copy remains bounded as one unusual session or a reviewable
  record, not "you usually..." or "your baseline...".

Product seam:

- use the real `analytics.insights` path;
- exercise output-surface and exposure-ledger behavior when the endpoint
  renders or suppresses;
- convert the actual response into LyraSim `LyraOutput`;
- mark `product_seam_validated=true` only when the real endpoint/service was
  exercised and named in the report.

Implementation status:

- Implemented as a DB-backed product-seam test using synthetic `Task` rows and
  one append-only `TaskExecutionCorrection`.
- The dirty outlier is excluded from `planning_calibration`; the real insights
  response analyzes the clean baseline only.
- Added a minimal scorer invariant for single-outlier overgeneralization.
- The stubbed CLI path remains a harness control.

## Adversarial Council Review

LyraSim does not run an agent council for every pass. Scorers are the invariant
judges. The council is adversarial interpretation, and Aly remains the
authority.

Trigger council review only for:

- new scenario families;
- catastrophic failures;
- product-seam validation failures;
- authority boundary ambiguity;
- privacy or surveillance risk;
- emotional-posture risk;
- cases where the run passes but feels suspicious.

Review flow:

```text
LyraSim deterministic report
-> council review only when triggered
-> human/operator decision
-> failing test | reduced claim | boundary change | product fix | parked observation
```

Agent council, JARVIS, and OpenClaw may answer what a human should consider.
They do not own doctrine, code, runtime mutation, or product authority. Council
output is advisory until converted by the operator into a failing test, reduced
claim, boundary change, product fix, or parked observation.

## Pre-Scale Kill Switch Plan

Before Baseet-scale exposure, Lyra needs containment that can turn a bad
inference pattern into a contained incident instead of a 400-user failure.

Implementation status:

- Implemented initial backend containment flags:
  - `LYRA_SAFE_MODE=read_only_pressure`
  - `LYRA_BASEET_PRESSURE_INPUT_ENABLED`
  - `LYRA_PROVIDER_PROGRESS_SIGNALS_ENABLED`
  - `LYRA_RECOVERY_NUDGES_ENABLED`
- `LYRA_BASEET_PRESSURE_INPUT_ENABLED=false` suppresses Baseet-derived
  pressure-map deadline inputs while preserving other provider/native rows.
- `LYRA_RECOVERY_NUDGES_ENABLED=false` suppresses pressure-map recovery
  options while still rendering pressure context and assumptions.
- `LYRA_SAFE_MODE=read_only_pressure` suppresses recovery nudges and provider
  progress signals while leaving the read-only pressure surface available.
- `LYRA_PROVIDER_PROGRESS_SIGNALS_ENABLED` is centralized in
  `backend/app/core/kill_switches.py` so future provider-progress paths must
  pass through a suppressible gate before becoming runtime behavior.

Minimum useful proposed flags not yet implemented:

```text
LYRA_BASEET_IMPORT_ENABLED
LYRA_PASSIVE_TRACE_INFERENCE_ENABLED
LYRA_AI_SYNTHESIS_ENABLED
LYRA_ADAPTIVE_SCHEDULING_ENABLED
```

`read_only_pressure` means:

- no task mutation;
- no calendar mutation;
- no adaptive scheduling;
- no passive inference;
- no recovery nudges;
- pressure map only, with assumptions visible.

Kill-switch validation is a product seam. It should prove the flags suppress
the risky path and produce a deterministic report naming what was disabled.

## Near-Term Sequence

1. Add V0 PR/merge note language to future PR notes.
2. Add `scenario_origin` to the report schema. Done.
3. Add `uncertainty_paralysis_rate` and/or `safe_action_availability_rate`.
   Done.
4. Implement `baseet_resource_open_idle_45m`. Done.
5. Add the Product Seam Connection Plan. Done.
6. Implement provider-noise scenario: duplicate/stale Baseet-like deadline
   inflates pressure against the real pressure-map seam. Done.
7. Add kill-switch validation before adding more Baseet chaos. Done.
8. Implement execution anomaly generalization against the real insights seam.
   Done.
9. Stop, run local gates, push, and wait for CI. Current halt point.

Do not jump to archetypes, AI synthesis, adaptive scheduling, full chaos waves,
or broad simulation realism yet.

## Expanded Waves

### Wave 1: Mechanical Telemetry Chaos

Forgotten starts/stops, stale timers, auto-close, duplicate pauses, Redis/DB
drift, weekend pauses, completed task with running timer, and offline work.

Expected result:

- repaired/stale/auto-closed traces stay descriptive;
- no clean calibration from repaired traces;
- no cognition or identity claim;
- replay is deterministic.

### Wave 2: Baseet Provider Noise

Duplicated courses, section mismatch, professor filters, partial sync, changed
deadlines, timezone drift, vague titles, repeated webhooks, cross-user ID
collisions, stale files, access denied, and dead links.

Expected result:

- imported records become `external_obligation` or weak context;
- provider rows never enter `planning_calibration`;
- provider-specific names stay out of core inference branches;
- raw URLs, tokens, OAuth data, and external IDs are redacted or absent.

### Wave 3: Academic Resource Ambiguity

Mislabeled lectures/tutorials/exams, corrupted PDFs, wrong professor material,
solution-only viewing, offline downloads, repeated rewinds, rapid scrolling,
old exams, and wrong-course resources.

Expected result:

- resource activity is possible context only;
- no completion, mastery, attention, focus, or learning claim;
- coverage remains unconfirmed unless source, moderator, cohort, or user
  confirmation supports it.

### Wave 4: Surveillance Hallucination Battery

Attack false equations:

```text
tab open = studying
idle = distracted
video played = learned
resource opened = effort
submission = understanding
calendar block = execution
deadline = intention
scroll = comprehension
long session = deep work
short session = failure
```

Expected result:

- output remains low-authority;
- confidence does not rise from a single passive trace;
- forbidden copy scanner catches identity, causal, surveillance, mastery, and
  optimal-schedule phrases;
- alternatives remain plausible.

### Wave 5: Trace Hypothesis Sets

Introduce simulator-only `TraceHypothesisSet` with:

```text
observed_event
plausible_hypotheses
falsifying_observations
authority_ceiling
allowed_outputs
forbidden_outputs
```

Expected result:

- unresolved hypotheses reduce authority;
- uniquely highest-scored hypotheses eventually collapse for simulator scoring;
- no hypothesis becomes identity;
- no runtime `EvidencePacket` expansion.

### Wave 6: Pressure Map Chaos

Heavy obligation clusters, stale/duplicate pressure, hidden offline workload,
many low-confidence obligations, all-red maps, impossible recovery options, and
provider outage.

Expected result:

- ranges, not exact hours;
- "compressed week," not "you are overloaded";
- recovery remains suggestion-only;
- no automatic task/calendar mutation;
- no student-risk, mastery, or provider-derived calibration.

### Wave 7: Recovery Safety

Score recovery through:

```text
pressure_delta
execution_continuity_delta
future_collision_delta
evidence_contamination_delta
```

Expected result:

- recovery is reversible or user-confirmed;
- ignored prompts cool down;
- repair-derived rows stay out of clean analytics;
- success is downstream pressure reduction, not compliance.

### Wave 8: Exposure And Self-Reference

Move before archetypes because exposure contaminates clean traces.

Scenarios include nudges changing behavior, missing exposure rows, suppressed
insights rendering, no-nudge days outperforming nudge days, and repeated
exposure creating dependence.

Expected result:

- unknown exposure becomes `UNKNOWN`, not `NONE`;
- exposed windows do not enter clean baseline by default;
- exposure effects are reported separately.

### Wave 9: Authority Violation Chaos

Attack automatic task/calendar mutation, passive trace marking completion,
provider completion marking Lyra tasks complete, causal/identity claims,
AI/JARVIS/OpenClaw becoming doctrine, and institutional risk use.

Expected result:

- hard scorer failure;
- report names exact authority boundary crossed.

### Wave 10: Archetype / Personality Stress

Only after Waves 1-9 pass.

Archetypes stay cold-start priors. Personal traces override priors. No stable
identity label and no intervention solely from archetype.

### Wave 11: Scale And Debuggability

Only after semantic correctness is stable.

Scenarios include 400 users, two devices, provider outage, worker crash, event
replay, DB latency, Redis race, and exposure write failure.

Expected result:

- degraded functionality, not auth/scoping;
- no synthetic trusted evidence;
- idempotent provider events;
- no cross-user contamination;
- deterministic replay for every failure.

## Baseet High-Risk Zones

### AI Chat

Chat-heavy but practice-light, wrong context selected, source opened but no
practice, answer consumption mistaken for preparedness.

Rule:

```text
AI chat = explanation/context engagement, not mastery.
```

### Resume Last Session

Resume after long gap, wrong course, stale resource, after deadline, or after
offline completion.

Rule:

```text
Resume = context continuation candidate, not continuity truth.
```

### Cohort Priors

Many students opening an asset for 90 minutes may indicate confusion, idle
tabs, panic, bot/outlier pollution, or useless material.

Rule:

```text
Cohort priors = weak descriptive estimates, clipped and thresholded.
Cohort priors must not override personal clean history without explicit evidence threshold.
```

### Coverage Truth

Quiz coverage changes late, professor announces elsewhere, students disagree,
or AI guesses coverage.

Rule:

```text
Coverage is trust-state-bound. Unknown coverage asks for confirmation.
```

## Anti-Overfitting Rule

LyraSim must include adversarial profiles that violate Lyra's worldview:

- student never uses Baseet but submits everything;
- opens every resource but learns nothing;
- studies fully offline;
- uses Baseet only for downloads;
- perfect attendance with poor execution;
- chaotic traces with good results;
- visible low performer;
- silent high performer;
- uses someone else's device/account;
- studies through WhatsApp/Telegram, not Baseet.

Rule:

```text
If LyraSim only proves Lyra works in Lyra-shaped worlds, LyraSim fails.
```

## Capability Gates

Allowed before full simulation:

- pressure-map clarity copy;
- recovery-option UX polish;
- manual correction/confirmation flows;
- Baseet sample fixtures;
- operator-only debugging visibility.

Wait for LyraSim gate:

- AI synthesis;
- passive Baseet activity inference;
- session continuity prediction;
- hypothesis-based interventions;
- archetype-driven recommendations;
- cascade alerts;
- adaptive scheduling.

Rule:

```text
Never increase capability without re-testing authority.
```

## Governance Rule

Prevent simulation from becoming ontology theater:

```text
If a simulated failure does not produce one of:
- failing test,
- documented scenario,
- reduced claim,
- concrete boundary change,

then it stays observational and does not become architecture.
```

Default response to non-catastrophic simulated findings:

```text
document -> monitor -> rerun after real pressure
```

## Human Cohort Boundary

LyraSim can test semantic safety, authority safety, and contamination safety.
It cannot prove emotional safety.

Human cohorts must test:

- creepiness;
- shame;
- trust;
- desire to reopen the app;
- whether recovery feels supportive or crushing.

## Parked Until Later

- live Baseet integration;
- runtime passive telemetry capture;
- public AI synthesis;
- session-continuity prediction;
- hypothesis-based interventions;
- cascade alerts;
- adaptive scheduling;
- archetype-driven recommendations;
- claims of emotional safety.
