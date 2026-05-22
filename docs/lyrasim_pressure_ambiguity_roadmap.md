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

Implementation status:

- `scenario_origin`, `safe_action_availability_rate`, and
  `uncertainty_paralysis_rate` are implemented for the Baseet idle-resource
  increment.

Metric rule:

```text
If a denominator is zero, report null plus not_applicable, not 0.
```

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
Level 0: Suppress
  No safe claim and no useful action.

Level 1: Clarify
  Ask the user to resolve ambiguity.

Level 2: Repair
  Offer reversible, low-regret recovery.

Level 3: Recommend
  Suggest a bounded action from repeated evidence.

Level 4: Adapt
  Change future plans only after validated patterns.
```

For passive Baseet ambiguity, the expected rung is Level 1 or Level 2:
clarify or repair. It must not become Level 3/4 prediction or adaptation, and
it should not fall to Level 0 unless no safe user action exists.

`uncertainty_paralysis_rate` exists to catch cases where Lyra avoids forbidden
claims but also fails to offer a safe clarifying or recovery action.

Implementation status:

- Planned for review. Not implemented until explicitly green-lit.

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

Implementation status:

- Implemented as a harness-only, stub-output scenario. It does not validate a
  live product seam yet.
- Proposed next guardrail: make scenarios declare explicit expected-output
  contracts and report failure severity after review/green light.

## Near-Term Sequence

1. Add V0 PR/merge note language to future PR notes.
2. Add `scenario_origin` to the report schema. Done.
3. Add `uncertainty_paralysis_rate` and/or `safe_action_availability_rate`.
   Done.
4. Implement `baseet_resource_open_idle_45m`. Done.
5. Implement provider-noise scenario: duplicate/stale deadline inflates pressure.
   Next.
6. Stop, run local gates, push, and wait for CI. Required after each increment.

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
